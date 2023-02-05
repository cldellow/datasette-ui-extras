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

## Features

### Writing


- Adds an `edit-row.html` template which is used on row pages when `_dux_edit=1` is present.

- Adds an `edit_control` hook that you can use to override which control should be rendered to edit a given `(database, table, column)` tuple.

In progress, see the [Edit UI issue](https://github.com/cldellow/datasette-ui-extras/issues/48) for the roadmap.


### Reading / browsing

The plugin tries to emphasize your data, and de-emphasize any other
chrome.

- Tables have sticky headers so you can keep track of columns while
  scrolling big data sets.

- Facets are rendered in a sidebar, lazy loaded after your core
  table has been shown.

- The human description for '=' and '!=' against a column that is a
  foreign key includes the label of the foreign row.

- New facet types:
    - facet by year (`2022`)
    - facet by year/month (`2022-10`)
    - statistical summary (min, median, p90, p95, p99, max)

- Pressing `/` focuses the search box.

- When viewing a single entry's page, we render the data as a vertical
  column, with one attribute per row.

- Mobile column options: Click the column name to see the column options, for sorting and faceting.

- JSON arrays of strings are displayed as a comma-separated list.

- JSON arrays of strings are 3x faster to filter and 4x faster to facet.

- Views: better support for views of the shape `SELECT ... FROM base_table`
    - Can navigate to row page, e.g. https://dux.fly.dev/cooking/questions/1

- Advanced export: This control is hidden by default. Click the `(Advanced)` link to see it.

- Filters: These controls are hidden by default. Click the funnel icon to see them.

- Suggested facets: We no longer suggest facets. Instead, use the cog menu
  on the column to add facets.

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
