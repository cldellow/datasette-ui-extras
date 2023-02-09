window.CheckboxControl = class CheckboxControl {
  constructor(initialValue, config) {
    this.config = config;
    this.value_ = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('input');
    this.el.type = 'checkbox';
    this.el.checked = this.value_ !== '0' && this.value !== 0;
    this.el.addEventListener('change', () => {
      this.dirty = true;
      this.value_ = this.el.checked ? 1 : 0;
    });

    return this.el;
  }

  get value() {
    return this.value_;
  }
};


