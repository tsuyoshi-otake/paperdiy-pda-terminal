"""Write print-ready 3MF files for a Bambu Lab A1 mini (180 x 180 mm bed), one file per plate.

Every part is turned into its print orientation (see README "Print orientation") and laid out on the
plate, so the files can be opened in Bambu Studio / OrcaSlicer / PrusaSlicer and sliced directly.
Parts are grouped by colour as in the README renders: plate 1 = lid (navy), plates 2-3 = cream (the three
small push-rods ride along on plate 3; print them in another colour separately if you like).

    python3 src/export_3mf.py          # after src/build.py; reads out/, writes 3mf/
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import CAD_DIR, OUT_DIR, SPLIT_DIR  # noqa: E402

BED = 180.0
MARGIN = 3.0     # keep parts this far from the bed edge
GAP = 6.0        # between parts
OUT_3MF = os.path.join(CAD_DIR, "3mf")

FLIP_X = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])      # top face down
ROT_Z90 = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])  # turn on the bed
LAY_FLAT_Y = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])  # hinge cover plates: visible face on the bed


def part(path, *rots):
    m = trimesh.load(path, force="mesh")
    for r in rots:
        m.apply_transform(r)
    lo, hi = m.bounds
    m.apply_translation([-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]])  # centred, on the bed
    return m


def S(name):
    return os.path.join(SPLIT_DIR, f"{name}.stl")


def O(name):
    return os.path.join(OUT_DIR, f"{name}.stl")


def rows_layout(rows):
    """rows: list of rows (front to back), each a list of (name, mesh). Returns [(name, mesh, (x, y))]."""
    placed = []
    row_h = [max(m.extents[1] for _, m in r) for r in rows]
    total_h = sum(row_h) + GAP * (len(rows) - 1)
    y = BED / 2 - total_h / 2
    for r, h in zip(rows, row_h):
        total_w = sum(m.extents[0] for _, m in r) + GAP * (len(r) - 1)
        x = BED / 2 - total_w / 2
        for name, m in r:
            w = m.extents[0]
            placed.append((name, m, (x + w / 2, y + h / 2)))
            x += w + GAP
        y += h + GAP
    for name, m, (cx, cy) in placed:  # every part must stay on the bed
        ex = m.extents
        assert MARGIN <= cx - ex[0] / 2 and cx + ex[0] / 2 <= BED - MARGIN, (name, "x", cx, ex)
        assert MARGIN <= cy - ex[1] / 2 and cy + ex[1] / 2 <= BED - MARGIN, (name, "y", cy, ex)
        assert ex[2] <= BED, (name, "z")
    return placed


def write_3mf(path, placed, title):
    objs, items = [], []
    for i, (name, m, (cx, cy)) in enumerate(placed, start=1):
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        objs.append(f'<object id="{i}" name="{escape(name)}" type="model"><mesh><vertices>{v}</vertices>'
                    f'<triangles>{t}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {cx:.4f} {cy:.4f} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             f'<metadata name="Title">{escape(title)}</metadata>'
             '<metadata name="Designer">PaperDIY PDA Terminal (derivative of unkyulee/phone-enclosure)</metadata>'
             '<metadata name="LicenseTerms">CC BY-NC 4.0</metadata>'
             f'<resources>{"".join(objs)}</resources><build>{"".join(items)}</build></model>')
    content_types = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                     '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
                     '</Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)


def main():
    os.makedirs(OUT_3MF, exist_ok=True)
    plates = {
        # navy: lid pieces, ceiling (top face) on the bed; no supports needed
        "plate1_lid.3mf": ("Lid (A + B)", [
            [("lid_A_left", part(S("lid_A_left"), FLIP_X, ROT_Z90)),
             ("hinge_cover_lid_1", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
             ("hinge_cover_lid_2", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y))],
            [("lid_B_main", part(S("lid_B_main"), FLIP_X))],
        ]),
        # cream: keyboard tray pieces, floor on the bed
        "plate2_tray.3mf": ("Keyboard tray (A + B)", [
            [("tray_A_left", part(S("tray_A_left"), ROT_Z90)),
             ("hinge_cover_tray_1", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y)),
             ("hinge_cover_tray_2", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
            [("tray_B_main", part(S("tray_B_main")))],
        ]),
        # cream: display panel pieces (screen face down), strap (top face down), push-rods (flat side down)
        "plate3_panel_parts.3mf": ("Display panel (A + B), strap, push-rods", [
            [("key_pushrod_1", part(O("key_pushrod_x2"), ROT_Z90)),
             ("key_pushrod_2", part(O("key_pushrod_x2"), ROT_Z90)),
             ("power_pushrod", part(O("power_pushrod")))],
            [("panel_A_left", part(S("panel_A_left"), ROT_Z90)),
             ("paperdiy_strap", part(O("paperdiy_strap"), FLIP_X, ROT_Z90))],
            [("panel_B_main", part(S("panel_B_main")))],
        ]),
    }
    for fname, (title, rows) in plates.items():
        placed = rows_layout(rows)
        path = os.path.join(OUT_3MF, fname)
        write_3mf(path, placed, title)
        # re-load and check what was written
        sc = trimesh.load(path)
        geoms = sc.dump() if isinstance(sc, trimesh.Scene) else [sc]
        lo = np.min([g.bounds[0] for g in geoms], axis=0)
        hi = np.max([g.bounds[1] for g in geoms], axis=0)
        ok = all(g.is_watertight for g in geoms) and lo[0] >= 0 and lo[1] >= 0 and hi[0] <= BED and hi[1] <= BED \
            and abs(lo[2]) < 1e-3
        print(f"{fname}: {len(geoms)} parts, extent x {lo[0]:.1f}..{hi[0]:.1f} y {lo[1]:.1f}..{hi[1]:.1f} "
              f"z {lo[2]:.1f}..{hi[2]:.1f} -> {'OK' if ok else 'CHECK'}")
        for name, m, _ in placed:
            print(f"    {name:16s} {m.extents[0]:6.1f} x {m.extents[1]:6.1f} x {m.extents[2]:5.1f} mm")
        assert ok, fname


if __name__ == "__main__":
    main()
