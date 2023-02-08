window.TextareaControl = class TextareaControl {
  constructor(db, table, column, initialValue, dataset) {
    this.initialValue = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('textarea');
    this.el.rows = 5;
    this.el.value = this.initialValue;
    this.el.addEventListener('change', () => this.dirty = true);

    return this.el;
  }

  get value() {
    return this.dirty ? this.el.value : this.initialValue;
  }
};

