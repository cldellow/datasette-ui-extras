---
title: How to contribute
description: Learn how to modify datasette-ui-extras itself.
---

## Configure your environment

To set up this plugin locally, first checkout [the code](https://github.com/cldellow/datasette-ui-extras). Then create a new virtual environment:

```shell
cd datasette-ui-extras
python3 -m venv venv
source venv/bin/activate
```

Now install the dependencies and test dependencies:

```shell
pip install -e '.[test]'
```

To run the tests:

```
pytest
```
