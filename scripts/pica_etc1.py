"""Decode MH4U .tex v0xA5 formats 11 (ETC1) and 12 (ETC1A4) -- the Guild Card backgrounds.

The rules are the 3U extract's pica_tex.py (which follows Citra's texture_decode.cpp), done with
numpy over every subtile at once. The header is pica_la4.py's. PICA layout: 8x8 tiles left to
right, top to bottom, each holding four 4x4 ETC1 subtiles in the order (x 0-3, y 0-3),
(x 4-7, y 0-3), (x 0-3, y 4-7), (x 4-7, y 4-7); a subtile is a little-endian u64, texel index
4 * x + y (ETC1A4: an 8-byte alpha word first, 4 bits per texel, same index). Memory row 0 is the
top of the image.
"""
import struct
import numpy as np

MOD_TABLE = np.array([(2, 8), (5, 17), (9, 29), (13, 42), (18, 60), (24, 80), (33, 106), (47, 183)], np.int32)
ETC1, ETC1A4 = 11, 12


def decode_etc1(d):
    """-> (h, w, 4) uint8 RGBA."""
    assert d[:4] == b'TEX\0', 'not a TEX'
    w1, w2, w3 = struct.unpack_from('<III', d, 4)
    assert w1 & 0xFFF == 0xA5, hex(w1)
    mips, w, h = w2 & 0x3F, (w2 >> 6) & 0x1FFF, (w2 >> 19) & 0x1FFF
    fmt = (w3 >> 8) & 0xFF
    assert fmt in (ETC1, ETC1A4), 'format %d, expected ETC1 / ETC1A4' % fmt
    n = w * h // 16
    words = np.frombuffer(d[16 + 4 * mips:16 + 4 * mips + (16 if fmt == ETC1A4 else 8) * n], '<u8')
    a = words[0::2] if fmt == ETC1A4 else None
    v = words[1::2] if fmt == ETC1A4 else words
    bits = lambda shift, mask: ((v >> np.uint64(shift)) & np.uint64(mask)).astype(np.int32)

    flip, diff = bits(32, 1), bits(33, 1)
    t2, t1 = bits(34, 7), bits(37, 7)
    # Differential mode: 5-bit base + signed 3-bit delta per channel, expanded to 8 bits.
    base = np.stack([bits(59, 31), bits(51, 31), bits(43, 31)], 1)
    dl = np.stack([bits(56, 7), bits(48, 7), bits(40, 7)], 1)
    dl = np.where(dl >= 4, dl - 8, dl)
    d1, d2 = base, base + dl
    d1, d2 = (d1 << 3) | (d1 >> 2), (d2 << 3) | (d2 >> 2)
    # Individual mode: two 4-bit colours.
    i1 = np.stack([bits(60, 15), bits(52, 15), bits(44, 15)], 1)
    i2 = np.stack([bits(56, 15), bits(48, 15), bits(40, 15)], 1)
    i1, i2 = (i1 << 4) | i1, (i2 << 4) | i2
    c1 = np.where(diff[:, None] == 1, d1, i1)
    c2 = np.where(diff[:, None] == 1, d2, i2)

    sub = np.full((n, 4, 4, 4), 255, np.uint8)               # [subtile][y][x]
    for x in range(4):
        for y in range(4):
            t = 4 * x + y
            first = np.where(flip == 1, y < 2, x < 2)
            col = np.where(first[:, None], c1, c2)
            m = MOD_TABLE[np.where(first, t1, t2), bits(t, 1)]
            m = np.where(bits(16 + t, 1) == 1, -m, m)
            sub[:, y, x, :3] = np.clip(col + m[:, None], 0, 255)
            if a is not None:
                sub[:, y, x, 3] = ((a >> np.uint64(4 * t)) & np.uint64(15)).astype(np.uint8) * 17

    # (tile row, tile col, subtile y, subtile x, y, x, rgba) -> image rows and columns
    tiles = sub.reshape(h // 8, w // 8, 2, 2, 4, 4, 4)
    return tiles.transpose(0, 2, 4, 1, 3, 5, 6).reshape(h, w, 4)
