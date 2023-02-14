---
title: Built-in edit controls
description: Discover the built-in edit controls of datasette-ui-extras.
---

You can use these controls by returning their name from an [`edit_control`](http://localhost:3000/docs/hooks#edit-control) hook, or reference them for inspiration when authoring your own controls.

## CheckboxControl

Renders a checkbox. Persists a `1` when checked, `0` otherwise.

See [CheckboxControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/CheckboxControl.js) on GitHub.

## DateControl

Renders a timezone-aware date picker, with optional time picker.

Persists an ISO 8601 date or timestamp string.

Options:

- `t` - if `true`, uses a `T` as the time separator; otherwise uses a space
- `utc` - if `true`, saves time in UTC timezone with a `Z` suffix; otherwise saves in user's local time with no zone suffix
- `precision` - one of `date`, `secs` or `millis`; controls whether a date or time is persisted, and with what granularity

See [DateControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/DateControl.js) on GitHub.

## DropdownControl

Renders a dropdown. Persists the `value` field.

Options:

- `choices` - an array of `{ value: "value to store"; label: "Label to show" }` objects

See [DropdownControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/DropdownControl.js) on GitHub.

## ForeignKeyControl

Renders an autocomplete box to pick a row from another table.

Options:

- `initialLabel` - the initial label to show
- `otherAutosuggestColumnUrl` - the URL of the [autosuggest endpoint](http://localhost:3000/docs/endpoints#dux-autosuggest-column)
- `labelColumn` - the column to autosuggest

See [ForeignKeyControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/ForeignKeyControl.js) on GitHub.

## JSONTagsControl

Renders a multiselect control to popular a JSON array of strings.

Options:

- `autosuggestColumnUrl` - the URL of the [autosuggest endpoint](http://localhost:3000/docs/endpoints#dux-autosuggest-column)
- `column` - the column to autosuggest

See [JSONTagsControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/JSONTagsControl.js) on GitHub.

## NumberControl

Renders a text input that saves its value as a number.

See [NumberControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/NumberControl.js) on GitHub.

## StringAutocompleteControl

Renders a free-form text input that also autocompletes against values from a column.

Options:

- `autosuggestColumnUrl` - the URL of the [autosuggest endpoint](http://localhost:3000/docs/endpoints#dux-autosuggest-column)
- `column` - the column to autosuggest

See [StringAutocompleteControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/StringAutocompleteControl.js) on GitHub.

## StringControl

Renders a free-form single-line text input.

See [StringControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/StringControl.js) on GitHub.

## TextareaControl

Renders a free-form multi-line text input.

See [TextareaControl](https://github.com/cldellow/datasette-ui-extras/blob/main/datasette_ui_extras/static/edit-row/TextareaControl.js) on GitHub.
