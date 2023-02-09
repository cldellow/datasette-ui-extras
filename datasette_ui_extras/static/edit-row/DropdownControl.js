window.DropdownControl = class DropdownControl {
  constructor(initialValue, config) {
    this.config = config;
    this.initialValue = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('select');
    this.el.value = this.initialValue;

    const choices = [];
    if (this.config.nullable) {
      choices.push({value: null, label: 'Not set'});
    }

    choices.push(...this.config.choices);
    for (const choice of choices) {
      const opt = document.createElement('option');
      opt.value = JSON.stringify(choice.value);
      opt.innerText = choice.label;

      if (this.initialValue === choice.value)
        opt.selected = true;

      this.el.appendChild(opt);
    }

    this.el.addEventListener('change', () => this.dirty = true);

    return this.el;
  }

  get value() {
    return this.dirty ? JSON.parse(this.el.value) : this.initialValue;
  }
};


