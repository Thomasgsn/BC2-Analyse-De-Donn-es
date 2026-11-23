/* Corrige la sémantique des contrôles Dash 4.5, sans modifier leurs événements.
   Vérifié par Chromium/axe et navigation clavier dans tests/integration/browser.py. */
(function () {
  function repair() {
    for (const id of ['segment', 'level']) {
      const trigger = document.getElementById(id);
      if (!trigger) continue;
      const wrapper = trigger.closest('.dash-dropdown-wrapper');
      const focus = wrapper && wrapper.querySelector('.dash-dropdown-focus-target');
      if (focus) {
        if (focus.hasAttribute('aria-hidden')) focus.removeAttribute('aria-hidden');
        const label = document.querySelector('label[for="' + id + '"]');
        if (label && focus.getAttribute('aria-label') !== label.textContent) focus.setAttribute('aria-label', label.textContent);
      }
    }
    for (const [id, name] of [['market-mode', 'Indicateur financier'], ['macro-series', 'Série macro-économique'], ['macro-period', 'Période affichée']]) {
      const group = document.getElementById(id);
      if (!group) continue;
      if (group.getAttribute('role') !== 'radiogroup') group.setAttribute('role', 'radiogroup');
      if (!group.hasAttribute('aria-label')) group.setAttribute('aria-label', name);
      group.querySelectorAll('label').forEach(label => {
        if (label.hasAttribute('role')) label.removeAttribute('role');
        if (label.hasAttribute('aria-selected')) label.removeAttribute('aria-selected');
      });
    }
  }
  new MutationObserver(repair).observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['role', 'aria-selected', 'aria-hidden']});
  document.addEventListener('DOMContentLoaded', repair);
})();
