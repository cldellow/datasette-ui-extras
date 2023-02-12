window.NumberControl = class NumberControl {
  constructor(initialValue, config) {
    this.initialValue = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('input');
    this.el.type = 'text';
    this.el.value = this.initialValue;
    this.el.addEventListener('change', () => this.dirty = true);

    return this.el;
  }

  get value() {
    if (!this.dirty)
      return this.initialValue;

    if (this.el.value === '')
      return null;

    return Number(this.el.value);
  }
};

