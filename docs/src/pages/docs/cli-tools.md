---
title: Command-line tools
description: Learn about datasette-ui-extras's CLI tools.
---

## `dedux`

`datasette-ui-extras` needs to create various hidden tables and triggers to maintain
statistics about your data. This allows us to offer autosuggest and schema-specific
editing controls.

If you no longer wish to use `datasette-ui-extras`, you can remove these additions by
using the `dedux` tool.

```shell
datasette dedux mydb.db
```

## `yolo`

You can use the `yolo` mode to enable a frictionless single-user mode:

```shell
datasette yolo mydb.db
```

Yolo mode will do the following:

- create `mydb.db` if it does not exist
- put `mydb.db` into [WAL mode](https://www.sqlite.org/wal.html) for increased
  concurrency during writes
- update or create Datesette's `metadata.json` file with a very permissive set
  of permissions for this database

**Yolo mode is only suitable for Datasette instances that protected at the
network level.** For example, if you are running Datasette on your laptop's
loopback interface, or behind a load balancer that enforces authentication,
such as [oauth2-proxy](https://github.com/oauth2-proxy/oauth2-proxy).
