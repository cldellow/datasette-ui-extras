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
      choices.push(null);
    }

    choices.push(...this.config.choices);
    for (const choice of choices) {
      const opt = document.createElement('option');
      opt.value = JSON.stringify(choice);
      opt.innerText = choice === null ? 'Not set' : choice;
      if (this.initialValue === choice)
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


