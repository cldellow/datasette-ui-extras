window.StringControl = class StringControl {
  constructor(db, table, column, initialValue) {
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
      console.log(JSON.stringify(data, null, 2));
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
      // console.log(stub);
      const { control, database, table, column, initialValue } = stub.dataset;

      const ctor = window[control];
      if (!ctor) {
        alert(`TODO: could not find constructor for edit control ${control}`);
        continue;
      }

      const parsed = JSON.parse(initialValue);
      const instance = new ctor(database, table, column, parsed);
      stub.parentElement.replaceChild(instance.createControl(), stub);
      controls[column] = instance;
    }

    const form = document.querySelector('.dux-edit-form');
    if (form)
      form.addEventListener('submit', onFormSubmit);
  }

  addEventListener('DOMContentLoaded', initialize);
})();
