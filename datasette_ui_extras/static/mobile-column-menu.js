(function () {
  function initialize() {
    // Only run on the table page
    if (!document.body.classList.contains('table'))
      return;


    const table = document.querySelector('.rows-and-columns');

    if (!table)
      return;

    const scrim = document.createElement('div');
    scrim.classList.add('dropdown-scrim');
    document.body.appendChild(scrim);
    scrim.addEventListener('click', () => {
      document.body.classList.remove('show-column-menu');
    });

    table.addEventListener('click', (e) => {
      const el = e.srcElement;

      if (!el)
        return;

      // This will be TR if they clicked in the cell, or A if they clicked on a link
      // in the cell.
      //
      // Only TD means that they clicked on the :before content.
      if (el.tagName !== 'TD')
        return;

      // Show the cog menu. This is a bit unfortunate - we dispatch a synthetic
      // click event to the cog, so that Datasette will wire up the appropriate
      // things on its end.

      // Figure out which column this is.
      const index = Array.prototype.indexOf.call(el.parentNode.children, el)
      if (index === -1)
        return;

      const cog = document.querySelector(`.rows-and-columns th:nth-of-type(${index + 1}) .dropdown-menu-icon`);
      if (!cog)
        return;

      document.body.classList.toggle('show-column-menu');
      const clickEvent = new MouseEvent('click', {
        view: window,
        bubbles: true,
        cancelable: true
      });
      cog.dispatchEvent(clickEvent);
    });
  }

  addEventListener('DOMContentLoaded', initialize);
})();

