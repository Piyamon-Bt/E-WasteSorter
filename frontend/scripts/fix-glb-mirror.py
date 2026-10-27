#!/usr/bin/env python3
"""Undo a Z-axis mirror in GLB files by wrapping each scene's roots in a node scaled [1, 1, -1].

The retro-*.glb exports have their geometry mirrored (text reads backwards and the
front faces -Z), which matches an exporter that negated Z when converting
coordinate systems. glTF renderers, three.js / <model-viewer> included, handle the
negative scale by flipping face winding, so materials and lighting stay correct.

Usage: python3 scripts/fix-glb-mirror.py public/assets/models/retro-*.glb
Files that already have a "mirror-fix" node are skipped, so running it twice is safe.
"""
import json
import struct
import sys

MARKER = 'mirror-fix'


def fix(path: str) -> str:
    data = open(path, 'rb').read()
    magic, version, _ = struct.unpack('<4sII', data[:12])
    if magic != b'glTF' or version != 2:
        return 'not a glTF 2.0 binary'
    json_len, json_type = struct.unpack('<II', data[12:20])
    assert json_type == 0x4E4F534A  # 'JSON'
    gltf = json.loads(data[20:20 + json_len])
    rest = data[20 + json_len:]  # BIN chunk (header included), untouched

    nodes = gltf.setdefault('nodes', [])
    if any(n.get('name') == MARKER for n in nodes):
        return 'already fixed'
    for scene in gltf.get('scenes', []):
        roots = scene.get('nodes', [])
        nodes.append({'name': MARKER, 'scale': [1, 1, -1], 'children': roots})
        scene['nodes'] = [len(nodes) - 1]

    payload = json.dumps(gltf, separators=(',', ':')).encode()
    payload += b' ' * (-len(payload) % 4)
    out = struct.pack('<II', len(payload), 0x4E4F534A) + payload + rest
    open(path, 'wb').write(struct.pack('<4sII', b'glTF', 2, 12 + len(out)) + out)
    return 'fixed'


if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(f'{p}: {fix(p)}')
