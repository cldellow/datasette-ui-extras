(function () {
  function focusSearchBox() {
    const box = document.querySelector('.search-row #_search');

    if (!box)
      return;

    const maybeFocus = (e) => {
      const tagName = (e.target || {}).tagName;

      if (tagName === 'INPUT' || tagName === 'TEXTAREA' || tagName === 'SELECT')
        return;

      if (e.key !== '/')
        return;

      box.focus();
      box.select();
      e.preventDefault();
      return false;
    };

    document.addEventListener('keydown', maybeFocus);
  }

  addEventListener('DOMContentLoaded', focusSearchBox);
})();
