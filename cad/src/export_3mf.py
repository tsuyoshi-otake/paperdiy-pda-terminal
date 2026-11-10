"""Write print-ready 3MF files for a Bambu Lab A1 mini (180 x 180 mm bed), one file per plate, and (kit design) the
same plates with the lid, tray and panel in one piece each for printers with a bed of 220 mm or more (3mf/large/).

Every part is turned into its print orientation (see cad/README.md, "Printing") and laid out on the
plate, so the files can be opened in Bambu Studio / OrcaSlicer / PrusaSlicer and sliced directly.
Kit design (PD_MOUNT = "kit", default): plate 0 = test coupons (print first), plate 1 = lid (navy), plate 2 = tray
(cream). The earlier design ("bare") adds plate 3 (panel, strap, push-rods), plates 4-5 (front clip, magnet jigs) and
3mf/usb_variants/ (lid A for other USB-C cables).

Kit design: the A1 mini plates are also written as Bambu Studio projects with the print settings chosen
(3mf/bambu_a1mini/, see BAMBU below).

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
from params import CAD_DIR, OUT_DIR, SPLIT_DIR, USB_PM_SCREW_SPACING, USB_PM_VARIANTS, WHOLE_BED, WHOLE_DIR  # noqa: E402

BED = 180.0
MARGIN = 3.0     # keep parts this far from the bed edge
GAP = 6.0        # between parts
OUT_3MF = os.path.join(CAD_DIR, "3mf")

# Bambu Studio projects for the A1 mini with a 0.4 mm nozzle (3mf/bambu_a1mini/): the same plates with the printer,
# process and filament presets chosen, so they open ready to slice. How Bambu Studio reads such a file (its source,
# src/libslic3r/Format/bbs_3mf.cpp, PresetBundle::load_config_file_config, PresetCollection::load_external_preset):
# a 3MF whose "Application" metadata starts with "BambuStudio-" is a project; Metadata/project_settings.config (JSON)
# names the three presets; every option that is not listed in "different_settings_to_system" is taken from the
# system preset of that name as installed on the user's computer, the listed ones from the file. So the file carries
# only the preset names and the handful of options changed from "0.20mm Standard @BBL A1M" (2 walls, grid infill,
# classic walls, no elephant-foot compensation), and stays right when Bambu updates its presets.
# The version is the lowest 2.x: a file newer than the program only brings up an "update Bambu Studio" notice.
BAMBU = dict(
    dir="bambu_a1mini", prefix="bambu_", version="02.00.00.00",
    printer="Bambu Lab A1 mini 0.4 nozzle", printer_model="Bambu Lab A1 mini", nozzle="0.4",
    process="0.20mm Standard @BBL A1M", bed="Textured PEI Plate",
    # option: value, as in Bambu Studio's process tabs (see ASSEMBLY_ja.md, 2.)
    changed=dict(wall_loops="3",                      # screws bite into three walls
                 sparse_infill_pattern="gyroid",
                 wall_generator="arachne",            # fills the 1.0-1.2 mm walls and ribs without a gap
                 elefant_foot_compensation="0.1",     # the visible faces are first layers
                 precise_z_height="1"),               # panel 1.6 mm, splice pockets 0.6 / 0.8 mm
    filament=dict(pla=("Bambu PLA Basic @BBL A1M", "GFA00", "#3B6FB6"), tpu=("Bambu TPU 95A HF @BBL A1M", "GFU00", "#2B2B2B")),
    preset="PaperDIY PDA 0.20mm @BBL A1M")            # the same changes as a process preset to import (the fallback)

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


def W(name):
    return os.path.join(WHOLE_DIR, f"{name}.stl")


def rows_layout(rows, BED=BED):
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
            # test coupons: hinge seat (lid + tray), dovetail key (if the split has keys), snap tab + recess, one cover of each kind
            "plate0_test_coupons.3mf": ("Test coupons (print first)", [
                [coupon("coupon_hinge_tray"), coupon("coupon_hinge_lid"), coupon("coupon_latch_tray")],
                ([coupon("coupon_dovetail_A"), coupon("coupon_dovetail_B")] if "coupon_dovetail_A" in csrc else [])
                + [coupon("coupon_latch_lid")],
                [("hinge_cover_lid", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
                 ("hinge_cover_tray", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
            ]),
            # navy: lid pieces, top face on the bed (tilted level); no supports needed
            "plate1_lid.3mf": ("Lid (A + B)", [
                [("lid_A_left", part(S("lid_A_left"), LAY_TOP, FLIP_X, ROT_Z90)),
                 ("hinge_cover_lid_1", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
                 ("hinge_cover_lid_2", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y))],
                [("lid_B_main", part(S("lid_B_main"), LAY_TOP, FLIP_X))],
            ] + splice_row("lid", LAY_TOP, FLIP_X)),
            # cream: keyboard tray pieces, floor on the bed
            "plate2_tray.3mf": ("Keyboard tray (A + B)", [
                [("tray_A_left", part(S("tray_A_left"), ROT_Z90)),
                 ("hinge_cover_tray_1", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y)),
                 ("hinge_cover_tray_2", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
                [("tray_B_main", part(S("tray_B_main")))],
            ] + splice_row("tray")),
        } | ({
            # TPU feet (0.4 nozzle), table side on the bed
            "plate4_tpu.3mf": ("TPU feet (print in TPU with a 0.4 nozzle)", [
                [(f"tpu_foot_{i}", part(O("tpu_foot"))) for i in (1, 2)],
                [(f"tpu_foot_{i}", part(O("tpu_foot"))) for i in (3, 4)],
            ]),
        } if os.path.exists(O("tpu_foot")) else {}) | ({
            # bezel panel pieces, visible face on the bed (the locating rim grows upward)
            "plate3_panel.3mf": ("Bezel panel (A + B)", [
                [("panel_A_left", part(S("panel_A_left"), ROT_Z90))],
                [("panel_B_main", part(S("panel_B_main")))],
            ] + splice_row("panel")),
        } if os.path.exists(S("panel_B_main")) else {}) | {
            f"usb_variants/{usb_name(sp)}.3mf": (
                f"Lid A for a USB-C panel mount with {sp:g} mm hole spacing" if sp > 0
                else "Lid A, USB-C panel-mount opening only (glue the connector in)",
                [[(usb_name(sp), part(os.path.join(SPLIT_DIR, "usb_variants", f"{usb_name(sp)}.stl"), LAY_TOP, FLIP_X, ROT_Z90))]])
            for sp in USB_PM_VARIANTS if os.path.exists(os.path.join(SPLIT_DIR, "usb_variants", f"{usb_name(sp)}.stl"))}
    return bare_plates(csrc, coupon)


def splice_row(kind, *rots):
    """The splice plates of one kind (out/split/splice/) as an extra row, flat on the bed, long side along x."""
    files = sorted(glob.glob(os.path.join(SPLIT_DIR, "splice", f"{kind}_splice_*.stl")))
    items = []
    for f in files:
        m = part(f, *rots)
        if m.extents[1] > m.extents[0]:
            m = part(f, *rots, ROT_Z90)
        items.append((os.path.splitext(os.path.basename(f))[0], m))
    return [items] if items else []


def large_plates():
    """The kit design's plates with whole parts (no split, nothing to glue), for a bed of WHOLE_BED or more."""
    if not (KIT and os.path.exists(W("lid"))):
        return {}
    p = {
        "large/plate1_lid.3mf": ("Lid, one piece (bed 220 mm or more)", [
            [("hinge_cover_lid_1", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y)),
             ("hinge_cover_lid_2", part(O("hinge_cover_lid_x2"), LAY_FLAT_Y))],
            [("lid", part(W("lid"), LAY_TOP, FLIP_X))],
        ]),
        "large/plate2_tray.3mf": ("Keyboard tray, one piece (bed 220 mm or more)", [
            [("hinge_cover_tray_1", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y)),
             ("hinge_cover_tray_2", part(O("hinge_cover_tray_x2"), LAY_FLAT_Y))],
            [("tray", part(W("tray")))],
        ]),
        "large/plate3_panel.3mf": ("Bezel panel, one piece (bed 220 mm or more)", [
            [("panel", part(W("panel")))],
        ]),
    }
    for sp in USB_PM_VARIANTS:
        n = usb_name(sp).replace("lid_A_left", "lid")
        p[f"large/usb_variants/{n}.3mf"] = (
            (f"Lid, one piece, for a USB-C panel mount with {sp:g} mm hole spacing" if sp > 0
             else "Lid, one piece, USB-C panel-mount opening only (glue the connector in)"),
            [[(n, part(W(f"usb_variants/{n}"), LAY_TOP, FLIP_X))]])
    return p


