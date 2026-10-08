"use strict";
/* Stream pop-out: mirrors the main window's last roll and theme. Both arrive through
   localStorage — the main window writes them, and the "storage" event fires in every OTHER
   same-origin window, which is exactly this one. */
(function () {
  const RESULT_KEY = "mh4u-randomizer-last-result";
  const THEME_VARS_KEY = "mh4u-randomizer-theme-vars";
  const card = document.getElementById("card");

  function showResult(json) {
    let r = null;
    try { r = JSON.parse(json || "null"); } catch (e) {}
    if (r && typeof r === "object") window.MH4U_CARD.render(card, r);
    else window.MH4U_CARD.placeholder(card, "Waiting for a roll from the main app…");
  }
  // Only the variables the main app derives, and only colour strings, since storage is shared
  // with every app on this origin.
  function showTheme(json) {
    let vars = null;
    try { vars = JSON.parse(json || "null"); } catch (e) {}
    if (!vars || typeof vars !== "object") return;
    for (const [k, v] of Object.entries(vars)) {
      if (/^--[a-z0-9-]+$/.test(k) && /^rgb\(\d+,\d+,\d+\)$/.test(v)) document.documentElement.style.setProperty(k, v);
    }
  }

  window.addEventListener("storage", (e) => {
    if (e.key === RESULT_KEY) showResult(e.newValue);
    if (e.key === THEME_VARS_KEY) showTheme(e.newValue);
  });
  try {
    showTheme(localStorage.getItem(THEME_VARS_KEY));
    showResult(localStorage.getItem(RESULT_KEY));
  } catch (e) {
    showResult(null);
  }
})();
