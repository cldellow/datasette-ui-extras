(function () {
  function initialize() {
    // Only run on the row page
    if (!document.body.classList.contains('row'))
      return;

    // Rewrite any media queries in the <style> tags in the head
    // that have 'and (max-width: 576px)'
    for (const style of [...document.querySelectorAll('head style')]) {
      style.textContent = style.textContent.replace(' and (max-width: 576px)', '');
    }

  }

  addEventListener('DOMContentLoaded', initialize);
})();
