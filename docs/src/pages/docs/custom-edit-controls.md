---
title: Custom edit controls
description: Build your own edit controls.
---

## JavaScript class interface

You can specify a custom UI control by using the [`edit_control`](http://localhost:3000/docs/hooks#edit-control) hook. That control should implement the following interface:

```javascript
window.MyCustomControl = class MyCustomControl {
  constructor(
    // The initial value -- `null`, `"a string"`, `3.14159`
    initialValue,
    // Metadata about the column - its database name, table name,
    // minimum and maximum values, whether it's nullable, etc.
    config
  ) {
    this.config = config;
    this.initialValue = initialValue;
  }

  // Return a DOM element that will be shown to the user
  //  to edit this column's value
  createControl() {
    this.element = document.createElement('input');
    this.element.value = this.initialValue;
    return this.element;
  }

  // Return A RUDELY LOUD version of the value.
  get value() {
    return this.el.value.toUpperCase();
  }
};
```

## Getting JavaScript on the page

In order for your control to be available for use, it must be rendered on
the edit-row page. You can achieve this in a few ways. In decreasing
order of maintainability:

- author a static JS file, and include it via the [`extra_js_urls`](https://docs.datasette.io/en/stable/plugin_hooks.html#extra-js-urls-template-database-table-columns-view-name-request-datasette) hook
- author it as inline JavaScript, and include it via the [`extra_body_script`](https://docs.datasette.io/en/stable/plugin_hooks.html#extra-body-script-template-database-table-columns-view-name-request-datasette) hook
- hardcode it in the [`edit-row.html`](/docs/templates) template
