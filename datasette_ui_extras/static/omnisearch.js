(function () {
  function initialize() {
    // Only run on the table page
    if (!document.body.classList.contains('table'))
      return;

    const search = document.querySelector('#_search');

    if (!search)
      return;

    const awesomplete = new Awesomplete(search, {
      minChars: 0,
      filter: () => { // We will provide a list that is already filtered ...
        return true;
      },
      sort: false,    // ... and sorted.
      list: []
    });

    search.addEventListener('input', async (e) => {
      const me = new URL(window.location.href);
      me.pathname += '/-/dux-omnisearch';
      me.searchParams.set('q', e.target.value);

      const rv = await fetch(me.toString());

      const json = await rv.json();

      const values = [];
      for (const row of json) {
        values.push({
          label: row.value,
          value: row.url
        });
      }
      awesomplete.list = values;
      awesomplete.evaluate();
    });

    search.addEventListener('awesomplete-select', (e) => {
      e.preventDefault();
      window.location.href = e.text.value;
    });
  }

  addEventListener('DOMContentLoaded', initialize);
})();
