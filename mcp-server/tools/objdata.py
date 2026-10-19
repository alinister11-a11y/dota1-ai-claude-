"""Parse WC3 object-data files (w3u / w3a) into {newId: (origId, {field: [(level, value)]})}."""
import struct

def parse(data, with_levels):
    p = 0
    ver, = struct.unpack_from('<i', data, p); p += 4
    out = {}
    for table in (0, 1):                       # 0 = modified originals, 1 = custom objects
        n, = struct.unpack_from('<i', data, p); p += 4
        for _ in range(n):
            orig = data[p:p + 4].decode('latin-1'); new = data[p + 4:p + 8].decode('latin-1'); p += 8
            if ver >= 3:                       # 1.33+ format has set count; not expected here
                raise ValueError('object data version %d not supported' % ver)
            nm, = struct.unpack_from('<i', data, p); p += 4
            mods = {}
            for _ in range(nm):
                fid = data[p:p + 4].decode('latin-1'); p += 4
                vt, = struct.unpack_from('<i', data, p); p += 4
                lvl = 0
                if with_levels:
                    lvl, ptr = struct.unpack_from('<ii', data, p); p += 8
                if vt == 0:
                    val, = struct.unpack_from('<i', data, p); p += 4
                elif vt in (1, 2):
                    val, = struct.unpack_from('<f', data, p); p += 4
                elif vt == 3:
                    e = data.index(b'\0', p); val = data[p:e].decode('utf-8', 'replace'); p = e + 1
                else:
                    raise ValueError('bad var type %d' % vt)
                p += 4                             # end marker
                mods.setdefault(fid, []).append((lvl, val))
            key = new if table == 1 and new != '\0\0\0\0' else orig
            out[key] = (orig, mods)
    return ver, out
