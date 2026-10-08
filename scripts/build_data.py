r"""Build the randomizer's quest data and icons from a local MH4U extract.

    python scripts/build_data.py [C:\MH4U-Extract]

Reads only the game itself (plus the hand-kept MONSTER_CLASS table below) and writes:

    docs/data.js                          window.MH4U_RANDOMIZER_DATA = { quests, monsters, weaponIcons, icons, backgrounds }
    docs/assets/MonsterIcons/MH4U-*.png   the game's monster and quest-type icons
    docs/assets/WeaponIcons/icon_*.png    the game's weapon-class icons
    docs/assets/GuildCardBG/gc_bgNN.webp  the Guild Card backgrounds (and thumbs/gc_bgNN.webp)

The quest decode is the MH4U Hunting Log's (its scripts/build_data.py has the long header, and the
two data.js files agree field for field on every quest they share); what is new here is the Arena
loaner sets and the monster classes. The extract layout is the MH4U Collection Tracker's: romfs
unpacked from the cart image, ARC entries under arcx\ (the extract's tools\arc4.py; the quests need
`python arc4.py extract "loc\quest\m"`), code.bin decompressed. 4U's text is LMD (lmd_messages).

QUEST FILES -- romfs loc/data/quest00.arc and quest01.arc, entries loc\quest\mNNNNN (type hash
1bbfd18e), one per quest; a few sit in both arcs, byte for byte. DLC quests are not on the cart.
  Header: u32 quest info offset (0xa0), 'v005', then section offsets. +0x28 -> a 0-terminated list
  of large-monster waves; each wave is a run of 0x28-byte records, u32 monster number first,
  0xffffffff ends it. The waves are every large monster the quest spawns, intruders included.
  Quest info (at +0xa0):
    +0x00 u8   quest type: 1 slay, 2 capture, 3 hunt, 4 deliver, 8 several monsters, 16 special
    +0x01 u8   flags: 0x04 repel allowed, 0x10 Urgent, 0x20 Key
    +0x1c u32  -> five language tables (English first) of seven string offsets: name, main
               objective, failure condition, description, small monsters, client, subquest.
               Strings are UTF-16LE, 0-terminated, in the quest file itself.
    +0x20 u16  quest number (= the file name), +0x22 u8 star, +0x24 u8 map (mapName id)
    +0x2c 8 bytes x3   objectives: two main, then the subquest. u8 kind (1 slay/hunt, 0x81
               capture, 2 deliver -- target = item number, 4 break/wound/mount), u8, u16,
               u16 target (monster or item number), u16 count
    +0x44 u32  -> the quest's loaner sets (ARENA LOANERS below), 0 on every other quest
    +0x48 u16 x5  the quest's icons on the board (cells of cmn_micon; 98 = none). Slot 0 is the
               quest's own; the markers 84 (DANGER) / 88 (OUTBREAK: frenzied monsters) / 123 (the
               red OUTBREAK: Apex monsters) join the later slots.

ARENA LOANERS -- the block the info's +0x44 points at, right after the text: sets of 0x160 bytes,
  each opening with u32 2 (the run ends at the first set that doesn't). In a set:
    +0x1c  equipment {u8 type, u8, u16 number}: the weapon. Type 7-20 is the class (TYPES below,
           the same item types the Collection Tracker reads), number = index into the class's
           weapon-name table. The second byte is the Kinsect on a glaive and a bowgun setting on
           LBG/HBG; the randomizer doesn't use it.
    +0x38  five 0x1c-byte armor slots (types 1, 3, 2, 4, 5), +0xc4 the talisman (type 6),
    +0x100 the item pouch as (u16 item, u16 count) -- not used here.
  All sixteen Grudge Matches carry five sets; the fourteen Training quests carry one, the weapon
  their name gives (Training: Bow -> a Bow), which is how the weapon field was confirmed. The
  game's own text asks "Choose your equipment." (C_counter 64) on the Arena counter. Kiranico's
  MH4U pages were unreachable (HTTP 500), so the sets were checked against nothing outside the game.

GUILD CARD BACKGROUNDS -- romfs loc/data/gc_bgNN.arc, one texture each, lyt\lobby\guild_card\
  ui_guild_MM_ID (extract with `python arc4.py extract "guild_card\ui_guild_"`). 512x256, ETC1 or
  ETC1A4 (pica_etc1.py). The background's number is the arc's NN: its name is GuildCard message
  290 + NN, which lines up with the art throughout (1 Ancestral Steppe, 9 Bird Wyvern Hues, 33
  Square Enix, 44 Super Mario, 77 Sonic). From gc_bg33 on, the texture inside is named one number
  higher (gc_bg33 holds ui_guild_34_ID); the arc number is the one the names follow. Numbers 27-32
  (Jump, Famitsu, Dengeki...) have no arc on the cart. The four whose name is "Invalid Message"
  (69, 86, 88, 89) are the "dummy_20" / "dummy_39" / "dummy_40" placeholders and a black page,
  and are skipped. So is 67 "Furry Friends" (BG_LEFT_OUT): its arc holds ui_guild_68, which is
  byte-identical to 57 "Equipment Exhibit"'s ui_guild_58 -- the two arcs differ only in that digit
  of the entry name, both verified against the cart's IVFC hash tree, and the game loads each from
  its own arc. The picture (hunters in assorted armour with Felynes) reads as Equipment Exhibit's.
  Written whole (512x256, pixels unchanged) as lossless WebP plus a 192x96
  thumbnail, the same as the MH3U Quest Randomizer (Raven's call, 2026-10-08).
  Note the game shows only the middle 400x240 (x 56-456, y 8-248): the Guild Card layout (lobby
  ui505) draws them in pane ui505_bg, 512x256 with UVs 0-1, centred on the 400x240 top screen, and
  every copyright line ends just inside that window. The edges outside it hold scraps the card never
  shows -- Primal Forest and Volcanic Hollow have a 39 px black bar at the left -- and they are kept.

MONSTER CLASSES -- kept by hand, spelled out in full, as in the MH3U randomizer (whose header
  explains the search for a class table that came up empty there). The script stops if a large
  monster has no class, so a rebuild can't silently leave one out of the Monsters filter. Variants
  that share their base monster's game name (Apex, Savage, Rusted...) are VARIANTS-named and get
  their own row, since the quests name them apart.

Needs: Python 3.10+, Pillow (with WebP), numpy. pica_la4.py and pica_etc1.py (beside this script)
decode the textures.
"""
import collections, glob, json, os, re, struct, sys

