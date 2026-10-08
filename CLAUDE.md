# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

A static single-page web app: a quest randomizer for Monster Hunter 4 Ultimate, ported from the
[MH3U Quest Randomizer](../mh3u-quest-randomizer) (itself a port of the
[MHGU Quest Randomizer](../MHGU%20Quest%20Randomizer)). The user narrows the quest pool with
filters, presses Randomize, and gets a quest, a weapon class and any custom challenges that rolled.

No build step for the app, no framework, no modules. `docs/app.js` is one IIFE, `docs/card.js`
draws the result card, `docs/styles.css` is hand-written, `docs/data.js` is generated.

GitHub Pages serves `docs/` through the "Deploy Pages" Actions workflow on push to `master`, like
the other MH apps.

## Relationship to the 3U Quest Randomizer

A port, not a fork that tracks it. The filter panels, level trees, challenges (with Chaos Mode),
export/import, reset, theme, result card and stream pop-out are the 3U app's (and its CLAUDE.md
explains what 3U changed from GU). What changed for 4U:

- **Quest data** comes from the game via `scripts/build_data.py`. The quest decode is the
  [MH4U Hunting Log](../mh4u-hunting-log)'s, and the two `data.js` files agree field for field on
  every quest they share.
- **Boards** are Caravan 1-10★, Gathering Hall 1-7★ + G1-G3★ (stored as stars 8-10), and the
  Arena's sixteen Grudge Matches under the Hall's labels. A board lists only the stars it has
  quests on (the Arena has no 1★ or 7★), so ranks are built from the data (`RANK` in app.js), not
  from fixed star counts. ALL lays them end to end, 28 levels. Arena starts switched off.
- **Left out:** Training (one fixed set per weapon, always a Great Jaggi), the three Expeditions
  ("Return on the Wagon") and the Guild Quests (built at run time; the Hunting Log's single Guild
  Quest entry and its monster pool aren't carried over).
- **Frenzy / Apex** are two more gates under Large Monsters, from the OUTBREAK markers in the
  quest's board icons (`q.Frenzy`, `q.Apex`), with their pills.
- 14 weapon classes (Charge Blade, Insect Glaive added, with the GU app's chip colours).
- **Monsters tree** groups the large monsters under the game's own class names and order
  (HunterNote 22-35; Gore Magala is the game's "???"). The classes are hand-kept
  (`MONSTER_CLASS`); the script stops if a large monster has none. Variants the quests name apart
  (Apex, Savage Deviljho, Rusted Kushala Daora…) get their own rows.
- **Guild Card backgrounds are back** (3U dropped GU's, which were MHGU's): Theme > Content
  Background offers 64 of 4U's own, named by the game, then the flat Digital Blue / Green.
  Furry Friends (67) is left out for now (`BG_LEFT_OUT`, Raven's call): the cart gives it a
  byte-identical copy of Equipment Exhibit's picture. The saved value is `gc_bgNN` or a hex and is
  only applied if the grid offers it (`BG_OPTIONS`), so a saved gc_bg67 falls back to None.
- Storage keys are `mh4u-randomizer-*`. The theme palette is the MH4U apps' shared copy.

## Data

`python scripts/build_data.py "C:\MH4U-Extract"` rewrites `docs/data.js`
(`window.MH4U_RANDOMIZER_DATA = { quests, monsters, weaponIcons, icons, backgrounds }`), the icon
folders and `docs/assets/GuildCardBG/`. The quest files and backgrounds must be extracted first
(`python tools\arc4.py extract "loc\quest\m" "guild_card\ui_guild_"` in the extract). The script
header documents the file layout. Worth knowing:

- **Guild Card backgrounds**: the number that names a background is the `gc_bgNN.arc` number
  (GuildCard message 290 + NN), not the texture's own: from 33 on, the texture inside is named one
  higher. "Invalid Message" slots are dev placeholders and are skipped. Exported whole (512x256,
  uncropped) and shown with `cover`, swapped in on load with a latest-pick-wins counter — the
  MH3U Quest Randomizer's behaviour, at Raven's request. The game itself shows only the middle
  400x240 (layout ui505, pane ui505_bg, centred on the top screen), so the edges carry scraps the
  card never shows: Primal Forest and Volcanic Hollow have a 39 px black bar at the left. That
  trade-off is known and accepted; don't "fix" it with a crop without asking. ETC1 / ETC1A4, decoded by
  `pica_etc1.py` (checked pixel for pixel against the 3U extract's `pica_tex.py` on all 69).

- **Arena loaner sets** are in the quest file, not the executable: quest info +0x44 points at
  0x160-byte sets right after the text, weapon `{u8 type, u8, u16 number}` at +0x1c. Every Grudge
  Match has five; each Training quest has one, matching its name — the script asserts that, which
  is the check on the layout. Only the weapon is used. Kiranico's MH4U pages were unreachable, so
  nothing outside the game was checked.
- `Key` is the game's flag bit (the Hunting Log's note on where it differs from Kiranico applies).
  Don't "fix" it toward Kiranico.

## Critical: cache busting

Bump the `?v=N` on `styles.css`, `data.js`, `card.js` or `app.js` in `docs/index.html` whenever
that file changes (and on `styles.css` / `card.js` in `docs/stream-view.html`).

## Conventions

All user text goes into the DOM via `textContent`/`.value` — never `innerHTML`. Saved filters,
imported files and the stream pop-out's stored result are read back as untrusted shape
(`applyState`, `cleanChallenges`, card.js's `str`/`list` guards).
