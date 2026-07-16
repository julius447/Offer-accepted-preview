/* =========================================================================
   Ampy offert-accepterad-sida — JS
   1) Fills the [data-oa] / [data-oa-href] markers from a global AMPY_OFFER
      object IF present (server can inject it, or the page SSR's the values and
      this is a no-op). Sample values stay if AMPY_OFFER is absent.
   2) Replays the check animation when the card scrolls into view.
   Scoped to .oa, no dependencies, respects reduced-motion.
   ---------------------------------------------------------------------------
   Expected AMPY_OFFER shape (all optional; server fills from the CRM):
     {
       "kund.fornamn": "Anna",
       "kund.epost": "anna@exempel.se",
       "offert.referens": "#2026-0142",
       "offert.tjanst": "Laddbox: Zaptec Go, installerad",
       "offert.arbete": "…kort omfattning…",
       "offert.pdf_url": "https://…/offert.pdf",
       "offert.villkor_url": "https://ampy.se/kopvillkor/",
       "pris.delsumma": "12 980 kr",
       "pris.avdrag_label": "Grön teknik-avdrag (50%)",
       "pris.avdrag": "−6 490 kr",
       "pris.att_betala": "6 490 kr"
     }
   ========================================================================= */
(function () {
  var root = document.querySelector('.oa');
  if (!root) return;

  // 1 · data-fill from AMPY_OFFER (if the server provided one)
  var data = window.AMPY_OFFER;
  if (data && typeof data === 'object') {
    root.querySelectorAll('[data-oa]').forEach(function (el) {
      var key = el.getAttribute('data-oa');
      if (data[key] != null && data[key] !== '') el.textContent = data[key];
    });
    root.querySelectorAll('[data-oa-href]').forEach(function (el) {
      var key = el.getAttribute('data-oa-href');
      if (data[key]) el.setAttribute('href', data[key]);
    });
  }

  // 2 · replay the check draw-in when the card enters the viewport
  if (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  if (!('IntersectionObserver' in window)) return;
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var svg = entry.target.querySelector('.oa__check-svg');
      if (svg) { var clone = svg.cloneNode(true); svg.parentNode.replaceChild(clone, svg); }
      io.unobserve(entry.target);
    });
  }, { threshold: 0.25 });
  io.observe(root);
})();
