(function() {
  function onFormSubmit(e) {
    e.preventDefault();

    // TODO: collect values from controls and submit them

  /*
      fetch('/cooking/qtitles/1/-/update', {
          method: 'POST',
          headers: {
              'content-type': 'application/json'
          },
          body: JSON.stringify({
              update: {
                  'title': 'new title'
              }
          })
      })
        .then((response) => response.json())
        .then((data) => console.log(JSON.stringify(data, null, 2)));
  */
  }


  function initialize() {
    // Only run on the row page
    if (!document.body.classList.contains('row'))
      return;

    const form = document.querySelector('.dux-edit-form');
    if (form)
      form.addEventListener('submit', onFormSubmit);
  }

  addEventListener('DOMContentLoaded', initialize);
})();
