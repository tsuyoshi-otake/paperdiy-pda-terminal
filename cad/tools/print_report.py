#!/usr/bin/env python3
"""Printability report for the A1 mini plates.

1. Slices every plate in 3mf/ with PrusaSlicer's command line and an approximation of the Bambu Studio
   A1 mini / 0.20 mm Standard / PLA profile (tools/a1mini_pla_020.ini): print time, filament, and the slicer's
   own "print stability" warnings (floating regions, long bridges, loose extrusions, low bed adhesion).
2. Measures wall thickness on every printed part (rays from the surface inwards).
3. Estimates whether the open device tips over backwards: lid-side mass and centre of mass from the sliced
   part masses plus the bought parts, swept over the opening angle.
4. Kit design: whether the lid stays shut (the hinges' spring-back against the snap) and what it takes to open it.

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
from params import (TPU_FEET, FOOT_H, HINGE_TORQUE, HINGE_TORQUE_TOL, LATCH, BACK_OLD_Y)  # noqa: E402
from params import (OUT_DIR, SPLIT_DIR, Y_BACK, HINGE_AXIS_Y, Z_PART, PD_L, PD_TOP_X, PANEL_Z_BACK, BATT_CX, BATT_CY,  # noqa: E402
                    BATT_T, USB_PM_Y, USB_PM_Z, PD_MOUNT, KIT_MASS_G, KIT_CX, KIT_T, USB_CEIL)

INI = os.path.join(HERE, "a1mini_pla_020.ini")
INI_TPU = os.path.join(HERE, "a1mini_tpu_040.ini")      # for plate4_tpu (the feet)
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
    "Low bed adhesion": ("a small part with little area on the bed: give it a brim (Bambu Studio's brim type Auto "
                         "does)" if PD_MOUNT == "kit" else
                         "the push-rods are 3-4 mm thin bars and the front clips stand 20 mm tall on a 1.6 mm U: keep "
                         "Bambu Studio's brim type on Auto (its default) or give them a brim"),
    "Floating bridge anchors": ("the tray's floor is bridged over the four 0.8 mm pockets for the TPU feet in its bottom "
                                "(16 x 8 mm, anchored in the floor's first layers and its infill; checked in the sliced "
                                "layers: a short, low bridge that prints fine)" if PD_MOUNT == "kit" else
                                "the lid's 1.2 mm ceiling is bridged over the sparse infill of the two hinge housings "
                                "(internal bridges inside solid blocks; checked in the sliced layers)"),
    "Loose extrusions": "the 5 mm counterbore at the panel's screen face is bridged 1.5 mm above the bed "
                        "(same in the real panel, a short bridge that prints fine)",
}
ROD_NOTE = ("the snap tip: each half of the split end is one 1 mm perimeter loop and the barbs are 0.35 mm bumps on "
            "its outline, which the sliced G-code traces")
THIN_NOTE = {"panel_B_main": "the screen-window bevel ends in a sharp edge (as in the original panel)",
             "key_pushrod_x2": ROD_NOTE, "power_pushrod": ROD_NOTE}
if PD_MOUNT == "kit":
    THIN_NOTE["lid_A_left"] = (f"the ceiling over the USB-C channel is {USB_CEIL:g} mm (USB_CEIL), printed as the first "
                               "layers on the bed")
    THIN_NOTE["panel_B_main"] = "the snap bumps on its front and back edges come to a ridge"
    _sp = "the splice-plate pockets at the seam leave half the wall until the plate is glued in"
    for _p in ("lid_A_left", "lid_B_main", "tray_A_left", "tray_B_main", "panel_A_left", "panel_B_main"):
        THIN_NOTE[_p] = (THIN_NOTE[_p] + "; " + _sp) if _p in THIN_NOTE else _sp
    for _c in ("hinge_cover_lid_x2", "hinge_cover_tray_x2"):
        THIN_NOTE[_c] = ("a 1 mm plate; the thin spots are the edges of the screw countersinks and of the cones under "
                         "them, which the screw head and the hinge's countersink hold from both sides")

LID_PARTS = [("lid_A_left", 1), ("lid_B_main", 1), ("panel_A_left", 1), ("panel_B_main", 1), ("paperdiy_strap", 1),
             ("key_pushrod_x2", 2), ("power_pushrod", 1), ("hinge_cover_lid_x2", 2), ("top_plate_blank", 1)]
if PD_MOUNT == "kit":
    LID_PARTS = [("lid_A_left", 1), ("lid_B_main", 1), ("hinge_cover_lid_x2", 2)]
    if os.path.exists(os.path.join(SPLIT_DIR, "panel_B_main.stl")):
        LID_PARTS += [("panel_A_left", 1), ("panel_B_main", 1)]
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


def slice_file(exe, path, tmp, bed=None):
    out = os.path.join(tmp, os.path.basename(path) + ".gcode")
    extra = ["--bed-shape", f"0x0,{bed:g}x0,{bed:g}x{bed:g},0x{bed:g}"] if bed else []
    ini = INI_TPU if "tpu" in os.path.basename(path) else INI
    r = subprocess.run([exe, "--export-gcode", "--load", ini, *extra, "--dont-arrange", "-o", out, path],
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


def lid_stays_shut(report, lid_m, lid_cg, base_m, base_cg):
    """The hinges' spring-back against the snap, and what it takes to open the lid (kit design)."""
    import build                                          # the snap's plate model
    g = 9.81e-3                                           # N per gram
    n = 2
    T, lo, hi = n * HINGE_TORQUE, n * HINGE_TORQUE * (1 - HINGE_TORQUE_TOL), n * HINGE_TORQUE * (1 + HINGE_TORQUE_TOL)
    arm = (HINGE_AXIS_Y - lid_cg[1]) / 1000               # m, lid closed (level): the largest moment
    M = lid_m * g * arm
    lever = (HINGE_AXIS_Y + BACK_OLD_Y) / 1000            # axis to the front face
    push = [(t - M) / lever for t in (lo, T, hi)]
    k, _, _ = build.latch_plate()
    hold = lambda e: k * e * (np.tan(np.radians(LATCH["open_deg"])) + 0.3) / (1 - 0.3 * np.tan(np.radians(LATCH["open_deg"])))  # noqa: E731
    eng = LATCH["bump"] - LATCH["clr"]
    lift = lid_m * g * arm / lever                        # the lid's weight, as a force at the front edge
    f_open = hold(eng) + T / lever - lift
    base_arm, kb_arm = (HINGE_AXIS_Y - base_cg[1]) / 1000, (HINGE_AXIS_Y - KB_CG[1]) / 1000
    kb_one_hand = (hi / g - base_m * base_arm) / kb_arm   # keyboard heavy enough for the base to stay down by itself
    report.update(hinge_torque_nm=[lo, T, hi], lid_moment_nm=M, springback_push_n=push, snap_k=k, snap_hold_n=hold(eng),
                  snap_hold_low_n=hold(eng - 0.15), open_force_n=f_open,
                  keyboard_for_one_hand_g=kb_one_hand)
    return ["## Does the lid stay shut?", "",
            f"The two HG-MF08 are free-stop friction hinges: together {T:.3f} N\u00b7m ({lo:.3f}..{hi:.3f} with their "
            f"\u00b1{100 * HINGE_TORQUE_TOL:.0f} %). The lid side's moment about the axis is at most {M:.3f} N\u00b7m (level, "
            f"{lid_m:.0f} g at {1000 * arm:.1f} mm), so the hinges hold it at any angle ({lo / M:.1f}x at least) and it never "
            "falls shut by itself.", "",
            "Let go, friction hinges turn back a little (the twist stored in them and in their seats). Anywhere else that "
            "is made up for by pushing a little further; at the closed position the lid lands on the tray and cannot go "
            f"further, so it comes up again: every degree at the axis is {1000 * lever * np.radians(1):.1f} mm at the front "
            "edge. The snap is what keeps it down.", "",
            "| | at the front edge |", "| --- | --- |",
            f"| push from the hinges' spring-back, less the lid's weight | {push[0]:.1f}..{push[2]:.1f} N |",
            f"| the snap holds (plate model, {eng:.2f} mm engagement) | {hold(eng):.1f} N |",
            f"| the snap holds if the print leaves {eng - 0.15:.2f} mm | {hold(eng - 0.15):.1f} N |",
            f"| to open: snap + hinge friction - the lid's weight | about {f_open:.1f} N |", "",
            "Press the front of the lid until the snap clicks; a lid that is only laid down stays open by the spring-back. "
            f"To open, hold the base: it weighs {base_m:.0f} g plus the keyboard, less than the pull on the lid, and the hinges "
            f"would carry it up with the lid unless the keyboard weighed about {kb_one_hand:.0f} g.", ""]


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
            if os.path.basename(p)[:6] in ("plate1", "plate2", "plate3"):
                total_g += r["grams"]; total_min += minutes(r["time"])
            lines.append(f"| `{os.path.basename(p)}` | {r['time']} | {r['grams']:.0f} g ({r['metres']:.1f} m) | "
                         f"{'; '.join(r['warnings']) if r['warnings'] else 'none'} |")
        if PD_MOUNT == "kit":
            n = len([p for p in plates if os.path.basename(p)[:6] in ("plate1", "plate2", "plate3")])
            lines += ["", f"Plates 1-{n} together: about **{total_g:.0f} g** of PLA and **{total_min // 60} h {total_min % 60:02d} min** "
                      "of printing (plate 0, the test coupons, comes on top; plate 4, the feet, is TPU, sliced with "
                      "`tools/a1mini_tpu_040.ini`).", ""]
        else:
            lines += ["", f"Plates 1-3 together: about **{total_g:.0f} g** of PLA and **{total_min // 60} h {total_min % 60:02d} min** "
                      "of printing (plate 0, the test coupons, and the optional plates 4 and 5, front clip and magnet jigs, come on top).", ""]
        large = sorted(glob.glob(os.path.join(CAD, "3mf", "large", "plate*.3mf")))
        if large:
            lines += ["### One-piece plates for bigger printers (`3mf/large/`, sliced on a 220 x 220 mm bed)", "",
                      "| Plate | Time | Filament | Slicer stability warnings |", "| --- | --- | --- | --- |"]
            lg, lm = 0.0, 0
            for p in large:
                r = slice_file(exe, p, tmp, bed=220)
                report["large/" + os.path.basename(p)] = r
                if not r["ok"]:
                    lines.append(f"| large/{os.path.basename(p)} | slicing failed | | {r.get('error', '')[:80]} |")
                    continue
                lg += r["grams"]; lm += minutes(r["time"])
                lines.append(f"| `large/{os.path.basename(p)}` | {r['time']} | {r['grams']:.0f} g ({r['metres']:.1f} m) | "
                             f"{'; '.join(r['warnings']) if r['warnings'] else 'none'} |")
            lines += ["", f"Together: about **{lg:.0f} g** and **{lm // 60} h {lm % 60:02d} min**, with nothing to glue.", ""]
            report["large_total_g"], report["large_total_min"] = lg, lm
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
    lines += ["", f"Largest share apart from the noted parts: {100 * worst:.2f} %. " +
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
    bought = ((PAPERDIY_G, pd_c), (BATTERY_G, bat_c), (USB_CABLE_G, usb_c), (HINGE_G, np.array([0, HINGE_AXIS_Y, Z_PART])))
    if PD_MOUNT == "kit":
        with open(os.path.join(OUT_DIR, "assembly.json")) as f:
            kz = json.load(f)["KIT"]["z0"]
        bought = ((KIT_MASS_G, np.array([KIT_CX, 0.0, kz + KIT_T / 2])), (HINGE_G, np.array([0, HINGE_AXIS_Y, Z_PART])))
    for g, c in bought:
        lid_m += g; lid_mc += g * c
    lid_cg = lid_mc / lid_m
    base_m, base_mc = 0.0, np.zeros(3)
    for name, qty in BASE_PARTS:
        g, c = part_mass(name)
        base_m += g * qty; base_mc += g * qty * c
    base_m += HINGE_G; base_mc += HINGE_G * np.array([0, HINGE_AXIS_Y, Z_PART])
    base_cg = base_mc / base_m

    tray = trimesh.load(stl("keyboard_tray") if os.path.exists(os.path.join(OUT_DIR, "keyboard_tray.stl")) else stl("tray_B_main"))
    feet = [tray] + ([trimesh.load(stl("hinge_cover_tray_x2"))]                 # flush tray covers reach the table
                     if os.path.exists(os.path.join(OUT_DIR, "hinge_cover_tray_x2.stl")) else [])
    pivot_y = max(float(m.vertices[m.vertices[:, 2] < 0.05][:, 1].max(initial=-1e9)) for m in feet)   # rearmost point on the table
    if TPU_FEET:                                         # standing on the TPU feet: the rear ones' back edge
        pivot_y = Y_BACK - TPU_FEET["inset"]
    lid = trimesh.load(os.path.join(OUT_DIR, "display_lid_usbc.stl"))
    lv = np.asarray(lid.vertices)
    def lowest(deg):                                  # lowest lid point at this opening (all vertices)
        a = np.radians(-deg)
        return float((Z_PART + (lv[:, 1] - HINGE_AXIS_Y) * np.sin(a) + (lv[:, 2] - Z_PART) * np.cos(a)).min())
    touch = next((d / 10 for d in range(0, 1801) if lowest(d / 10) < -FOOT_H), 180.0)   # first contact, 0.1 deg steps
    table_limit = int(np.ceil(touch)) - 1                # last whole degree with the lid still above the table

    need, rows = 0.0, []
    angles = list(range(0, table_limit + 1)) + [touch]     # whole degrees, then the exact contact angle
    for deg in angles:
        ly = open_point(lid_cg, deg)[1]
        k = (lid_m * (ly - pivot_y) + base_m * (base_cg[1] - pivot_y)) / (pivot_y - KB_CG[1])
        need = max(need, k)
        if deg in (90, 100, 110, 120, 130, 140, 150) or deg is touch:
            rows.append(f"| {deg:.0f} deg | {ly - pivot_y:+.1f} mm | {max(0.0, k):.0f} g |")
    report.update(lid_g=lid_m, base_g=base_m, lid_cg=lid_cg.tolist(), pivot_y=pivot_y, table_contact_deg=touch, table_limit=table_limit,
                  keyboard_min_g=need)
    lines += ["## Does it tip over backwards?", "",
              (f"Lid side (printed parts{' as sliced' if exe else ' (solid estimate)'} + PaperDIY Complete Kit {KIT_MASS_G} g "
               f"+ half the hinges): **{lid_m:.0f} g**, centre of mass " if PD_MOUNT == "kit" else
               f"Lid side (printed parts{' as sliced' if exe else ' (solid estimate)'} + PaperDIY {PAPERDIY_G} g + battery "
               f"{BATTERY_G:g} g + USB-C cable {USB_CABLE_G:g} g + half the hinges): **{lid_m:.0f} g**, centre of mass ") +
              f"{HINGE_AXIS_Y - lid_cg[1]:.1f} mm in front of the hinge axis when closed. Base without the keyboard: **{base_m:.0f} g**. " +
              (f"The device stands on its TPU feet and tips about the rear ones' back edge at y = {pivot_y:.1f} mm; the lid reaches the table at "
               if TPU_FEET else f"The device rests on the back edge of the tray at y = {pivot_y:.1f} mm; the lid reaches the table at ") +
              f"{touch:.1f} deg and is supported from there on.", "",
              "| Opening | lid centre of mass behind the back edge | keyboard needed so it does not tip |", "| --- | --- | --- |"] + rows
    lines += ["", f"**The keyboard has to weigh at least {need:.0f} g** (centre of mass assumed in the middle of the tray) for "
              f"the device to stay on its feet at every angle until the lid rests on the table ({touch:.0f} deg). Weigh yours; if it is lighter, "
              "stay below the angle in the table where the needed weight exceeds it, or add weight in the tray.", ""]
    if PD_MOUNT == "kit":
        lines += lid_stays_shut(report, lid_m, lid_cg, base_m, base_cg)
    with open(os.path.join(OUT_DIR, "print_report.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(os.path.join(OUT_DIR, "print_report.json"), "w") as f:
        json.dump(report, f, indent=1, default=float)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
