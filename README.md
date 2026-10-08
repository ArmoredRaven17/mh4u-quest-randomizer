# MH4U Quest Randomizer

A quest randomizer for **Monster Hunter 4 Ultimate**. Narrow the pool, hit Randomize, and get a
quest and a weapon to take on it, plus any challenges of your own that rolled. A port of the
[MH3U Quest Randomizer](https://github.com/ArmoredRaven17/mh3u-quest-randomizer) (itself a port of
the [MHGU Quest Randomizer](https://github.com/ArmoredRaven17/MHGU-Quest-Randomizer)), with its
quest data read from the game itself.

```
Quest: Gathering Hall G2★ / Seer of Swords |
Monster: Seregios |
Locale: Ancestral Steppe |
Weapon: Insect Glaive |
Challenges: No Items
```

That's what **Copy to Clipboard** produces.

## Features

- **The cartridge's quest boards** — 455 quests (180 Caravan, 259 Gathering Hall, 16 Arena Grudge
  Matches), by board and star, with the Gathering Hall's G1★-G3★.
- **Filters** — by category (Urgent, Large Monsters with Capture / Multi Monster / Repel / Frenzy /
  Apex, Small Monsters, Delivery, Harvest Tours), Keys Only, any individual star, any large monster
  (grouped under the game's own class names) and any of the fourteen weapon classes. A live count
  shows how many quests are left.
- **Arena loaner sets** — an Arena roll hands you one of the quest's five loaner sets, read from
  the quest file, instead of a weapon of your own.
- **Challenges** — your own conditions, each with a chance %, rolled alongside the quest, with
  the GU app's Chaos Mode.
- **Stream view** — pops the card out on a chroma-key green background, updating with every
  roll and theme change.
- **Themes, export/import, autosave** — the MH4U monster-icon themes shared with the other MH4U
  apps; filters and challenges are saved in the browser and can be exported to a file.
- **Guild Card backgrounds** — 64 of the game's Guild Card backgrounds behind the result, or
  a flat blue/green for chroma-keying.

Downloadable Event and Challenge Quests aren't on the cartridge, so they aren't in the pool.
Guild Quests are built by the game at run time from relic data, and the Training quests and the
three Expeditions aren't hunts to roll, so those are left out too.

## Where the data comes from

[scripts/build_data.py](scripts/build_data.py) reads a local extract of a personally owned copy of
the game: the quest files (`loc\quest\mNNNNN` in `quest00.arc` / `quest01.arc`), the English
message tables, the icon atlases, the Guild Card background textures (`gc_bgNN.arc`) and two
tables in the executable. The quest decode is shared
with the [MH4U Hunting Log](https://github.com/ArmoredRaven17/mh4u-hunting-log); this repo adds
the Arena loaner sets, which sit in the quest files right after their text. The monster classes in
the Monsters filter are the one hand-kept table: the game names the classes but no table assigning
them was found. The script header documents every field.

## Running it

No build step for the app. Serve `docs/`:

```
python -m http.server 5593 --directory docs
```

## Regenerating data

Needs the extract laid out like `C:\MH4U-Extract` (romfs unpacked, arcs extracted, the quest files
and backgrounds extracted with `python tools\arc4.py extract "loc\quest\m" "guild_card\ui_guild_"`,
`code.bin` decompressed), Python 3.10+, Pillow (with WebP) and numpy:

```
python scripts/build_data.py "C:\MH4U-Extract"
```

This rewrites `docs/data.js`, `docs/assets/MonsterIcons/`, `docs/assets/WeaponIcons/` and
`docs/assets/GuildCardBG/`.

## Cache busting

GitHub Pages caches assets by full URL. When you change `styles.css`, `data.js`, `card.js` or
`app.js`, bump the `?v=N` query string on its tag in `docs/index.html` (and `docs/stream-view.html`).

## AI assistance

Most of this project — the port, the loaner-set decode and this README — was written with
[Claude Code](https://claude.com/claude-code), Anthropic's AI coding tool, working from the author's
direction and reviewed before landing.

## Licensing

Code is MIT (see [LICENSE](LICENSE)). Game data and icons are Capcom's — see [NOTICE.md](NOTICE.md).
Monster Hunter 4 Ultimate is © Capcom Co., Ltd.; this is an unofficial fan project.
