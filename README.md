# datasette-ui-extras

[![PyPI](https://img.shields.io/pypi/v/datasette-ui-extras.svg)](https://pypi.org/project/datasette-ui-extras/)
[![Changelog](https://img.shields.io/github/v/release/cldellow/datasette-ui-extras?include_prereleases&label=changelog)](https://github.com/cldellow/datasette-ui-extras/releases)
[![Tests](https://github.com/cldellow/datasette-ui-extras/workflows/Test/badge.svg)](https://github.com/cldellow/datasette-ui-extras/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/cldellow/datasette-ui-extras/blob/main/LICENSE)

This plugin collects UI tweaks that people have proposed for Datasette.

Compared to core Datasette, this plugin is more willing:

- to use features that require more modern browsers
- to add features that require storing state (e.g., a visitor's
  preferences about how to view a table)
- to require JavaScript
- to release UI changes

I think these are generally reasonable tradeoffs -- as a plugin that users opt-in
to, we have the luxury of being more aggressive in our minimum requirements
and release cadence.

If Datasette makes a breaking change, the plugin may stop working. In that case,
you can uninstall the plugin while waiting for a fix.

OK, that's enough disclaimers.

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-ui-extras

## Usage

TBD

## Features

- facets are re-styled (inspired by [datasette#1159](https://github.com/simonw/datasette/pull/1159))
- tables have a "sticky" header that remains visible as you scroll (similar to "Freeze Rows" in Google Sheets)
- pressing `/` focuses the search box on tables that have one

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-ui-extras
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
