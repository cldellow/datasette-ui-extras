window.ForeignKeyControl = class ForeignKeyControl {
  constructor(initialValue, config) {
    this.config = config;
    this.initialValue = initialValue;
    this.value_ = initialValue;
    this.dirty = false;
  }

  createControl() {
    const autosuggest = document.createElement('input');
    autosuggest.classList.add('dux-fkey-picker');
    this.el = autosuggest;

    autosuggest.type = 'text';

    if (this.config.initialLabel)
      autosuggest.value = this.config.initialLabel;

    let setInput;
    if (this.config.nullable) {
        this.el = document.createElement('div');
        this.el.classList.add('dux-nullable-fkey-picker');

        const notSetInput = document.createElement('input');
        notSetInput.type = 'radio';
        notSetInput.name = this.config.column;
        notSetInput.id = notSetInput.name + '-null';
        notSetInput.value = 'null';
        if (this.initialValue == null) notSetInput.checked = true;
        this.notSetInput = notSetInput;
        notSetInput.addEventListener('change', () => this.dirty = true);
        this.el.appendChild(notSetInput);

        const notSetLabel = document.createElement('label');
        notSetLabel.innerText = 'Not set';
        notSetLabel.htmlFor = this.config.column + '-null';
        this.el.appendChild(notSetLabel);

        setInput = document.createElement('input');
        setInput.type = 'radio';
        setInput.name = this.config.column;
        setInput.value = 'set';
        setInput.addEventListener('change', () => this.dirty = true);
        this.el.appendChild(setInput);
        if (this.initialValue !== null) setInput.checked = true;

        this.el.appendChild(autosuggest);
    }

    return [
      this.el,
      () => {
        const awesomplete = new Awesomplete(autosuggest, {
          minChars: 0,
          filter: () => { // We will provide a list that is already filtered ...
            return true;
          },
          sort: false,    // ... and sorted.
          list: []
        });

        autosuggest.addEventListener('keyup', async (e) => {
          if (e.key !== 'Backspace' && e.key.length !== 1) {
            return;
          }
          const rv = await fetch(this.config.otherAutosuggestColumnUrl + '?' + new URLSearchParams({
            column: this.config.labelColumn,
            q: e.target.value,
          }));
          const json = await rv.json();

          const values = [];
          for (const row of json) {
            for (const pk of row.pks) {
              values.push({
                label: row.value,
                value: pk
              });
            }
          }
          awesomplete.list = values;
          awesomplete.evaluate();
        });

        autosuggest.addEventListener('awesomplete-selectcomplete', (e) => {
          console.log(e);

          const pkeys = Object.values(e.text.value);
          if (pkeys.length !== 1) {
            alert(`datasette-ui-extras: expected a single pkey, but got ${JSON.stringify(e.text.value)}`);
            return;
          }

          this.value_ = pkeys[0];
          this.dirty = true;
          autosuggest.value = e.text.label;
          if (setInput)
            setInput.checked = true;

        });


      }
    ]
  }

  get value() {
    if (this.dirty) {
      if (this.notSetInput && this.notSetInput.checked)
        return null;

      return this.value_;
    }

    return this.initialValue;
  }
}
