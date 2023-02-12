window.JSONTagsControl = class JSONTagsControl {
  constructor(initialValue, config) {
    this.autosuggestColumnUrl = config.autosuggestColumnUrl;
    this.column = config.column;
    this.initialValue = initialValue;
    this._value = JSON.parse(this.initialValue || '[]');
    this.el = null;
    this.dirty = false;
  }

  // Return a DOM element that will be shown to the user to edit this column's value
  createControl() {
    this.div = document.createElement('div');
    this.div.classList.add('dux-json-tags');
    this.ul = document.createElement('ul');
    this.div.appendChild(this.ul);

    const input = document.createElement('input');
    input.type = 'text';
    this.div.appendChild(input);
    input.addEventListener('change', () => this.dirty = true);

    const syncChanges = () => {
      const parser = new DOMParser();
      this.ul.replaceChildren();
      let i = 0;
      for (const v of this._value) {
        const li = document.createElement('li');

        const x = parser.parseFromString(
        `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 dux-remove-me">
  <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
</svg>
`, 'image/svg+xml').documentElement;
        const captured = i;
        i++;
        x.addEventListener('click', () => {
          this.dirty = true;
          this._value.splice(captured, 1);
          syncChanges();
        });

        li.appendChild(x);
        const span = document.createElement('span');
        span.innerText = v;
        li.appendChild(span);
        this.ul.appendChild(li);
      }
    }

    syncChanges();

    return [
      this.div,
      () => {
        const awesomplete = new Awesomplete(input, {
          minChars: 0,
          filter: () => { // We will provide a list that is already filtered ...
            return true;
          },
          sort: false,    // ... and sorted.
          list: []
        });

        input.addEventListener('awesomplete-selectcomplete', (e) => {
          const choice = e.text.value;
          this.dirty = true;
          this._value.push(choice);
          syncChanges();
          input.value = '';
        });

        input.addEventListener('keyup', async (e) => {
          if (e.key === 'Enter') {
            if (e.target.value) {
              this.dirty = true;
              this._value.push(e.target.value);
              syncChanges();
              input.value = '';
              return;
            }
          }
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
    return this.dirty ? JSON.stringify(this._value) : this.initialValue;
  }
};

