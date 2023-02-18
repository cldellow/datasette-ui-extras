---
title: SQL schema
description: Learn how datasette-ui-extras works with your SQL tables and views.
---

## Overview

`datasette-ui-extras` inspects your database's structure in order to present its editing user interface.

## Supported features

### Nullable columns

Nullable columns will present a radio button to determine if the column has
a value or not.

### Check constraints

A column whose choices are constrained to a list through a `CHECK` constraint
will be presented to the user as a dropdown.

```sql
CREATE TABLE options(
  color TEXT NOT NULL IN ('red', 'green', 'blue')
)
```

### Foreign key constraints

A single-column foreign key constraint will present as an autocompletable
text input. The label in the autocomplete box will be chosen using
[Datasette's rules to specify the label column](https://docs.datasette.io/en/stable/metadata.html#specifying-the-label-column-for-a-table).

```sql
CREATE TABLE country(
  id INTEGER PRIMARY KEY,
  label TEXT NOT NULL
);

CREATE TABLE person(
  name TEXT NOT NULL,
  birth_country INTEGER NOT NULL REFERENCES country(id)
);
```

### JSON string arrays

A column that contains a JSON array of strings will present as a
multi-select control with autocomplete.

```sql
CREATE TABLE person(
  name TEXT NOT NULL,
  fave_foods TEXT NOT NULL DEFAULT '["chocolate bars", "lollipops"]'
);
```

### ISO 8601 dates

Dates in ISO 8601 form like `2023-01-01` will show a date picker.

```sql
CREATE TABLE holiday(
  name TEXT NOT NULL,
  added_on TEXT NOT NULL DEFAULT DATE()
);
```

### ISO 8601 timestamps

Timestamps in ISO 8601 form like `2023-01-02 03:04:05` will show a date
picker and time picker.

The format and precision of existing rows will be matched, so formats like
`2023-01-02T03:04:05` (using `T` as the time separator) or `2023-01-02 03:04:05.000`
(with millisecond precision) are also supported.

#### A note about timezones

SQLite's [`DATETIME()`](https://www.sqlite.org/lang_datefunc.html#time_values) function always uses the UTC timezone.
Unfortunately, it produces a time like `2023-01-02 03:04:05`, which _does not tell us what timezone is being used_.

`datasette-ui-extras` treats such timestamps without timezones as local times. No interpretation is done on them. A user in Toronto will see the same time as a user in Beijing.

If your timestamp instead includes a timezone indicator, for example, `DATETIME() || 'Z'`,
`datasette-ui-extras` will recognize that it is safe to do timezone operations.
When the user edits the timestamp, we'll convert the time to their local timezone.
Before saving it, we'll convert it back to UTC and persist it as such.

## Unsupported features

The following features do not currently receive special treatment. Your
schema can still include them, but they will be more difficult to edit.

- Composite foreign keys
- Timestamps expressed as seconds-since-the-epoch or Julian days
