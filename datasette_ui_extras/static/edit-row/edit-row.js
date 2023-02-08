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
