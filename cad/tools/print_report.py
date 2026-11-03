#!/usr/bin/env python3
"""Printability report for the A1 mini plates.

1. Slices every plate in 3mf/ with PrusaSlicer's command line and an approximation of the Bambu Studio
   A1 mini / 0.20 mm Standard / PLA profile (tools/a1mini_pla_020.ini): print time, filament, and the slicer's
   own "print stability" warnings (floating regions, long bridges, loose extrusions, low bed adhesion).
2. Measures wall thickness on every printed part (rays from the surface inwards).
3. Estimates whether the open device tips over backwards: lid-side mass and centre of mass from the sliced
   part masses plus the bought parts, swept over the opening angle.

    python3 tools/print_report.py            # after src/build.py and src/export_3mf.py
Writes out/print_report.md. Without prusa-slicer on PATH (or PRUSA_SLICER=...) only parts 2-3 run, with
solid-model masses instead of sliced ones.
"""
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CAD, "src"))
from params import (OUT_DIR, SPLIT_DIR, Y_BACK, HINGE_AXIS_Y, Z_PART, PD_L, PD_TOP_X, PANEL_Z_BACK, BATT_CX, BATT_CY,  # noqa: E402
                    BATT_T, USB_PM_Y, USB_PM_Z)

INI = os.path.join(HERE, "a1mini_pla_020.ini")
PLA = 1.24                      # g/cm3
THIN = 0.8                      # mm: two 0.4 mm lines
# bought parts: (grams, centre in the closed assembly frame, source)
PAPERDIY_G = 26.4               # [M] M5Stack spec, PaperDIY Assembly Kit (incl. its 140 mAh cell, which is removed)
BATTERY_G = 38.0                # [A] typical 1S 2000 mAh pouch (50 x 34 x 10)
USB_CABLE_G = 10.0              # [A] panel-mount extension, short
HINGE_G = 4.0                   # [A] per hinge, half moves with the lid
KB_CG = (0.0, 0.0, 8.0)         # [A] keyboard centre of mass: middle of the tray pocket

# what the slicer warnings on these parts mean (checked by hand)
KNOWN = {
    "Low bed adhesion": "the push-rods are 3-4 mm thin bars: keep Bambu Studio's brim type on Auto (its default) "
                        "or give them a brim",
    "Loose extrusions": "the 5 mm counterbore at the panel's screen face is bridged 1.5 mm above the bed "
                        "(same in the real panel, a short bridge that prints fine)",
}
THIN_NOTE = {"panel_B_main": "the screen-window bevel ends in a sharp edge (as in the original panel)"}

LID_PARTS = [("lid_A_left", 1), ("lid_B_main", 1), ("panel_A_left", 1), ("panel_B_main", 1), ("paperdiy_strap", 1),
             ("key_pushrod_x2", 2), ("power_pushrod", 1), ("hinge_cover_lid_x2", 2), ("top_plate_blank", 1)]
BASE_PARTS = [("tray_A_left", 1), ("tray_B_main", 1), ("hinge_cover_tray_x2", 2)]


def stl(name):
    for d in (SPLIT_DIR, OUT_DIR):
        p = os.path.join(d, f"{name}.stl")
        if os.path.exists(p):
            return p
    raise FileNotFoundError(name)


def slicer():
    exe = os.environ.get("PRUSA_SLICER") or shutil.which("prusa-slicer") or shutil.which("PrusaSlicer")
    return exe


def slice_file(exe, path, tmp):
    out = os.path.join(tmp, os.path.basename(path) + ".gcode")
    r = subprocess.run([exe, "--export-gcode", "--load", INI, "--dont-arrange", "-o", out, path],
                       capture_output=True, text=True, timeout=900)
    text = r.stdout + r.stderr
    warn = []
    m = re.search(r"Detected print stability issues:\n(.*?)(?:Consider enabling supports\.|\Z)", text, re.S)
    if m:
        # blocks separated by blank lines, each = an issue kind ("Low bed adhesion") + the objects it concerns,
        # in either order; object names here never contain spaces, issue kinds always do
        lines = [x.strip() for x in m.group(1).splitlines()]
        blocks, cur = [], []
        for x in lines + [""]:
            if x:
                cur.append(x)
            elif cur:
                blocks.append(cur); cur = []
        if len(blocks) == 1 and len(blocks[0]) > 2:          # no blank lines: alternate kind / objects
            blocks = [blocks[0][i:i + 2] for i in range(0, len(blocks[0]), 2)]
        for b in blocks:
            kinds = [x for x in b if " " in x.replace(", ", ",")]
            objs = [x for x in b if x not in kinds]
            warn.append(f"{' / '.join(kinds) or '?'}: {', '.join(objs)}")
    res = {"warnings": warn, "ok": r.returncode == 0 and os.path.exists(out)}
    if res["ok"]:
        with open(out, errors="replace") as f:
            g = f.read()
        t = re.search(r"; estimated printing time \(normal mode\) = (.+)", g)
        w = re.search(r"; total filament used \[g\] = ([\d.]+)", g)
        mm = re.search(r"; filament used \[mm\] = ([\d.]+)", g)
        res.update(time=t.group(1).strip() if t else "?", grams=float(w.group(1)) if w else None,
                   metres=float(mm.group(1)) / 1000 if mm else None)
    else:
        res["error"] = text[-500:]
    return res


