"""Parse / patch the player list of a TFT war3map.w3i (format 25)."""
import struct

def _str(d, p):
    e = d.index(b'\0', p)
    return d[p:e], e + 1

def players(d):
    p = 0
    fmt, = struct.unpack_from('<i', d, p); p += 4
    if fmt != 25:
        raise ValueError('w3i format %d' % fmt)
    p += 8                                   # saves, editor version
    for _ in range(4):
        _, p = _str(d, p)                    # name, author, description, recommended players
    p += 32 + 16 + 8 + 4 + 1                 # camera bounds, complements, playable w/h, flags, tileset
    p += 4                                   # loading screen number
    for _ in range(4):
        _, p = _str(d, p)                    # loading model, text, title, subtitle
    p += 4                                   # game data set
    for _ in range(4):
        _, p = _str(d, p)                    # prologue path, text, title, subtitle
    p += 4 + 12 + 4                          # fog style, start/end/density, color
    p += 4                                   # global weather
    _, p = _str(d, p)                        # sound environment
    p += 1 + 4                               # light tileset, water tint
    n, = struct.unpack_from('<i', d, p); p += 4
    out = []
    for _ in range(n):
        start = p
        num, typ, race, fixed = struct.unpack_from('<iiii', d, p); p += 16
        name, p = _str(d, p)
        p += 8 + 8                           # start x/y, ally priorities
        out.append({'offset': start, 'num': num, 'type': typ, 'race': race, 'name': name.decode('utf-8', 'replace')})
    return out

def set_types(d, mapping):
    """mapping: player number -> type (1 human, 2 computer)."""
    b = bytearray(d)
    for pl in players(d):
        if pl['num'] in mapping:
            struct.pack_into('<i', b, pl['offset'] + 4, mapping[pl['num']])
    return bytes(b)
