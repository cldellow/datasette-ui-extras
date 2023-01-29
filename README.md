# datasette-ui-extras

[![PyPI](https://img.shields.io/pypi/v/datasette-ui-extras.svg)](https://pypi.org/project/datasette-ui-extras/)
[![Changelog](https://img.shields.io/github/v/release/cldellow/datasette-ui-extras?include_prereleases&label=changelog)](https://github.com/cldellow/datasette-ui-extras/releases)
[![Tests](https://github.com/cldellow/datasette-ui-extras/workflows/Test/badge.svg)](https://github.com/cldellow/datasette-ui-extras/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/cldellow/datasette-ui-extras/blob/main/LICENSE)

This plugin aims to be a batteries-included theme that makes Datasette more like a self-hosted Airtable or Notion.

You can share read-only access, while still allowing authenticated users to edit data.

You can see a demo at https://dux-demo.fly.dev/

The plugin _tries_ to use stable Datasette hooks where possible. Some of the features
I add aren't natively extensible. In those cases, I do some shenanigans. I try to
exercise good judgment so that we can fail gracefully if Datasette makes a breaking
change.

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-ui-extras

## Usage

The current version of the plug-in only adds read-only features.

A future version will have configuration knobs to permit read-write
of existing tables.

## Features

### Writing

In progress.

### Reading / browsing

The plugin tries to emphasize your data, and de-emphasize any other
chrome.

- Tables have sticky headers so you can keep track of columns while
  scrolling big data sets.

- Facets are rendered in a sidebar, lazy loaded after your core
  table has been shown.

- New facet types: facet by year (`2022`) or year/month (`2022-10`)

- Pressing `/` focuses the search box.

- When viewing a single entry's page, we render the data as a vertical
  column, with one attribute per row.

- JSON arrays of strings are displayed as a comma-separated list.

- Advanced export: This control is hidden by default. Click the `(Advanced)` link to see it.

- Filters: These controls are hidden by default. Click the funnel icon to see them.

- Suggested facets: We no longer suggest facets. Instead, use the cog menu
  on the column to add facets.

- Table/view definitions: These are hidden.


## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-ui-extras
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
