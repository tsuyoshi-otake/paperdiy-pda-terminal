"""Write print-ready 3MF files for a Bambu Lab A1 mini (180 x 180 mm bed), one file per plate.

Every part is turned into its print orientation (see README "Print orientation") and laid out on the
plate, so the files can be opened in Bambu Studio / OrcaSlicer / PrusaSlicer and sliced directly.
Kit design (PD_MOUNT = "kit", default): plate 0 = test coupons (print first), plate 1 = lid (navy), plate 2 = tray
(cream). The earlier design ("bare") adds plate 3 (panel, strap, push-rods), plates 4-5 (front clip, magnet jigs) and
3mf/usb_variants/ (lid A for other USB-C cables).

    python3 src/export_3mf.py          # after src/build.py; reads out/, writes 3mf/
"""
import glob
import json
import os
import sys
import zipfile
from xml.sax.saxutils import escape

import numpy as np
import trimesh

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import CAD_DIR, OUT_DIR, SPLIT_DIR, USB_PM_SCREW_SPACING, USB_PM_VARIANTS  # noqa: E402

BED = 180.0
MARGIN = 3.0     # keep parts this far from the bed edge
GAP = 6.0        # between parts
OUT_3MF = os.path.join(CAD_DIR, "3mf")

FLIP_X = trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])      # top face down
ROT_Z90 = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1])  # turn on the bed
LAY_FLAT_Y = trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])  # hinge cover plates: visible face on the bed
STAND_X = trimesh.transformations.rotation_matrix(np.pi / 2, [0, 1, 0])     # front clip: U profile flat on the bed
with open(os.path.join(OUT_DIR, "assembly.json")) as _f:
    ASM = json.load(_f)
KIT = ASM.get("PD_MOUNT") == "kit"
# the kit design's lid top is a plane z = a + b y: tilt it level before turning it top face down
LAY_TOP = (trimesh.transformations.rotation_matrix(-np.arctan(ASM["LID_TOP"][1]), [1, 0, 0]) if KIT else np.eye(4))
# print orientation of everything cut from the three big parts
ORIENT = {"lid": (LAY_TOP, FLIP_X), "tray": (), "panel": ()}


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


def C(name):
    return os.path.join(OUT_DIR, "coupons", f"{name}.stl")


def usb_name(s):
    return "lid_A_left_usb_noscrew" if s <= 0 else f"lid_A_left_usb{s:g}mm"


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


def placed_layout(items):
    """items: [(name, mesh, (cx, cy))] placed by hand. Checks the bed edge and a GAP / 2 clearance between bounding boxes."""
    boxes = []
    for name, m, (cx, cy) in items:
        ex = m.extents
        b = (cx - ex[0] / 2, cy - ex[1] / 2, cx + ex[0] / 2, cy + ex[1] / 2)
        assert MARGIN <= b[0] and b[2] <= BED - MARGIN and MARGIN <= b[1] and b[3] <= BED - MARGIN, (name, b)
        for other, o in boxes:
            sep = max(o[0] - b[2], b[0] - o[2], o[1] - b[3], b[1] - o[3])
            assert sep >= GAP / 2, (name, other, sep)
        boxes.append((name, b))
    return items


