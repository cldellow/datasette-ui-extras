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