EXTRACT = sys.argv[1] if len(sys.argv) > 1 else r'C:\MH4U-Extract'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CODE = open(os.path.join(EXTRACT, 'exefs', 'code.decompressed.bin'), 'rb').read()
BASE = 0x100000
QUESTS = glob.glob(os.path.join(EXTRACT, 'arcx', 'loc', 'data', 'quest0*', 'loc', 'quest', 'm*.1bbfd18e'))
ENG = os.path.join(EXTRACT, 'arcx', 'eng', 'data')
MSG = os.path.join(ENG, 'core_common', 'eng', 'msg')
TEXTURES = os.path.join(ENG, 'core_common', 'eng', 'lyt', 'common', 'texture')
GUILD_BG = os.path.join(EXTRACT, 'arcx', 'loc', 'data', 'gc_bg*')
MONSTER_TEX = os.path.join(TEXTURES, 'cmn_micon_BM_MQ_NOMIP.241f5deb')
ICON_TEX = os.path.join(TEXTURES, 'cmn_icon_GSM_NOMIP.241f5deb')

QUEST_ORDER = 0xefce2a
LOANER_SET = 0x160        # bytes per Arena loaner set
BG_LEFT_OUT = {67}        # Furry Friends: the cart gives it Equipment Exhibit's picture (see above)


def lmd_messages(path):
    """LMD (type 62440501) -> messages by the id the game asks for. Same reader as the Hunting
    Log's and the Collection Tracker's."""
    b = open(path, 'rb').read()
    assert b[:4] == b'lmd\0', path
    nmsg, nops, nstr = struct.unpack_from('<3I', b, 8)
    oops, ostr = struct.unpack_from('<2I', b, 0x18)
    pool = []
    for i in range(nstr):
        p, n, _ = struct.unpack_from('<3I', b, ostr + 12 * i)
        pool.append(b[p:p + 2 * n].decode('utf-16-le'))
    out = []
    for i in range(nmsg):
        k = struct.unpack_from('<IHH', b, 0x24 + 8 * i)[1]
        s = ''
        while k != 0xffff and k < nops:
            op, arg = struct.unpack_from('<2I', b, oops + 16 * k)
            if op == 22:
                break
            s += pool[arg] if op == 1 else ''
            k += 1
        out.append(s)
    return out


