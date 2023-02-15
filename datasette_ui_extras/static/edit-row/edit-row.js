(function() {
  const controls = {};

  async function onFormSubmit(e) {
    e.preventDefault();

    const redirectAfterEditEndpoint = new URL(window.location.href);
    redirectAfterEditEndpoint.pathname += '/-/dux-redirect-after-edit';
    redirectAfterEditEndpoint.searchParams.set('action', 'update-row');

    const updateEndpoint = new URL(window.location.href);
    updateEndpoint.pathname += '/-/update';

    const update = {};
    for (const [k, control] of Object.entries(controls)) {
      update[k] = control.value;
    }

    try {
      {
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
          return;
        }
      }

      {
        const redirectResponse = await fetch(redirectAfterEditEndpoint.toString(), {
            method: 'GET',
        });
        const data = await redirectResponse.json();
        window.location.href = data.url;
      }

    } catch(e) {
      console.error(e);
      alert(`An error occurred while updating the row: ${JSON.stringify(e)}`);
    }
  }


  function initialize() {
    // Only run on the row page
    if (!document.body.classList.contains('row'))
      return;

    const stubs = document.querySelectorAll('.dux-edit-stub');
    for (const stub of [...stubs]) {
      const { control, initialValue, config } = stub.dataset;

      const ctor = window[control];
      if (!ctor) {
        alert(`TODO: could not find constructor for edit control ${control}`);
        continue;
      }


      const parsedConfig = JSON.parse(config);
      const parsedInitialValue = JSON.parse(initialValue);
      const instance = new ctor(parsedInitialValue, parsedConfig);

      const createControlResult = instance.createControl();

      const controlElement = Array.isArray(createControlResult) ? createControlResult[0] : createControlResult;
      stub.parentElement.replaceChild(controlElement, stub);

      if(Array.isArray(createControlResult))
        createControlResult[1]();
      controls[parsedConfig['column']] = instance;
    }

    const form = document.querySelector('.dux-edit-form');
    if (form)
      form.addEventListener('submit', onFormSubmit);
  }

  addEventListener('DOMContentLoaded', initialize);
})();

// Add an "Edit row" button on the regular row page
(function() {
  function initialize() {
    // Only run on the row page, not the edit-row page
    if (!document.body.classList.contains('row') || document.body.classList.contains('edit-row'))
      return;

    // TODO: check if user has update-row permission; maybe we embed
    //       some _dux_permissions constants via a extra_body_script?
    if (!__dux_permissions['update-row'])
      return;

    const h1 = document.querySelector('h1');

    if (!h1)
      return;

    const form = document.createElement('form');
    const button = document.createElement('input');
    button.type = 'submit';
    button.value = 'Edit data';
    form.appendChild(button);
    h1.after(form);

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const url = new URL(window.location.href);
      url.searchParams.append('_dux_edit', '1');
      window.location = url.toString();
    });
  }

  addEventListener('DOMContentLoaded', initialize);
})();
