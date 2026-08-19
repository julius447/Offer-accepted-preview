/* =========================================================================
   Ampy offert-accepterad-sida — JS
   Fills the [data-oa] / [data-oa-href] markers from a global AMPY_OFFER
   object IF present (server injects it, or SSRs the values and this is a
   no-op). Sample values stay if AMPY_OFFER is absent.
   The check + halo animations are pure CSS (run on load); no JS needed there.
   ---------------------------------------------------------------------------
   Expected AMPY_OFFER shape (all optional; server fills from the CRM):
     {
       "offert.referens":        "#2026-0187",
       "offert.giltig_till_lang":"16 september 2026",
       "offert.url":             "https://ampy.se/offert/<token>/",
       "offert.villkor_url":     "https://ampy.se/kopvillkor"
     }
   SERVER RULE: if giltig_till_lang is missing, render the sentence WITHOUT a
   date. Never a placeholder, never a guessed date, never an empty href.
   (Name / e-post / price fields exist in the CRM but are not shown on this
   lean confirmation — kept off the page on purpose.)
   ========================================================================= */
(function () {
  var root = document.querySelector('.oa');
  if (!root) return;
  var data = window.AMPY_OFFER;
  if (!data || typeof data !== 'object') return;

  root.querySelectorAll('[data-oa]').forEach(function (el) {
    var key = el.getAttribute('data-oa');
    if (data[key] != null && data[key] !== '') el.textContent = data[key];
  });
  root.querySelectorAll('[data-oa-href]').forEach(function (el) {
    var key = el.getAttribute('data-oa-href');
    if (data[key]) el.setAttribute('href', data[key]);
  });
})();
