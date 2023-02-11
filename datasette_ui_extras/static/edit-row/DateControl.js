window.DateControl = (function () {
  const pad = (x) => {
    const rv = String(x);
    if (rv.length < 2)
      return '0' + rv;

    return rv;
  }

  const strftime = (format, date, utc) => {
    return format.replace(/%[a-z]+\b/gi, (needle) => {
      // We support a very stripped down set of strftime formatters!
      if (needle == '%Y')
        return utc ? date.getUTCFullYear() : date.getFullYear();
      if (needle == '%m')
        return pad((utc ? date.getUTCMonth() : date.getMonth()) + 1);
      if (needle == '%d')
        return pad(utc ? date.getUTCDate() : date.getDate());
      if (needle == '%H')
        return pad(utc ? date.getUTCHours() : date.getHours());
      if (needle == '%M')
        return pad(utc ? date.getUTCMinutes() : date.getMinutes());

      return needle;
    });
  };

  const extract = (date) => {
    {
      const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec(date);

      if (m) {
        return {
          year: Number(m[1]),
          month: Number(m[2]),
          day: Number(m[3]),
          hour: 0,
          minute: 0,
        }
      }
    }

    {
      const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2})[T ]([0-9]{2}):([0-9]{2})[:.0-9]+Z?$/.exec(date);

      if (m) {
        return {
          year: Number(m[1]),
          month: Number(m[2]),
          day: Number(m[3]),
          hour: Number(m[4]),
          minute: Number(m[5]),
        }
      }
    }

    const d = new Date();

    return {
      year: d.getFullYear(),
      month: d.getMonth() + 1,
      day: d.getDate(),
      hour: d.getHours(),
      minute: d.getMinutes(),
    }
  }

  const USLocale = {
    days: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    daysShort: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
    daysMin: ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'],
    months: ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    monthsShort: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    today: 'Today',
    clear: 'Clear',
    dateFormat: 'yyyy-MM-dd',
    timeFormat: 'hh:mm aa',
    firstDay: 0
  };

  return class DateControl {
    constructor(initialValue, config) {
      this.config = config;
      this.value_ = initialValue;
      this.initialValue = initialValue;
      this.dirty = false;
    }

    // Return a DOM element that will be shown to the user to edit this column's value
    createControl() {
      this.el = document.createElement('input');
      this.el.readOnly = true;

      const { year, month, day, hour, minute } = extract(this.initialValue || '');

      const date = this.config.utc ? new Date(Date.UTC(year, month - 1, day, hour, minute)) : new Date(year, month - 1, day, hour, minute);
      const t = this.config.t ? 'T' : ' ';
      const z = this.config.utc ? 'Z' : '';
      const precision = this.config.precision;

      return [
        this.el,
        () => {
          new AirDatepicker(this.el, {
            locale: USLocale,
            selectedDates: date,
            timepicker: precision !== 'date',
            onSelect: ({date}) => {
              this.dirty = true;

              if (precision === 'date')
                // Date is special; ignore UTC flag
                return this.value_ = strftime('%Y-%m-%d', date, false);

              if (precision === 'millis')
                return this.value_ = strftime(`%Y-%m-%d${t}%H:%M:00.000${z}`, date, this.config.utc);

              if (precision === 'secs')
                return this.value_ = strftime(`%Y-%m-%d${t}%H:%M:00${z}`, date, this.config.utc);

            }
          });
        }
      ]
    }

    get value() {
      return this.dirty ? this.value_ : this.initialValue;
    }
  }
})();