def plates():
    """{file name: (title, rows)} with every part already in its print orientation."""
    with open(os.path.join(OUT_DIR, "coupons", "orientation.json")) as f:
        csrc = json.load(f)

    def coupon(n):
        return (n, part(C(n), *ORIENT[csrc[n]]))

    if KIT:
        return {
            # test coupons: hinge seat (lid + tray), dovetail key, snap tab + recess, and one cover of each kind
            "plate0_test_coupons.3mf": ("Test coupons (print first)", [
                [coupon("coupon_hinge_tray"), coupon("coupon_hinge_lid"), coupon("coupon_latch_tray")],
                [coupon("coupon_dovetail_A"), coupon("coupon_dovetail_B"), coupon("coupon_latch_lid")],
                [("hinge_cover_lid", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
                 ("hinge_cover_tray", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
            ]),
            # navy: lid pieces, top face on the bed (tilted level); no supports needed
            "plate1_lid.3mf": ("Lid (A + B)", [
                [("lid_A_left", part(S("lid_A_left"), LAY_TOP, FLIP_X, ROT_Z90)),
                 ("hinge_cover_lid_1", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
                 ("hinge_cover_lid_2", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y))],
                [("lid_B_main", part(S("lid_B_main"), LAY_TOP, FLIP_X))],
            ]),
            # cream: keyboard tray pieces, floor on the bed
            "plate2_tray.3mf": ("Keyboard tray (A + B)", [
                [("tray_A_left", part(S("tray_A_left"), ROT_Z90)),
                 ("hinge_cover_tray_1", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y)),
                 ("hinge_cover_tray_2", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
                [("tray_B_main", part(S("tray_B_main")))],
            ]),
        } | ({
            # bezel panel pieces, visible face on the bed (the locating rim grows upward)
            "plate3_panel.3mf": ("Bezel panel (A + B)", [
                [("panel_A_left", part(S("panel_A_left"), ROT_Z90))],
                [("panel_B_main", part(S("panel_B_main")))],
            ]),
        } if os.path.exists(S("panel_B_main")) else {}) | {
            f"usb_variants/{usb_name(sp)}.3mf": (
                f"Lid A for a USB-C panel mount with {sp:g} mm hole spacing" if sp > 0
                else "Lid A, USB-C panel-mount opening only (glue the connector in)",
                [[(usb_name(sp), part(os.path.join(SPLIT_DIR, "usb_variants", f"{usb_name(sp)}.stl"), LAY_TOP, FLIP_X, ROT_Z90))]])
            for sp in USB_PM_VARIANTS if os.path.exists(os.path.join(SPLIT_DIR, "usb_variants", f"{usb_name(sp)}.stl"))}
    p = {
        # test coupons: hinge seat, dovetail key, panel corner screw, push-rod bore, plus a rod and two covers
        "plate0_test_coupons.3mf": ("Test coupons (print first)", [
            [coupon("coupon_hinge_tray"), coupon("coupon_hinge_lid"), coupon("coupon_corner_lid")],
            [coupon("coupon_dovetail_A"), coupon("coupon_dovetail_B"), coupon("coupon_corner_panel"),
             coupon("coupon_keywall_lid")],
            [("key_pushrod", part(O("key_pushrod_x2"), ROT_Z90)),
             ("hinge_cover_lid", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
             ("hinge_cover_tray", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
        ]),
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
        # cream: display panel pieces (screen face down), strap (top face down), push-rods (flat side down),
        # optional top plate (visible face down; print it in an accent colour if you like)
        # placed by hand: the railed strap is nearly square, so the rows layout no longer fits
        "plate3_panel_parts.3mf": ("Display panel (A + B), strap, push-rods", {"place": [
            ("panel_B_main", part(S("panel_B_main")), (90.0, 133.9)),
            ("paperdiy_strap", part(O("paperdiy_strap"), FLIP_X), (42.6, 42.4)),
            ("panel_A_left", part(S("panel_A_left"), ROT_Z90), (131.1, 18.8)),
            ("top_plate_blank", part(O("top_plate_blank"), FLIP_X), (120.0, 75.45)),
            ("power_pushrod", part(O("power_pushrod")), (112.75, 57.75)),
            ("key_pushrod_1", part(O("key_pushrod_x2"), ROT_Z90), (149.0, 47.75)),
            ("key_pushrod_2", part(O("key_pushrod_x2"), ROT_Z90), (149.0, 58.75)),
        ]}),
    }
    # any colour: optional front clip that keeps the closed lid shut (one is enough; the second is a spare)
    p["plate4_front_clip.3mf"] = ("Front clip (optional, keeps the lid shut)", [
        [("front_clip_1", part(O("front_clip"), STAND_X)), ("front_clip_2", part(O("front_clip"), STAND_X))],
    ])
    # any colour: drilling jigs for the retrofit magnetic catch (top face on the bed)
    p["plate5_magnet_jigs.3mf"] = ("Drilling jigs for the magnetic catch (optional)", [
        [("magnet_jig_L", part(O("magnet_jig_L"), FLIP_X)), ("magnet_jig_R", part(O("magnet_jig_R"), FLIP_X))],
    ])
    # lid A for other USB-C panel-mount cables (only the small left lid piece depends on the cable)
    for s in USB_PM_VARIANTS:
        n = usb_name(s)
        p[f"usb_variants/{n}.3mf"] = (f"Lid A for a USB-C panel mount with {s:g} mm hole spacing" if s > 0
                                      else "Lid A, USB-C opening only (glue the connector in)",
                                      [[(n, part(os.path.join(SPLIT_DIR, "usb_variants", f"{n}.stl"), FLIP_X, ROT_Z90))]])
    return p


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
    # fixed timestamps so the same geometry always gives the same file (reproducible checksums)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, data in (("[Content_Types].xml", content_types), ("_rels/.rels", rels), ("3D/3dmodel.model", model)):
            info = zipfile.ZipInfo(arc, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)


def main():
    for f in glob.glob(os.path.join(OUT_3MF, "*.3mf")) + glob.glob(os.path.join(OUT_3MF, "usb_variants", "*.3mf")):
        os.remove(f)                                    # a plate that is no longer made must not linger
    os.makedirs(os.path.join(OUT_3MF, "usb_variants"), exist_ok=True)
    for fname, (title, rows) in plates().items():
        placed = placed_layout(rows["place"]) if isinstance(rows, dict) else rows_layout(rows)
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
            print(f"    {name:24s} {m.extents[0]:6.1f} x {m.extents[1]:6.1f} x {m.extents[2]:5.1f} mm")
        assert ok, fname
    assert USB_PM_SCREW_SPACING in USB_PM_VARIANTS


if __name__ == "__main__":
    main()
