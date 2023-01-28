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
    const spinnerContainer = document.createElement('div');
    spinnerContainer.classList.add('spinner-container');
    const spinner = document.createElement('div');
    spinner.classList.add('spinner');
    spinnerContainer.appendChild(spinner);
    facetResults.appendChild(spinnerContainer);


    flexy.appendChild(tableWrapper);
    //alert(__dux_facets);

    // We hide the body tag to avoid jank when we insert the flexbox.
    // A better approach would be to ensure the HTML structure is suitable
    // at render-time, but that might require fiddling with templates in
    // a way that breaks extensibility.
    document.body.classList.add('lazy-facets-ready');
    fetchFacets(__dux_facets);
  }

  async function fetchFacets(facets) {
    const me = new URL(window.location.href);
    // Facet counts should not depend on pagination location
    me.searchParams.delete('_next');
    me.searchParams.set('_size', '0');
    me.searchParams.set('_nocount', '1');
    me.pathname += '.json';

    // Start all the fetches concurrently
    // CONSIDER: maybe we should batch these?
    const promises = [];
    for (const facet of facets) {
      const { param, source, column } = facet;
      me.searchParams.set(param, column);
      const results = fetch(me.toString())
        .then((response) => response.json())
        .then((data) => data);
      promises.push(results);
    }

    // Resolve them serially, this lets us safely insert in the right order
    let i = 0;
    while(promises.length > 0) {
      const facet = facets[i];
      i++;
      const first = await promises.shift();
      const facetInfo = first.facet_results[facet.column];

      if (!facetInfo) {
        // TODO: timed out? Show an error to the user.
        continue;
      }

      renderFacet(facetInfo);
    }

    document.body.classList.add('facets-loaded');
  }

  function renderFacet(facetInfo) {
    const facetResults = document.querySelector('.facet-results');
    const { name, results, toggle_url, hideable, type } = facetInfo;

    // Borrowed from https://github.com/simonw/datasette/blob/3c352b7132ef09b829abb69a0da0ad00be5edef9/datasette/templates/_facet_results.html
    // Some things are not implemented:
    // - the css classes for db/table/column
    // - ability to expand truncated facets
    // - nice thousands separators for counts
    const node = document.createElement('div');
    node.classList.add('facet-info');
    node.setAttribute('data-column', facetInfo.name);

    const listItems = [];
    for (const facetValue of facetInfo.results) {
      if (!facetValue.selected) {
        listItems.push(`<li><a href="${facetValue.toggle_url}" data-facet-value="${facetValue.value}">${facetValue.label || '-'}</a> ${facetValue.count}</li>`);
      } else {
        listItems.push(`<li>${facetValue.label || "-" } &middot; ${facetValue.count} <a href="${facetValue.toggle_url }" class="cross">&#x2716;</a></li>`);
      }
    }

    node.innerHTML = `
<p class="facet-info-name">
    <strong>${facetInfo.name}${ facetInfo.type !== 'column' ? ` (${facetInfo.type})` : ''}
        <span class="facet-info-total">${ facetInfo.truncated ? '&gt; ' : '' }${facetInfo.results.length}</span>
    </strong>
    ${facetInfo.hideable ? `<a href="${facetInfo.toggle_url}" class="cross">&#x2716;</a>` : ''}
    <ul class="tight-bullets">
    ${listItems.join('\n')}
    </ul>
</p>
`;

    facetResults.insertBefore(node, document.querySelector('.spinner-container'));
  }

  addEventListener('DOMContentLoaded', initialize);
})();
