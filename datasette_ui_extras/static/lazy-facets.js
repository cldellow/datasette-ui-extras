(function () {
  function initialize() {
    // Only run on the table page
    if (!document.body.classList.contains('table'))
      return;

    const tableWrapper = document.querySelector('.table-wrapper');

    // This is unexpected, but let's gracefully fail.
    if (!tableWrapper) {
      document.body.classList.add('lazy-facets-ready');
      return;
    }

    const flexy = document.createElement('div');
    flexy.classList.add('facet-table-wrapper');
    const parent = tableWrapper.parentElement;
    parent.insertBefore(flexy, tableWrapper);

    let facetResults = document.querySelector('.facet-results');
    if (!facetResults) {
      if (__dux_facets.length === 0) {
        document.body.classList.add('lazy-facets-ready');
        return;
      }

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

    // We hide the body tag to avoid jank when we insert the flexbox.
    // A better approach would be to ensure the HTML structure is suitable
    // at render-time, but that might require fiddling with templates in
    // a way that breaks extensibility.
    document.body.classList.add('lazy-facets-ready');
    fetchFacets(__dux_facets);
  }

  function urlWithReplacedArgs(href, obj) {
    if (!href.startsWith('http:') && !href.startsWith('https:')) {
      href = window.location.protocol + '//' + window.location.host + href;
    }
    const url = new URL(href);
    for (const [k, v] of Object.entries(obj)) {
      if (v === null)
        url.searchParams.delete(k);
      else {
        url.searchParams.set(k, v);
      }
    }

    return url.toString();
  }

  function fixupToggleUrl(toggle_url, oldQueryParams) {
    if (!toggle_url.startsWith('http:') && !toggle_url.startsWith('https:')) {
      toggle_url = window.location.protocol + '//' + window.location.host + toggle_url;
    }
    const url = new URL(toggle_url);
    for (const [k, v] of Object.entries(oldQueryParams)) {
      if (v === null)
        url.searchParams.delete(k);
      else {
        url.searchParams.set(k, v);
      }
    }

    url.pathname = url.pathname.replace('.json', '');
    return url.toString();
  }

  async function fetchFacets(facets) {
    const me = new URL(window.location.href);
    // Facet counts should not depend on pagination location

    // TODO: we should stash the old values for _next/_size/_nocount and restore them
    //       on each toggle_url that comes back
    const oldQueryParams = {
      '_next': me.searchParams.get('_next'),
      '_size': me.searchParams.get('_size'),
      '_nocount': me.searchParams.get('_nocount'),
      '_dux_facet': null,
      '_dux_facet_column': null,
    };
    me.searchParams.delete('_next');
    me.searchParams.set('_size', '0');
    me.searchParams.set('_nocount', '1');
    me.pathname += '.json';

    // Start all the fetches concurrently
    // CONSIDER: maybe we should batch these?
    const promises = [];
    for (const facet of facets) {
      const { param, source, column } = facet;
      me.searchParams.set('_dux_facet', param);
      me.searchParams.set('_dux_facet_column', column);
      const results = fetch(me.toString())
        .then((response) => response.json())
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
        renderFailedFacet(facet);
        continue;
      }

      facetInfo.toggle_url = fixupToggleUrl(facetInfo.toggle_url, oldQueryParams);
      for (const facetValue of facetInfo.results) {
        facetValue.toggle_url = fixupToggleUrl(facetValue.toggle_url, oldQueryParams);
      }

      renderFacet(facetInfo);
    }

    document.body.classList.add('facets-loaded');
  }

  function renderFailedFacet(facet) {
    const facetResults = document.querySelector('.facet-results');

    const node = document.createElement('div');
    node.classList.add('facet-info');
    node.setAttribute('data-column', facet.column);

    node.innerHTML = `
<p class="facet-info-name">
    <strong>${facet.column}</strong>
    <ul class="tight-bullets">
      <li>Computing this facet timed out.</li>
    </ul>
</p>
`;

    facetResults.insertBefore(node, document.querySelector('.spinner-container'));

  }

  function renderFacet(facetInfo) {
    const facetResults = document.querySelector('.facet-results');

    // Borrowed from https://github.com/simonw/datasette/blob/3c352b7132ef09b829abb69a0da0ad00be5edef9/datasette/templates/_facet_results.html
    // Some things are not implemented:
    // - the css classes for db/table/column
    // - ability to expand truncated facets
    const node = document.createElement('div');
    node.classList.add('facet-info');
    node.setAttribute('data-column', facetInfo.name);

    const listItems = [];
    for (const facetValue of facetInfo.results) {
      if (!facetValue.selected) {
        listItems.push(`<li><a href="${facetValue.toggle_url}" data-facet-value="${facetValue.value}">${facetValue.label || '-'}</a> ${facetValue.count.toLocaleString()}</li>`);
      } else {
        listItems.push(`<li>${facetValue.label || "-" } &middot; ${facetValue.count.toLocaleString()} <a href="${facetValue.toggle_url }" class="cross">&#x2716;</a></li>`);
      }
    }

    const askedForFacetSizeMax = window.location.search.indexOf('_facet_size=max') >= 0;
    let maybeMax = '';
    if (facetInfo.truncated) {
      maybeMax = `
<li class="facet-truncated">${ !askedForFacetSizeMax ? `<a href="${urlWithReplacedArgs(window.location.href, { _facet_size: 'max' })}">…</a>` : `…`}
                    </li>
      `;
    }
    node.innerHTML = `
<p class="facet-info-name">
    <strong>${facetInfo.name}${ facetInfo.type !== 'column' ? ` (${facetInfo.type})` : ''}
        <span class="facet-info-total">${ facetInfo.truncated ? '&gt; ' : '' }${facetInfo.results.length}</span>
    </strong>
    ${facetInfo.hideable ? `<a href="${facetInfo.toggle_url}" class="cross">&#x2716;</a>` : ''}
    <ul class="tight-bullets">
    ${listItems.join('\n')}
    ${maybeMax}
    </ul>
</p>
`;

    facetResults.insertBefore(node, document.querySelector('.spinner-container'));
  }

  addEventListener('DOMContentLoaded', initialize);
})();