def bare_plates(csrc, coupon):
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


def bambu_project_settings(filament):
    """Metadata/project_settings.config: the preset names and the options changed from the system process preset."""
    name, fid, colour = BAMBU["filament"][filament]
    cfg = {"from": "project", "name": "project_settings", "version": BAMBU["version"],
           "printer_technology": "FFF", "printer_model": BAMBU["printer_model"], "printer_variant": BAMBU["nozzle"],
           "nozzle_diameter": [BAMBU["nozzle"]],
           "printer_settings_id": BAMBU["printer"], "print_settings_id": BAMBU["process"],
           "filament_settings_id": [name], "filament_ids": [fid], "filament_colour": [colour],
           "curr_bed_type": BAMBU["bed"],
           # per preset, in the order process, filament, printer: its parent ("" = it is the system preset itself) and
           # the options that differ from it
           "inherits_group": ["", "", ""],
           "different_settings_to_system": [";".join(sorted(BAMBU["changed"])), "", ""]}
    cfg.update(BAMBU["changed"])
    return json.dumps(dict(sorted(cfg.items())), indent=4, ensure_ascii=False) + "\n"


def bambu_model_settings(names, plate_name):
    """Metadata/model_settings.config: every object on extruder 1, all of them on plate 1."""
    x = ['<?xml version="1.0" encoding="UTF-8"?>', "<config>"]
    for i, n in enumerate(names, start=1):
        x += [f'  <object id="{i}">', f'    <metadata key="name" value="{escape(n)}"/>',
              '    <metadata key="extruder" value="1"/>', "  </object>"]
    x += ["  <plate>", '    <metadata key="plater_id" value="1"/>',
          f'    <metadata key="plater_name" value="{escape(plate_name)}"/>', '    <metadata key="locked" value="false"/>']
    for i in range(1, len(names) + 1):
        x += ["    <model_instance>", f'      <metadata key="object_id" value="{i}"/>',
              '      <metadata key="instance_id" value="0"/>', f'      <metadata key="identify_id" value="{100 + i}"/>',
              "    </model_instance>"]
    x += ["  </plate>", "</config>"]
    return "\n".join(x) + "\n"


