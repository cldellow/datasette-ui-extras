# datasette-ui-extras

[![PyPI](https://img.shields.io/pypi/v/datasette-ui-extras.svg)](https://pypi.org/project/datasette-ui-extras/)
[![Changelog](https://img.shields.io/github/v/release/cldellow/datasette-ui-extras?include_prereleases&label=changelog)](https://github.com/cldellow/datasette-ui-extras/releases)
[![Tests](https://github.com/cldellow/datasette-ui-extras/workflows/Test/badge.svg)](https://github.com/cldellow/datasette-ui-extras/actions?query=workflow%3ATest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/cldellow/datasette-ui-extras/blob/main/LICENSE)

Add a few flourishes to the Datasette UI.

People have proposed some great ideas to make the UI more discoverable, more useful,
or more attractive. This plugin tries to be a canary channel for trying them out.

The plugin will never damage your data. It might stop working if Datasette makes
a breaking change -- in that case, you can uninstall the plugin while waiting
for a fix.

## Installation

Install this plugin in the same environment as Datasette.

    datasette install datasette-ui-extras

## Usage

TBD

## Features

- facets are re-styled (inspired by [datasette#1159](https://github.com/simonw/datasette/pull/1159))

## Development

To set up this plugin locally, first checkout the code. Then create a new virtual environment:

    cd datasette-ui-extras
    python3 -m venv venv
    source venv/bin/activate

Now install the dependencies and test dependencies:

    pip install -e '.[test]'

To run the tests:

    pytest
