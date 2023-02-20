---
title: metadata.json
description: Learn how to control datasette-ui-extras' behaviour through metadata.json.
---

The read-only changes are all enabled by default.

## Enable edit UI by default

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

## Restrict which columns are searched by omnisearch

By default, any column with a string-ish type is searched by the omnisearch feature.

You can instead explicitly specify the columns to be searched:

```json
{
  "databases": {
    "cooking": {
      "posts": {
        "plugins": {
          "datasette-ui-extras": {
            "omnisearch-columns": ["title", "owner_user_id", "post_type", "tags"]
          }
        }
      }
    }
  }
}
```