def msg(name): return lmd_messages(os.path.join(MSG, name + '_eng.62440501'))


EM = msg('emName')
ITEMS = msg('itemName')
COMMON = msg(os.path.join('common', 'Common'))
MAPS = msg(os.path.join('common', 'mapName'))
CARD = lmd_messages(os.path.join(ENG, 'core_lobby', 'eng', 'msg', 'lobby', 'GuildCard_eng.62440501'))

# mapName id -> locale, spelled out where the Guild Card spells it (the Hunting Log's LOCALES).
LOCALES = {i: s for i, s in enumerate(MAPS) if s}
for i, card in zip((1, 2, 3, 4, 15, 5), range(291, 297)):
    LOCALES[i] = CARD[card]
for i, pat in ((7, r'(Tower Summit)'), (8, r'(Speartip Crag)'), (10, r'(Castle Schrade)')):
    LOCALES[i] = re.search(pat, CARD[1795] + ' ' + CARD[1799]).group(1)

# Monster numbers whose emName entry repeats the base monster's name (the Hunting Log's VARIANTS).
VARIANTS = {
    43: 'Savage Deviljho', 45: 'Furious Rajang', 78: 'Crimson Fatalis', 82: 'Rusted Kushala Daora',
    97: 'Chaotic Gore Magala', 112: 'Apex Rajang', 113: 'Apex Deviljho', 114: 'Apex Zinogre',
    115: 'Apex Gravios', 117: 'White Fatalis', 119: 'Apex Diablos', 120: 'Apex Tidal Najarala',
    121: 'Apex Tigrex', 122: 'Apex Seregios',
}
def monster(em): return VARIANTS.get(em) or EM[em]

ITEM_CELLS = {84: 'Danger', 86: 'Chest', 88: 'Outbreak', 89: 'Egg', 90: 'Ore', 91: 'Fish', 92: 'Bone',
              93: 'Herb', 94: 'Mushroom', 95: 'Honey', 96: 'Scroll', 123: 'Apex Outbreak'}
NO_ICON, QUESTION_CELL, DANGER, FRENZY, APEX = 98, 0, 84, 88, 123

# Weapon classes in the GU apps' order: (item type, slug, name table). Label = Common 36 + type.
TYPES = [
    (7, 'great_sword', 'LswordName'), (13, 'long_sword', 'Lsword2Name'),
    (8, 'sword_and_shield', 'SwordName'), (17, 'dual_blades', 'WswordName'),
    (9, 'hammer', 'HammerName'), (18, 'hunting_horn', 'Hammer2Name'),
    (10, 'lance', 'LanceName'), (15, 'gunlance', 'Lance2Name'),
    (14, 'switch_axe', 'AxeName'), (20, 'charge_blade', 'GaxeName'), (19, 'insect_glaive', 'RodName'),
    (11, 'light_bowgun', 'LightName'), (12, 'heavy_bowgun', 'HeavyName'), (16, 'bow', 'BowName'),
]
ICON_CELL_TABLE, CLASS_OF = 0xfb8125, 0xf5f2fc

# The boards the randomizer rolls from. Training (one fixed set per weapon, always a Great Jaggi),
# the three Expeditions ("Return on the Wagon") and the Guild Quests (built at run time from relic
# data) are left out.
BOARDS = ('Caravan', 'Gathering Hall', 'Arena')

