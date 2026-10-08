"use strict";
/* The result card, shared by the main page and the stream pop-out (stream-view.html).
   app.js rolls a result into a plain object and hands it here; the pop-out gets the same object
   back out of localStorage and draws it with the same code, so the two can't drift apart.

   result = { rank, name, pills: [[label, class]], icon, main, locale, monsters,
              weapon, weaponIcon, loaner: "" | "Loaner Set 3 of 5", weaponName, challenges: [] }

   Every string goes in through textContent, never innerHTML: a challenge is user text, and the
   pop-out reads the result back from storage. */
(function () {
  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };

  // The GU randomizer's chip colours, for the fourteen classes 4U has.
  const WEAPON_COLORS = {
    "Great Sword": "#ff505b", "Long Sword": "#9beaf1", "Sword & Shield": "#dfd65f",
    "Dual Blades": "#6ac083", "Hammer": "#c3a3d2", "Hunting Horn": "#f89a64",
    "Lance": "#9fbcff", "Gunlance": "#f4baf5", "Switch Axe": "#aaaaaa",
    "Charge Blade": "#fc5800", "Insect Glaive": "#f5f5f5",
    "Light Bowgun": "#acd56b", "Heavy Bowgun": "#f8899c", "Bow": "#55edc4",
  };
  const FALLBACK_ICON = "assets/MonsterIcons/MH4U-Question_Mark_Icon.png";
  const str = (v) => typeof v === "string" ? v : "";
  const list = (v) => Array.isArray(v) ? v : [];

  function placeholder(root, text) {
    root.replaceChildren(el("p", "rc-placeholder", text));
  }

  function render(root, r) {
    const head = el("div", "rc-head");
    const icon = el("img", "rc-icon");
    icon.alt = "";
    icon.src = str(r.icon) || FALLBACK_ICON;
    icon.addEventListener("error", () => { icon.src = FALLBACK_ICON; }, { once: true });
    const text = el("div", "rc-headtext");
    text.append(el("div", "rc-rank", str(r.rank)), el("div", "rc-name", str(r.name) || "No quest matches these filters"));
    const pills = el("div", "rc-pills");
    for (const p of list(r.pills)) {
      if (Array.isArray(p) && typeof p[0] === "string") pills.appendChild(el("span", "pill " + str(p[1]), p[0]));
    }
    if (pills.childElementCount) text.appendChild(pills);
    head.append(icon, text);

    const body = el("div", "rc-body");
    const field = (label, value, cls) => {
      const f = el("div", "rc-field" + (cls ? " " + cls : ""));
      f.append(el("div", "rc-label", label), el("div", "rc-value", value));
      return f;
    };
    body.append(field("Main Objective", str(r.main) || "—", "rc-main"), field("Locale", str(r.locale) || "—"));
    if (str(r.monsters)) body.appendChild(field("Target", str(r.monsters)));

    if (str(r.weapon)) {
      const lo = el("div", "rc-field rc-loadout");
      lo.appendChild(el("div", "rc-label", str(r.loaner) || "Weapon"));
      const row = el("div", "rc-weapon-row");
      if (str(r.weaponIcon)) {
        const wi = el("img", "rc-weapon-icon");
        wi.alt = "";
        wi.src = r.weaponIcon;
        wi.addEventListener("error", () => wi.remove(), { once: true });
        row.appendChild(wi);
      }
      const chip = el("span", "rc-weapon", r.weapon);
      const hex = WEAPON_COLORS[r.weapon];
      if (hex) { chip.classList.add("chip"); chip.style.background = hex; }
      row.appendChild(chip);
      if (str(r.weaponName)) row.appendChild(el("span", "rc-weapon-name", r.weaponName));
      lo.appendChild(row);
      body.appendChild(lo);
    }

    const ch = list(r.challenges).filter(c => typeof c === "string");
    if (ch.length) {
      const box = el("div", "rc-field rc-challenges");
      box.appendChild(el("div", "rc-label", "Challenges"));
      const ul = el("ul", "rc-challenge-list");
      ch.forEach(c => ul.appendChild(el("li", null, c)));
      box.appendChild(ul);
      body.appendChild(box);
    }
    root.replaceChildren(head, body);
  }

  window.MH4U_CARD = { render, placeholder };
})();
