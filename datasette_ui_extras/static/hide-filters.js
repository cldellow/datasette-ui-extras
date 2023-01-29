(function () {
  const FilterOutline = `<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
  <path stroke-linecap="round" stroke-linejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 01-.659 1.591l-5.432 5.432a2.25 2.25 0 00-.659 1.591v2.927a2.25 2.25 0 01-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 00-.659-1.591L3.659 7.409A2.25 2.25 0 013 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0112 3z" />
</svg>`;

  const FilterSolid = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6">
  <path fill-rule="evenodd" d="M3.792 2.938A49.069 49.069 0 0112 2.25c2.797 0 5.54.236 8.209.688a1.857 1.857 0 011.541 1.836v1.044a3 3 0 01-.879 2.121l-6.182 6.182a1.5 1.5 0 00-.439 1.061v2.927a3 3 0 01-1.658 2.684l-1.757.878A.75.75 0 019.75 21v-5.818a1.5 1.5 0 00-.44-1.06L3.13 7.938a3 3 0 01-.879-2.121V4.774c0-.897.64-1.683 1.542-1.836z" clip-rule="evenodd" />
</svg>`

  function initialize() {
    // Only run on the table page
    if (!document.body.classList.contains('table'))
      return;

    // If _dux_show_filters 
    const me = new URL(window.location.href);
    const meWithShowFiltersToggled = new URL(window.location.href);
    const a = document.createElement('a');
    if (me.searchParams.get('_dux_show_filters') !== null) {
      document.body.classList.add('dux-show-filters');
      meWithShowFiltersToggled.searchParams.delete('_dux_show_filters');
      a.innerHTML = FilterSolid;
    } else {
      meWithShowFiltersToggled.searchParams.set('_dux_show_filters', '1');
      a.innerHTML = FilterOutline;
    }

    // Add a link that toggles the _dux_show_filters parameter
    const h3 = document.querySelector('h3');
    if (!h3)
      return;

    a.classList.add('dux-toggle-show-filters');

    a.href = meWithShowFiltersToggled.toString();

    h3.append(a);

  }
  addEventListener('DOMContentLoaded', initialize);
})();