# Hand-kept (see MONSTER CLASSES above). Every large monster on the kept boards' quests. Class
# names and order are the game's (HunterNote 22-35); Gore Magala is its "???" (HunterNote 20).
MONSTER_CLASS = {
    'Flying Wyvern': ['Rathian', 'Pink Rathian', 'Gold Rathian', 'Rathalos', 'Azure Rathalos',
                      'Silver Rathalos', 'Tigrex', 'Brute Tigrex', 'Molten Tigrex', 'Apex Tigrex',
                      'Khezu', 'Red Khezu', 'Basarios', 'Gravios', 'Black Gravios', 'Apex Gravios',
                      'Diablos', 'Black Diablos', 'Apex Diablos', 'Monoblos', 'White Monoblos',
                      'Seregios', 'Apex Seregios', 'Akantor', 'Ukanlos'],
    'Bird Wyvern': ['Yian Kut-Ku', 'Blue Yian Kut-Ku', 'Gypceros', 'Purple Gypceros', 'Yian Garuga',
                    'Great Jaggi', 'Velocidrome', 'Gendrome', 'Iodrome'],
    'Fanged Beast': ['Congalala', 'Emerald Congalala', 'Rajang', 'Furious Rajang', 'Apex Rajang',
                     'Kecha Wacha', 'Ash Kecha Wacha', 'Lagombi'],
    'Amphibian': ['Tetsucabra', 'Berserk Tetsucabra', 'Zamtrios', 'Tigerstripe Zamtrios'],
    'Snake Wyvern': ['Najarala', 'Tidal Najarala', 'Apex Tidal Najarala', 'Dalamadur', 'Shah Dalamadur'],
    'Elder Dragon': ['Kushala Daora', 'Rusted Kushala Daora', 'Teostra', 'Chameleos', 'Kirin',
                     'Oroshi Kirin', 'Shagaru Magala', "Dah'ren Mohran", 'Fatalis', 'Crimson Fatalis',
                     'White Fatalis', 'Gogmazios'],
    'Neopteron': ['Seltas', 'Desert Seltas', 'Seltas Queen', 'Desert Seltas Queen'],
    'Temnoceran': ['Nerscylla', 'Shrouded Nerscylla'],
    'Brute Wyvern': ['Deviljho', 'Savage Deviljho', 'Apex Deviljho', 'Brachydios', 'Raging Brachydios'],
    'Fanged Wyvern': ['Zinogre', 'Stygian Zinogre', 'Apex Zinogre'],
    'Piscine Wyvern': ['Cephadrome'],
    'Carapaceon': ['Daimyo Hermitaur', 'Plum D.Hermitaur'],
    '???': ['Gore Magala', 'Chaotic Gore Magala'],
}


def text(b, o):
    e = o
    while b[e:e + 2] != b'\0\0':
        e += 2
    return b[o:e].decode('utf-16-le')


def one_line(s): return re.sub(r'\s+', ' ', s).strip()


def u32(b, o): return struct.unpack_from('<I', b, o)[0]


def loaners(b, qi):
    """The quest's loaner sets -> [(item type, weapon number)], or []."""
    out, o = [], u32(b, qi + 0x44)
    while o and o + LOANER_SET <= len(b) and u32(b, o) == 2:
        t, _, n = struct.unpack_from('<BBH', b, o + 0x1c)
        out.append((t, n))
        o += LOANER_SET
    return out


def read_quest(path):
    b = open(path, 'rb').read()
    qi = u32(b, 0)
    assert b[4:8] == b'v005', path
    t = [text(b, o) for o in struct.unpack_from('<7I', b, u32(b, u32(b, qi + 0x1c)))]
    qid, star = struct.unpack_from('<HB', b, qi + 0x20)
    objs = [struct.unpack_from('<BBHHH', b, qi + 0x2c + 8 * k) for k in range(3)]
    waves, p = [], u32(b, 0x28)
    while p and u32(b, p):
        o = u32(b, p)
        while u32(b, o) != 0xffffffff:
            waves.append(u32(b, o))
            o += 0x28
        p += 4
    return dict(id=qid, star=star, map=b[qi + 0x24], type=b[qi], flags=b[qi + 1], main=[o for o in objs[:2] if o[0]],
                icons=[i for i in struct.unpack_from('<5H', b, qi + 0x48) if i != NO_ICON],
                waves=list(dict.fromkeys(waves)), name=one_line(t[0]), main_text=one_line(t[1]),
                loaners=loaners(b, qi))


def board(qid):
    """The Hunting Log's quest number ranges."""
    if qid < 100: return 'Training'
    if qid < 10000: return 'Caravan'
    if qid < 20000: return 'Gathering Hall'
    if qid < 30000: return 'Arena'
    return 'Expedition'


def quest_order():
    """The first two 0-terminated runs: the offline quests, then the Gathering Hall and Arena."""
    out, va, runs = [], QUEST_ORDER, 0
    while runs < 2:
        v = struct.unpack_from('<H', CODE, va - BASE)[0]
        if v:
            out.append(v)
        elif out:
            runs += 1
        va += 2
    return out


