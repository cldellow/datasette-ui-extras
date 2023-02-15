---
title: Hooks
description: Learn about the extensibility hooks of datasette-ui-extras.
---

You can extend `datasette-ui-extras` by writing small Python functions
that implement one of these hooks.

## `edit_control`

This hook determines which UI control is shown to edit a value.

```python
def edit_control(
  datasette, # An instance of the Datasette class
  database,  # The database name, e.g. "cooking"
  table,     # The table name, e.g. "posts"
  column,    # The column name, e.g. "tags"
  row,       # A sqlite3.Row with the other values for columns of the row
  value,     # The value being rendered
  metadata   # Stats about the column being rendered
)
```

We ship [several UI controls for editing fields](/docs/built-in-edit-controls).

By default, we choose which control to show based on your [database's schema](/docs/sql-schema). Sometimes
that choice is ambiguous. For example, if the existing rows are all ones and zeroes,
we might show a checkbox control. But perhaps we really ought to have shown
a free-form number input.

You can override our choice by implementing this hook.

```python
from datasette_ui_extras import hookimpl

@hookimpl
def edit_control(table, column):
  if table == 'my_table' and column == 'not_a_checkbox':
    return 'NumberControl'
```

Your function can return:

- `None` - to use the default behaviour
- a string, like `NumberControl` - to use the specified JavaScript class to render the control. This can be one of our [built-in controls](/docs/built-in-edit-controls) or a [custom control that you implement](/docs/custom-edit-controls)
- a tuple of (string, dict) - to use the specified JavaScript class to render the control, and pass the dict of parameters to it as configuration
- an awaitable function that returns one of the above values

## `redirect_after_edit`

This hook determines where a user is sent after creating, updating or deleting
a row.

```python
def redirect_after_edit(
  datasette, # An instance of the Datasette class.
  database,  # The database name, e.g. "cooking"
  table,     # The table name, e.g. "posts"
  action,    # "insert-row", "update-row" or "delete-row"
  pk         # The key of the modified row, eg `1` or `compound,key`
)
```

The `pk` value is [tilde-encoded](https://docs.datasette.io/en/stable/internals.html#tilde-encoding).

By default:

- for inserted or updated rows, the user is redirected to the row page
- for deleted rows, the user is redirected to the table page

You can customize this to create purpose-built workflows for editing:

```python
from datasette_ui_extras import hookimpl
from datasette.database import MultipleValues

@hookimpl
def redirect_after_edit(datasette, database, table):
  async def inner():
    next_row = await datasette.databases[database].execute(
      'SELECT id FROM turker_queue LIMIT 1'
    )

    try:
      return '{}/{}'.format(
        datasette.urls.table(database, table),
        next_row.single_value()
      )
    except MultipleValues:
      return '/congratulations-no-more-work'

  if table == 'turker_queue':
    return inner
```
