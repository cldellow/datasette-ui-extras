---
title: metadata.json
description: Learn how to control datasette-ui-extras' behaviour through metadata.json.
---

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

In either case, a user will only see the edit UI if they have the [`update-row`](https://docs.datasette.io/en/latest/authentication.html#update-row)
permission for the given table or view.
