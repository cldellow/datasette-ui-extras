---
title: Architecture guide
description: Get the 30,000 foot overview of how datasette-ui-extras works.
---

## Relationship to Datasette

`datasette-ui-extras` is a third-party Datasette plugin. In many cases, it's possible to
extend Datasette using its documented and supported [plugin hooks](https://docs.datasette.io/en/stable/plugin_hooks.html).

In some cases—mainly around the UI—extension via hooks is not yet supported.
For these cases, we act more like a parasite than a plugin, wildly monkey-patching Datasette and
fundamentally changing what it can do.

Some parts of `datasette-ui-extras` might migrate into core Datasette over time,
or at least be possible via officially-sanctioned plugin hooks.

The implications:

- Try to add features in a modular way. Limit their interaction with other
  features, so their blast radius is small if they stop working due to a
  breaking change in Datasette. This also makes it easier to upstream the feature
  into Datasette core.

- Try to follow Datasette's practices:
  - State should be represented in URLs, not cookies. For example, we use the
    [`_dux_show_filters` query parameters](https://dux.fly.dev/cooking/posts?_dux_show_filters=1) to toggle visibility of filters on the table page.
  - Choose reasonable defaults, but always consider having a hook for the
    user to customize behaviour.

{% callout title="JavaScript" %}
One area where we differ from Datasette is our willingness to use JavaScript.

In particular, all editing controls are currently implemented via JavaScript
and the Write API.
{% /callout %}


## How we communicate data to JavaScript

Most of our UI changes are achieved by self-contained JavaScript modules
that run on the page. These modules sometimes need configuration information
from the Python code. This information is passed via global variables:

- `__dux_permissions` is a map containing the set of permissions that
  the current user has. This is set on database, table and row pages.
- `__dux_facet_suggestions` is a map suggesting candidate facets for each column.
  This is set on the table page.
- `__dux_facets` is a map listing which facets are enabled. This is
  set on the table page.

## JavaScript and CSS extensions

A given feature like `lazy-load facets` or `edit rows` may have CSS and JavaScript
components.

The CSS and JavaScript should be placed in the `/static/` folder and registered
in the module's `__init__.py`.

Follow the existing examples to ensure that it's safe for your CSS and JavaScript
to be included on _any_ page. For example, you should use selectors that target
`body.edit-row` if your code is only intended for the edit row screen.

## The `dux_column_stats` index tables

Many of our features require knowing the shape of data contained in a table,
or the set of eligible values to be used in a given column.

This is achieved by an indexing process that runs in the background. It maintains
state in each database in a handful of hidden tables.

### `dux_ids`

`dux_ids` assigns a unique ID to every table name and column name in your schema.
This allows us to save storage space, as many of the other tables repeat these
names.

Browse an example [dux_ids](https://dux.fly.dev/cooking/dux_ids) table here.

### `dux_column_stats_ops`

`dux_column_stats_ops` tracks the queue of indexing work to be done.

Indexing happens in batches, on a per-column, per-table database. This allows us
to make progress while not locking up the Datasette instance for other users.

We use [keyset pagination](https://use-the-index-luke.com/no-offset) to remember
our location in the queue and efficiently fetch the next set of items to index.

Browse an example [dux_column_stats_ops](https://dux.fly.dev/cooking/dux_column_stats_ops) table here.

### `dux_column_stats`

`dux_column_stats` tracks high-level summary stats about the values in
a column: minimum, maximum, how many were `NULL`, how many were JSON objects,
etc.

This lets the plugin quickly propose what sort of edit control might be appropriate
for a given column.

Browse an example [dux_column_stats](https://dux.fly.dev/cooking/dux_column_stats) table here.

### `dux_column_stats_values`

`dux_column_stats_values` tracks all the individual values in columns containing
string-like values.

This lets us offer [per-column autosuggest](/docs/endpoints#dux-autosuggest-column).

Browse an example [dux_column_stats_values](https://dux.fly.dev/cooking/dux_column_stats_values) table here.

### `dux_pending_rows`

`dux_pending_rows` tracks rows that have been updated and need their columns' summary
stats updated.

Once we've finished the initial backfill of stats, we try to keep stats mostly
up-to-date. To achieve this, every table gets an INSERT, UPDATE and DELETE trigger.
The trigger creates a row in `dux_pending_rows` with a JSON object that represents
the old and new values of the modified row.

The background indexing thread consumes these rows and updates the stats columns.

There are some caveats: we only do updates that can be completed in fixed time.
For example, we can update counts, and expand the `min` and `max` values when
a new value is smaller or larger than older values.

However, deleting a row that previously contained the `min` or `max` value cannot
be efficiently handled in fixed time. To know what the new `min` or `max` value
should be, we'd need to scan all the rows of the table. Instead, we leave the
old value in place. In practice, for the purposes for which we use stats, and
the usage patterns of most databases, this works fine.

Browse an example [dux_pending_rows](https://dux.fly.dev/cooking/dux_pending_rows) table here.