def bambu_process_preset():
    """The changed options as a user process preset (File > Import > Import Configs in Bambu Studio)."""
    cfg = {"from": "User", "inherits": BAMBU["process"], "name": BAMBU["preset"], "print_settings_id": BAMBU["preset"],
           "version": BAMBU["version"]}
    cfg.update(BAMBU["changed"])
    return json.dumps(dict(sorted(cfg.items())), indent=4, ensure_ascii=False) + "\n"


def write_3mf(path, placed, title, bambu=None):
    """bambu: None = geometry only (any slicer); "pla" / "tpu" = a Bambu Studio project for the A1 mini (see BAMBU)."""
    objs, items = [], []
    for i, (name, m, (cx, cy)) in enumerate(placed, start=1):
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in m.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in m.faces)
        objs.append(f'<object id="{i}" name="{escape(name)}" type="model"><mesh><vertices>{v}</vertices>'
                    f'<triangles>{t}</triangles></mesh></object>')
        items.append(f'<item objectid="{i}" transform="1 0 0 0 1 0 0 0 1 {cx:.4f} {cy:.4f} 0"/>')
    model = ('<?xml version="1.0" encoding="UTF-8"?>\n'
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"'
             + (' xmlns:BambuStudio="http://schemas.bambulab.com/package/2021">'
                f'<metadata name="Application">BambuStudio-{BAMBU["version"]}</metadata>'
                '<metadata name="BambuStudio:3mfVersion">1</metadata>' if bambu else '>') +
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
    files = [("[Content_Types].xml", content_types), ("_rels/.rels", rels), ("3D/3dmodel.model", model)]
    if bambu:
        files += [("Metadata/model_settings.config", bambu_model_settings([n for n, _, _ in placed],
                                                                          os.path.splitext(os.path.basename(path))[0])),
                  ("Metadata/project_settings.config", bambu_project_settings(bambu))]
    # fixed timestamps so the same geometry always gives the same file (reproducible checksums)
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for arc, data in files:
            info = zipfile.ZipInfo(arc, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data)


def main():
    for sub in ("", "usb_variants", "large", "large/usb_variants", BAMBU["dir"]):
        for f in glob.glob(os.path.join(OUT_3MF, sub, "*.3mf")) + glob.glob(os.path.join(OUT_3MF, sub, "*.json")):
            os.remove(f)                                # a plate that is no longer made must not linger
    os.makedirs(os.path.join(OUT_3MF, "usb_variants"), exist_ok=True)
    jobs = [(k, v, BED) for k, v in plates().items()] + [(k, v, WHOLE_BED) for k, v in large_plates().items()]
    for fname, (title, rows), bed in jobs:
        os.makedirs(os.path.dirname(os.path.join(OUT_3MF, fname)), exist_ok=True)
        placed = placed_layout(rows["place"]) if isinstance(rows, dict) else rows_layout(rows, bed)
        path = os.path.join(OUT_3MF, fname)
        write_3mf(path, placed, title)
        if KIT and bed == BED and "/" not in fname:      # the A1 mini plates again, as Bambu Studio projects
            os.makedirs(os.path.join(OUT_3MF, BAMBU["dir"]), exist_ok=True)
            write_3mf(os.path.join(OUT_3MF, BAMBU["dir"], BAMBU["prefix"] + fname), placed, title,
                      bambu="tpu" if "tpu" in fname else "pla")
        # re-load and check what was written
        sc = trimesh.load(path)
        geoms = sc.dump() if isinstance(sc, trimesh.Scene) else [sc]
        lo = np.min([g.bounds[0] for g in geoms], axis=0)
        hi = np.max([g.bounds[1] for g in geoms], axis=0)
        ok = all(g.is_watertight for g in geoms) and lo[0] >= 0 and lo[1] >= 0 and hi[0] <= bed and hi[1] <= bed \
            and abs(lo[2]) < 1e-3
        print(f"{fname}: {len(geoms)} parts, extent x {lo[0]:.1f}..{hi[0]:.1f} y {lo[1]:.1f}..{hi[1]:.1f} "
              f"z {lo[2]:.1f}..{hi[2]:.1f} -> {'OK' if ok else 'CHECK'}")
        for name, m, _ in placed:
            print(f"    {name:24s} {m.extents[0]:6.1f} x {m.extents[1]:6.1f} x {m.extents[2]:5.1f} mm")
        assert ok, fname
    assert USB_PM_SCREW_SPACING in USB_PM_VARIANTS
    if KIT:
        with open(os.path.join(OUT_3MF, BAMBU["dir"], "paperdiy_process_a1mini_04.json"), "w") as f:
            f.write(bambu_process_preset())
        made = sorted(os.path.basename(f) for f in glob.glob(os.path.join(OUT_3MF, BAMBU["dir"], "*.3mf")))
        print(f"{BAMBU['dir']}/: {', '.join(made)} as Bambu Studio projects ({BAMBU['printer']}, {BAMBU['process']} with "
              f"{', '.join(f'{k} {v}' for k, v in BAMBU['changed'].items())}; {BAMBU['bed']}) + paperdiy_process_a1mini_04.json")


if __name__ == "__main__":
    main()