def minutes(s):
    h = re.search(r"(\d+)h", s); m = re.search(r"(\d+)m", s)
    return (int(h.group(1)) if h else 0) * 60 + (int(m.group(1)) if m else 0)


def thickness(mesh, n=6000):
    pts, fi = trimesh.sample.sample_surface_even(mesh, n, seed=1)
    nrm = mesh.face_normals[fi]
    org = pts - nrm * 1e-3
    loc, iray, _ = trimesh.ray.ray_triangle.RayMeshIntersector(mesh).intersects_location(org, -nrm, multiple_hits=False)
    d = np.full(len(pts), np.inf)
    d[iray] = np.linalg.norm(loc - org[iray], axis=1)
    return d


def open_point(p, deg):
    """Rotate a closed-assembly point about the hinge axis (lid opening)."""
    a = np.radians(-deg)
    y, z = p[1] - HINGE_AXIS_Y, p[2] - Z_PART
    return np.array([p[0], HINGE_AXIS_Y + y * np.cos(a) - z * np.sin(a), Z_PART + y * np.sin(a) + z * np.cos(a)])


def main():
    exe = slicer()
    lines = ["# Printability report", "",
             "Generated by `tools/print_report.py`. Slicer: " + (f"`{os.path.basename(exe)}` with `tools/a1mini_pla_020.ini` "
             "(an approximation of Bambu Studio's A1 mini 0.20 mm Standard + PLA, 3 walls, 15 % gyroid). Times are "
             "estimates; Bambu Studio's own estimate is the one to trust." if exe else "not found (slicing skipped)."), ""]
    report = {}
    tmp = tempfile.mkdtemp()

    # 1. plates
    if exe:
        lines += ["## Plates", "", "| Plate | Time | Filament | Slicer stability warnings |", "| --- | --- | --- | --- |"]
        total_g, total_min = 0.0, 0
        plates = sorted(glob.glob(os.path.join(CAD, "3mf", "plate*.3mf")))
        for p in plates:
            r = slice_file(exe, p, tmp)
            report[os.path.basename(p)] = r
            if not r["ok"]:
                lines.append(f"| {os.path.basename(p)} | slicing failed | | {r.get('error', '')[:80]} |")
                continue
            if not os.path.basename(p).startswith("plate0"):
                total_g += r["grams"]; total_min += minutes(r["time"])
            lines.append(f"| `{os.path.basename(p)}` | {r['time']} | {r['grams']:.0f} g ({r['metres']:.1f} m) | "
                         f"{'; '.join(r['warnings']) if r['warnings'] else 'none'} |")
        lines += ["", f"Plates 1-3 together: about **{total_g:.0f} g** of PLA and **{total_min // 60} h {total_min % 60:02d} min** "
                  "of printing (plate 0, the test coupons, comes on top).", ""]
        seen = sorted({w.split(":")[0] for r in report.values() if isinstance(r, dict) for w in r.get("warnings", [])})
        for k in seen:
            lines.append(f"- *{k}*: {KNOWN.get(k, 'not reviewed yet - look at it in the slicer preview')}")
        lines.append("")
        report["total_g"], report["total_min"] = total_g, total_min

    # 2. wall thickness
    lines += ["## Wall thickness", "",
              f"Share of each part's surface where the wall measured straight inwards is thinner than {THIN} mm "
              "(two extrusion lines). Small values come from sharp edges and the dovetail jaws.", "",
              "| Part | min (mm) | 1st percentile (mm) | surface < 0.8 mm |", "| --- | --- | --- | --- |"]
    worst = 0.0
    for name, _ in LID_PARTS + BASE_PARTS:
        m = trimesh.load(stl(name))
        d = thickness(m)
        frac = float((d < THIN).mean())
        note = THIN_NOTE.get(name, "")
        if not note:
            worst = max(worst, frac)
        lines.append(f"| {name} | {d.min():.2f} | {np.percentile(d, 1):.2f} | {100 * frac:.2f} %"
                     f"{' (' + note + ')' if note else ''} |")
    lines += ["", f"Largest share apart from the noted part: {100 * worst:.2f} %. " +
              ("OK: only sharp edges and the dovetail jaws." if worst < 0.01 else "CHECK the parts above 1 %."), ""]

    # 3. stability (tipping backwards when open)
    def part_mass(name):
        m = trimesh.load(stl(name))
        if exe:
            r = slice_file(exe, stl(name), tmp)
            if r["ok"] and r["grams"]:
                return r["grams"], m.center_mass
        return m.volume / 1000 * PLA * 0.55, m.center_mass        # rough: 3 walls + 15 % infill ~ 55 % of solid

    lid_m, lid_mc = 0.0, np.zeros(3)
    for name, qty in LID_PARTS:
        g, c = part_mass(name)
        lid_m += g * qty; lid_mc += g * qty * c
    pd_c = np.array([PD_TOP_X - PD_L / 2, 0.0, PANEL_Z_BACK + 2.5])
    bat_c = np.array([BATT_CX, BATT_CY, PANEL_Z_BACK + BATT_T / 2 - 0.75])
    usb_c = np.array([-90.0, USB_PM_Y, USB_PM_Z])
    for g, c in ((PAPERDIY_G, pd_c), (BATTERY_G, bat_c), (USB_CABLE_G, usb_c), (HINGE_G, np.array([0, HINGE_AXIS_Y, Z_PART]))):
        lid_m += g; lid_mc += g * c
    lid_cg = lid_mc / lid_m
    base_m, base_mc = 0.0, np.zeros(3)
    for name, qty in BASE_PARTS:
        g, c = part_mass(name)
        base_m += g * qty; base_mc += g * qty * c
    base_m += HINGE_G; base_mc += HINGE_G * np.array([0, HINGE_AXIS_Y, Z_PART])
    base_cg = base_mc / base_m

    tray = trimesh.load(stl("keyboard_tray") if os.path.exists(os.path.join(OUT_DIR, "keyboard_tray.stl")) else stl("tray_B_main"))
    pivot_y = float(tray.vertices[tray.vertices[:, 2] < 0.05][:, 1].max())   # rearmost point touching the table
    lid = trimesh.load(os.path.join(OUT_DIR, "display_lid_usbc.stl"))
    table_limit = next((d for d in range(0, 181) if np.min([open_point(v, d)[2] for v in lid.vertices[::7]]) < 0), 180)

    need, rows = 0.0, []
    for deg in range(0, table_limit + 1):
        ly = open_point(lid_cg, deg)[1]
        k = (lid_m * (ly - pivot_y) + base_m * (base_cg[1] - pivot_y)) / (pivot_y - KB_CG[1])
        need = max(need, k)
        if deg in (90, 100, 110, 120, 130, 140, table_limit):
            rows.append(f"| {deg} deg | {ly - pivot_y:+.1f} mm | {max(0.0, k):.0f} g |")
    report.update(lid_g=lid_m, base_g=base_m, lid_cg=lid_cg.tolist(), pivot_y=pivot_y, table_limit=table_limit,
                  keyboard_min_g=need)
    lines += ["## Does it tip over backwards?", "",
              f"Lid side (printed parts{' as sliced' if exe else ' (solid estimate)'} + PaperDIY {PAPERDIY_G} g + battery "
              f"{BATTERY_G:g} g + USB-C cable {USB_CABLE_G:g} g + half the hinges): **{lid_m:.0f} g**, centre of mass "
              f"{HINGE_AXIS_Y - lid_cg[1]:.1f} mm in front of the hinge axis when closed. Base without the keyboard: **{base_m:.0f} g**. "
              f"The device rests on the back edge of the tray at y = {pivot_y:.1f} mm; the lid reaches the table at "
              f"{table_limit} deg and is supported from there on.", "",
              "| Opening | lid centre of mass behind the back edge | keyboard needed so it does not tip |", "| --- | --- | --- |"] + rows
    lines += ["", f"**The keyboard has to weigh at least {need:.0f} g** (centre of mass assumed in the middle of the tray) for "
              f"the device to stay on its feet at every angle up to {table_limit} deg. Weigh yours; if it is lighter, "
              "stay below the angle in the table where the needed weight exceeds it, or add weight in the tray.", ""]
    with open(os.path.join(OUT_DIR, "print_report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(OUT_DIR, "print_report.json"), "w") as f:
        json.dump(report, f, indent=1, default=float)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
