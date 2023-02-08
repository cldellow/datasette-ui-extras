window.StringControl = class StringControl {
  constructor(db, table, column, initialValue, dataset) {
    this.initialValue = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('input');
    this.el.value = this.initialValue;
    this.el.addEventListener('change', () => this.dirty = true);

    return this.el;
  }

  get value() {
    return this.dirty ? this.el.value : this.initialValue;
  }
};

window.StringAutocompleteControl = class StringAutocompleteControl {
  constructor(db, table, column, initialValue, dataset) {
    this.autosuggestColumnUrl = dataset.autosuggestColumnUrl;
    this.column = column;
    this.initialValue = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('input');
    this.el.value = this.initialValue;

    this.el.addEventListener('change', () => this.dirty = true);

    return [
      this.el,
      () => {
        const awesomplete = new Awesomplete(this.el, {
          minChars: 0,
          filter: () => { // We will provide a list that is already filtered ...
            return true;
          },
          sort: false,    // ... and sorted.
          list: []
        });

        this.el.addEventListener('keyup', async (e) => {
          if (e.key !== 'Backspace' && e.key.length !== 1) {
            return;
          }
          const rv = await fetch(this.autosuggestColumnUrl + '?' + new URLSearchParams({
            column: this.column,
            q: e.target.value,
          }));
          const json = await rv.json();

          const values = json.map(x => x.value);
          awesomplete.list = json.map(x => x.value);
          awesomplete.evaluate();
        });

      }
    ]
  }

  get value() {
    return this.dirty ? this.el.value : this.initialValue;
  }
};

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

window.NumberControl = class NumberControl {
  constructor(db, table, column, initialValue, dataset) {
    this.initialValue = initialValue;
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.el = document.createElement('input');
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


(function() {
  const controls = {};

  async function onFormSubmit(e) {
    e.preventDefault();

    const updateEndpoint = new URL(window.location.href);
    updateEndpoint.pathname += '/-/update';

    const update = {};
    for (const [k, control] of Object.entries(controls)) {
      update[k] = control.value;
    }

    try {
      const response = await fetch(updateEndpoint.toString(), {
          method: 'POST',
          headers: {
              'content-type': 'application/json'
          },
          body: JSON.stringify({
              update,
          })
      });
      const data = await response.json();
      if (!data.ok) {
        alert(`Error: ${data.errors.join(', ')}`);
      }
    } catch(e) {
      alert(e);
    }
  }


  function initialize() {
    // Only run on the row page
    if (!document.body.classList.contains('row'))
      return;

    const stubs = document.querySelectorAll('.dux-edit-stub');
    for (const stub of [...stubs]) {
      const { control, database, table, column, initialValue } = stub.dataset;

      const ctor = window[control];
      if (!ctor) {
        alert(`TODO: could not find constructor for edit control ${control}`);
        continue;
      }

      const parsed = JSON.parse(initialValue);
      const instance = new ctor(database, table, column, parsed, stub.dataset);

      const createControlResult = instance.createControl();

      const controlElement = Array.isArray(createControlResult) ? createControlResult[0] : createControlResult;
      stub.parentElement.replaceChild(controlElement, stub);

      if(Array.isArray(createControlResult))
        createControlResult[1]();
      controls[column] = instance;
    }

    const form = document.querySelector('.dux-edit-form');
    if (form)
      form.addEventListener('submit', onFormSubmit);
  }

  addEventListener('DOMContentLoaded', initialize);
})();
