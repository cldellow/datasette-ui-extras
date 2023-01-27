(function () {
  function initialize() {
    // Only run on the table page
    if (!document.body.classList.contains('table'))
      return;

    const tableWrapper = document.querySelector('.table-wrapper');

    // This is unexpected, but let's gracefully fail.
    if (!tableWrapper)
      return;

    const flexy = document.createElement('div');
    flexy.classList.add('facet-table-wrapper');
    const parent = tableWrapper.parentElement;
    parent.insertBefore(flexy, tableWrapper);

    let facetResults = document.querySelector('.facet-results');
    if (!facetResults) {
      // TODO: only create this if we know facets will be shown
      facetResults = document.createElement('div');
      facetResults.classList.add('facet-results');
    }

    flexy.insertBefore(facetResults, null);

    flexy.appendChild(tableWrapper);

  }

  addEventListener('DOMContentLoaded', initialize);
})();
