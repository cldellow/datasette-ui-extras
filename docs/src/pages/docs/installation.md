---
title: Installation
description: Learn about datasette-ui-extras' installation requirements.
---

## Minimum requirements

- SQLite 3.27.0 or newer
    - We use modern features of SQL like the `JSON1` extension, [`VACUUM INTO` (3.27.0)](https://sqlite.org/changes.html#version_3_27_0), [window functions (3.25.0)](https://sqlite.org/changes.html#version_3_25_0), and [row values (3.15.0)](https://sqlite.org/changes.html#version_3_15_0)

{% callout title="Need a newer SQLite?" %}
Try `pip install pysqlite3-binary`.

Datasette will then use the SQLite from the [pysqlite3-binary](https://github.com/coleifer/pysqlite3) package, which is an up-to-date version.
{% /callout %}


## WAL mode

`datasette-ui-extras` works best if your database is in [write-ahead logging (WAL) mode](https://www.sqlite.org/wal.html) with the synchronous flag set to [`NORMAL`](https://www.sqlite.org/pragma.html#pragma_synchronous).

You must take action to enable this mode:

```shell
sqlite3 mydatabase.db "pragma journal_mode = wal"
```

WAL mode with `NORMAL` is recommended by the SQLite developers. It is faster
and supports more concurrency than the default settings. It is not the default
due to their long-standing commitment to backwards compatibility.
