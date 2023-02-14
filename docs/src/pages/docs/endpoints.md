---
title: Endpoints
description: Discover the API endpoints offered by datasette-ui-extras.
---

## `dux-autosuggest-column`

`datasette-ui-extras` tracks popular values in columns that contain strings, or JSON string arrays.
You can query these via an API endpoint. For example, to see the popular values in
the `posts.tags` column of the `cooking` database:

```shell
curl 'https://dux.fly.dev/cooking/posts/-/dux-autosuggest-column?column=tags&q=bak'
```

That will output something like:

```json
[
  {
    "value": "baking",
    "count": 340,
    "pks": [
      { "id": 14921 },
      { "id": 14928 },
      ...
    ]
  },
  {
    "value": "baking-powder",
    "count": 8,
    "pks": [ ... ]
  },
  {
    "value": "baking-soda",
    "count": 8,
    "pks": [ ... ]
  }
]
```

The `pks` field shows up to 10 primary keys of rows that have this value.
