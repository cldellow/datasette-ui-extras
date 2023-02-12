# datasette-ui-extras

[![PyPI](https://img.shields.io/pypi/v/datasette-ui-extras.svg)](https://pypi.org/project/datasette-ui-extras/)
[![Changelog](https://img.shields.io/github/v/release/cldellow/datasette-ui-extras?include_prereleases&label=changelog)](https://github.com/cldellow/datasette-ui-extras/releases)
[![Tests](https://github.com/cldellow/datasette-ui-extras/workflows/Test/badge.svg)](https://github.com/cldellow/datasette-ui-extras/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/cldellow/datasette-ui-extras/blob/main/LICENSE)

This plugin aims to be a batteries-included theme that makes Datasette more like a self-hosted Airtable or Notion.

You can share read-only access, while still allowing authenticated users to edit data.

You can see a demo at https://dux.fly.dev/

The plugin _tries_ to use stable Datasette hooks where possible. Some of the features
I add aren't natively extensible. In those cases, I do some shenanigans. I try to
exercise good judgment so that we can fail gracefully if Datasette makes a breaking
change.

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-ui-extras

### Minimum requirements

You must be on Linux-x86, because we load the sqlean crypto library, and have
only bothered to get it working for that platform. See [#69](https://github.com/cldellow/datasette-ui-extras/issues/69) for more info.

`datasette-ui-extras` uses some modern features of SQL, so you'll need SQLite
version 3.25.0 or newer.

> **Note**
>
> Need a newer SQLite? Try `pip install [pysqlite3-binary](https://github.com/coleifer/pysqlite3)`.
> Datasette will then use the SQLite from this package, which is an up-to-date version.

Features we use:

- the `JSON1` extension (minimum SQLite version varies by OS)
- Window functions, introduced in [version 3.25.0](https://sqlite.org/changes.html#version_3_25_0) (2018-09-15)
- Row values, introduced in [version 3.15.0](https://sqlite.org/changes.html#version_3_15_0) (2016-10-14)
- Loadable extensions, to load [the sqlean crypto library](https://github.com/nalgeon/sqlean/blob/main/docs/crypto.md) for generating hashes

## Usage

The read-only changes are all enabled by default.

To enable the edit UI by default for a given table, list them in your metadata.json:

```json
{
  "databases": {
    "mydb": {
      "plugins": {
        "datasette-ui-extras": {
          "editable": ["my_table", "my_view"]
        }
      }
    }
  }
}
```

You can also add `?_dux_edit=1` to the URL of a row page to get the edit view.

Your database will be put into WAL mode, the one true mode.

### Extensibility

You can customize the edit controls that are shown to users by a hook:

```python
from datasette_ui_extras import hookimpl

@hookimpl
def edit_control(datasette, database, table, column, metadata):
    # metadata has the contents of the dux_column_stats row for this column, if available.
    return 'ShoutyControl'

    # You can also return a tuple, the second argument will be merged into the config
    # object passed to your JS interface:
    return 'ShoutyControl', { 'suffix': '!!!' }
```

`ShoutyControl` must be a JavaScript class that is available to the page. This can be a pre-defined one provided by `datasette-ui-extras` or one you author via a file loaded by [`extra_js_urls`](https://docs.datasette.io/en/stable/plugin_hooks.html#extra-js-urls-template-database-table-columns-view-name-request-datasette) or inlined by [`extra_body_script`](https://docs.datasette.io/en/stable/plugin_hooks.html#extra-body-script-template-database-table-columns-view-name-request-datasette)

The class should conform to this interface:

```javascript
window.ShoutyControl = class ShoutyControl {
  constructor(initialValue, config) {
    this.initialValue = initialValue;
    this.el = null;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('input');
    this.el.value = this.initialValue;
    return this.el;
  }

  get value() {
    // Be shouty.
    return this.el.value.toUpperCase();
  }
}
```

## Features

### Writing


- Adds an `edit-row.html` template which is used on row pages when `_dux_edit=1` is present.
    - This follows the [usual Datasette rules for custom templates](https://docs.datasette.io/en/stable/custom_templates.html#custom-templates), and can be overridden on a per-table basis, for example, `edit-row-mydatabase-mytable.html`.

- Support for editing columns containing these data types:
    - JSON arrays of strings
    - Simple (i.e. not composite) foreign keys
    - A closed list of strings or ints, declared via `CHECK (column IN ('option 1', 'option 2'))`
    - Dates like `2023-01-01`
    - Timestamps like `2023-01-01T01:02:03` and a few variations

- Adds an `edit_control` hook that you can use to override which control should be rendered to edit a given `(database, table, column)` tuple.

In progress, see the [Edit UI issue](https://github.com/cldellow/datasette-ui-extras/issues/48) for the roadmap.


### Reading / browsing

The plugin tries to emphasize your data, and de-emphasize any other
chrome.

- Tables have sticky headers so you can keep track of columns while
  scrolling big data sets.

- Facets:
    - Facets are rendered in a sidebar, lazy loaded after your core
      table has been shown.
    - New facet types:
        - facet by year (`2022`)
        - facet by year/month (`2022-10`)
        - statistical summary (min, median, p90, p95, p99, max)
    - Suggested facets: We no longer suggest facets. Instead, use the cog menu
      on the column to add facets.


- Foreign keys:
    - The human description for '=' and '!=' against a column that is a
      foreign key includes the label of the foreign row.
    - The row page shows the label of foreign key values.

- Pressing `/` focuses the search box.

- When viewing a single row's page, we render the data as a vertical
  column, with one attribute per row.

- Mobile column options: Click the column name to see the column options, for sorting and faceting.

- JSON arrays of strings are displayed as a comma-separated list.

- JSON arrays of strings are 3x faster to filter and 4x faster to facet.

- Views: better support for views of the shape `SELECT ... FROM base_table`
    - Can navigate to row page, e.g. https://dux.fly.dev/cooking/questions/1

- Advanced export: This control is hidden by default. Click the `(Advanced)` link to see it.

- Filters: These controls are hidden by default. Click the funnel icon to see them.

- Table/view definitions: These are hidden.

### API

- Views: better support for views of the shape `SELECT ... FROM base_table`
    - JSON API can update these rows, assuming they have an [INSTEAD OF trigger](https://www.sqlite.org/lang_createtrigger.html#instead_of_trigger)

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-ui-extras
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