def main():
    order = {q: i for i, q in enumerate(quest_order())}
    raw = {}
    for path in sorted(QUESTS):
        q = read_quest(path)
        raw.setdefault(q['id'], q)
    # Training: one loaner set each, the weapon its name gives -- the check on the set layout.
    for qid in range(11, 25):
        (t, _), = raw[qid]['loaners']
        assert raw[qid]['name'] == 'Training: ' + COMMON[36 + t], (qid, raw[qid]['name'], COMMON[36 + t])
    keep = [q for q in raw.values() if q['name'] and q['id'] != 100 and board(q['id']) in BOARDS]
    keep.sort(key=lambda q: (order.get(q['id'], 1 << 20), q['id']))

    large = {em for q in raw.values() for em in q['waves']}
    cells = monster_cells(raw.values())
    cell_name = {QUESTION_CELL: 'Question Mark'}
    for em, c in sorted(cells.items()):
        cell_name.setdefault(c, monster(em))
    cell_name.update(ITEM_CELLS)
    names = {t: msg(table) for t, _, table in TYPES}

    quests, used, large_names = [], set(), set()
    for q in keep:
        # The Hunting Log's targets, icon and flags, field for field.
        kills = [(k, t) for k, _, _, t, _ in q['main'] if k in (1, 0x81) and t]
        ems = [t for _, t in kills]
        if q['type'] == 8 or not ems and q['type'] != 4:
            ems = list(dict.fromkeys(q['waves'] + ems))
        delivered = [ITEMS[t] for k, _, _, t, _ in q['main'] if k == 2]
        icon = q['icons'][0] if q['icons'] else cells.get(q['waves'][0], QUESTION_CELL) if q['waves'] else 96
        used.add(icon)
        large_names.update(monster(em) for em in ems if em in large)
        urgent = bool(q['flags'] & 0x10)
        entry = {
            'Id': q['id'], 'Type': board(q['id']), 'Level': q['star'],
            'Name': q['name'], 'Main': q['main_text'], 'Locale': LOCALES.get(q['map'], ''),
            'Monsters': [monster(em) for em in ems],
            'Icon': cell_name.get(icon, 'Question Mark').replace(' ', '_'),
            'Urgent': urgent, 'Key': bool(q['flags'] & 0x20) and not urgent,
            'Capture': q['type'] == 2 or any(k == 0x81 for k, _ in kills),
            'Repel': bool(q['flags'] & 0x04),
            'LgMonster': any(em in large for em in ems),
            'SmMonsters': any(em not in large for em in ems),
            'Delivery': any(d != 'Paw Pass Ticket' for d in delivered),
            'Harvest': 'Paw Pass Ticket' in delivered and not ems,
            'Frenzy': FRENZY in q['icons'], 'Apex': APEX in q['icons'],
        }
        if q['loaners']:
            sets = []
            for t, n in q['loaners']:
                assert t in names and 0 < n < len(names[t]), (q['id'], t, n)
                name = names[t][n]
                assert name and not name.lower().startswith('dummy') and name not in ('(None)', '-'), (q['id'], t, n, name)
                sets.append({'Weapon': COMMON[36 + t], 'Name': name})
            entry['ArenaSets'] = sets
        elif entry['Type'] == 'Arena':
            print('WARNING: no loaner sets on Arena quest', q['id'])
        quests.append(entry)

    classed = {n for ns in MONSTER_CLASS.values() for n in ns}
    unclassed = sorted(large_names - classed)
    if unclassed:
        sys.exit('No MONSTER_CLASS entry for large monster(s): %s' % ', '.join(unclassed))
    unknown_maps = sorted({q['Name'] for q in quests if not q['Locale']})
    if unknown_maps:
        print('WARNING: no locale for', unknown_maps)
    unnamed = sorted(c for c in used if c not in cell_name)
    if unnamed:
        print('WARNING: quest icon cells with no name:', unnamed)

    files = sorted(cell_name.items())
    files += [(cells[em], monster(em)) for em in sorted(VARIANTS)
              if em in cells and cell_name.get(cells[em]) != monster(em)]
    icons = write_monster_icons(files)
    write_weapon_icons()
    backgrounds = write_guild_backgrounds()

    monsters = [{'Name': n, 'Class': c} for c, ns in MONSTER_CLASS.items() for n in ns if n in large_names]
    data = {'quests': quests, 'monsters': monsters,
            'weaponIcons': {COMMON[36 + t]: s for t, s, _ in TYPES}, 'icons': sorted(icons),
            'backgrounds': backgrounds}
    with open(os.path.join(DOCS, 'data.js'), 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('// Generated by scripts/build_data.py from the game itself. Do not edit by hand.\n')
        fh.write('window.MH4U_RANDOMIZER_DATA = ' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';\n')
    print(len(quests), 'quests', dict(collections.Counter(q['Type'] for q in quests)),
          sum(q['Urgent'] for q in quests), 'urgent,', sum(q['Key'] for q in quests), 'key,',
          len(monsters), 'large monsters,', sum(len(q.get('ArenaSets', [])) for q in quests), 'loaner sets,',
          len(icons), 'icons,', len(backgrounds), 'Guild Card backgrounds')


def monster_cells(quests):
    """monster number -> cmn_micon cell, voted from the quests (the Hunting Log's ICONS)."""
    votes = collections.defaultdict(collections.Counter)
    for q in quests:
        icons = [i for i in q['icons'] if i not in (DANGER, FRENZY, APEX)]
        kills = [t for k, _, _, t, _ in q['main'] if k in (1, 0x81) and t]
        if len(kills) == 1 and icons:
            votes[kills[0]][icons[0]] += 1
        if q['waves'] and len(q['waves']) == len(icons):
            for em, c in zip(q['waves'], icons):
                votes[em][c] += 1
    cells = {em: v.most_common(1)[0][0] for em, v in votes.items()}
    for em in range(1, len(EM)):
        if em not in cells and em - 1 in cells and em + 1 in cells and cells[em + 1] - cells[em - 1] == 2:
            cells[em] = cells[em - 1] + 1
    return cells


def write_monster_icons(files):
    """One file per (cell, name): MH4U-<name>_Icon.png, the 34 px cell at 2x nearest."""
    from PIL import Image
    from pica_la4 import decode_rgba4
    atlas = decode_rgba4(open(MONSTER_TEX, 'rb').read())
    out = os.path.join(DOCS, 'assets', 'MonsterIcons')
    os.makedirs(out, exist_ok=True)
    written = []
    for c, name in files:
        stem = name.replace(' ', '_')
        r, k = divmod(c if c < 99 else c - 99, 7)
        x, y = (1 if c < 99 else 257) + 36 * k, 1 + 36 * r
        Image.fromarray(atlas[y:y + 34, x:x + 34]).resize((68, 68), Image.NEAREST).save(
            os.path.join(out, 'MH4U-%s_Icon.png' % stem), optimize=True)
        written.append(stem)
    return written


def write_weapon_icons():
    """The game's weapon-class player icons, 14x16 centred in 16x16, at 3x."""
    import numpy as np
    from PIL import Image
    from pica_la4 import decode_la4
    atlas = decode_la4(open(ICON_TEX, 'rb').read())
    out = os.path.join(DOCS, 'assets', 'WeaponIcons')
    os.makedirs(out, exist_ok=True)
    for t, slug, _ in TYPES:
        n = CODE[ICON_CELL_TABLE - BASE + CODE[CLASS_OF - BASE + t]]
        x, y = 14 * (n % 10), 160 + 16 * (n // 10)
        sq = np.zeros((16, 16, 4), np.uint8)
        sq[:, 1:15] = atlas[y:y + 16, x:x + 14]
        Image.fromarray(sq).resize((48, 48), Image.NEAREST).save(os.path.join(out, 'icon_%s.png' % slug), optimize=True)


def write_guild_backgrounds():
    """GUILD CARD BACKGROUNDS above -> [[number, name]] in the game's number order."""
    import numpy as np
    from PIL import Image
    from pica_etc1 import decode_etc1
    out = os.path.join(DOCS, 'assets', 'GuildCardBG')
    os.makedirs(os.path.join(out, 'thumbs'), exist_ok=True)
    found = []
    for d in glob.glob(GUILD_BG):
        n = int(re.fullmatch(r'gc_bg(\d+)', os.path.basename(d)).group(1))
        tex, = glob.glob(os.path.join(d, '**', 'ui_guild_*.241f5deb'), recursive=True)
        found.append((n, tex))
    assert len(found) == 69, 'expected 69 gc_bg arcs, found %d (extract "guild_card\\ui_guild_" first)' % len(found)
    written = []
    for n, tex in sorted(found):
        name = CARD[290 + n]
        if name == 'Invalid Message' or n in BG_LEFT_OUT:
            continue
        rgb = decode_etc1(open(tex, 'rb').read())[..., :3]
        assert rgb.max() > 0, (n, name)
        im = Image.fromarray(np.ascontiguousarray(rgb))
        stem = 'gc_bg%02d.webp' % n
        im.save(os.path.join(out, stem), lossless=True, method=6)
        im.resize((192, 96), Image.LANCZOS).save(os.path.join(out, 'thumbs', stem), quality=80)
        written.append([n, name])
    return written


if __name__ == '__main__':
    main()
