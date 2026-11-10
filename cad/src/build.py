#!/usr/bin/env python3
"""Build every output STL + renders for the PaperDIY PDA clamshell.

Run:  python3 ~/cad/src/build.py          (needs: trimesh manifold3d numpy shapely rtree pillow)
Booleans are done with manifold3d on the ORIGINAL phone-enclosure meshes (read-only, never modified).
"""
import os, sys, json, hashlib, glob
import numpy as np
import trimesh
import manifold3d as m3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from params import *          # noqa
import render as R

M, CS = m3.Manifold, m3.CrossSection
SEG = 48
BIG = 1000.0
LOG = []


def log(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    LOG.append(s)


# ------------------------------------------------------------------ helpers
def to_m(tm):
    man = M(m3.Mesh(vert_properties=np.asarray(tm.vertices, np.float32), tri_verts=np.asarray(tm.faces, np.uint32)))
    assert man.status() == m3.Error.NoError, man.status()
    return man


def to_t(man):
    mesh = man.to_mesh()
    return trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=True)


def load(name):
    path = os.path.join(ORIG_DIR, name)
    if not os.path.exists(path):
        sys.exit(f"missing {path}\n  run tools/fetch_original.sh (or set PHONE_ENCLOSURE_STL to the original STL folder)")
    with open(path, "rb") as f:
        digest = hashlib.sha256(f.read()).hexdigest()
    if digest != ORIG_SHA256.get(name) and os.environ.get("PHONE_ENCLOSURE_ANY_VERSION") != "1":
        sys.exit(f"{path}: sha256 {digest[:12]}... is not the pinned original ({ORIG_COMMIT[:7]}).\n"
                 f"  run tools/fetch_original.sh, or set PHONE_ENCLOSURE_ANY_VERSION=1 to build from it anyway")
    return trimesh.load(path)


def box(x0, x1, y0, y1, z0, z1):
    return M.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def rrect(cx, cy, w, h, r):
    if r <= 0:
        return CS.square([w, h], center=True).translate([cx, cy])
    return CS.square([w - 2 * r, h - 2 * r], center=True).offset(r, m3.JoinType.Round, 2.0, SEG).translate([cx, cy])


def prism_z(cs, z0, z1):
    return cs.extrude(z1 - z0).translate([0, 0, z0])


def prism_x(cs_yz, x0, x1):   # cs in (u=y, v=z), extruded along +x
    return cs_yz.extrude(x1 - x0).transform(np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], float))


def prism_y(cs_xz, y0, y1):   # cs in (u=x, v=z), extruded along y (det +1 mapping)
    return cs_xz.extrude(y1 - y0).transform(np.array([[1, 0, 0, 0], [0, 0, -1, y1], [0, 1, 0, 0]], float))


def cyl_z(r, z0, z1, x, y, r2=None):
    return M.cylinder(z1 - z0, r, r if r2 is None else r2, SEG).translate([x, y, z0])


def cyl_x(r, x0, x1, y, z):
    return M.cylinder(x1 - x0, r, r, SEG).rotate([0, 90, 0]).translate([x0, y, z])


def cyl_y(r, y0, y1, x, z):
    return M.cylinder(y1 - y0, r, r, SEG).rotate([-90, 0, 0]).translate([x, y0, z])


def union(parts):
    return M.batch_boolean(list(parts), m3.OpType.Add)


def section_cs(tm, axis, value, region):
    """Cross-section of trimesh `tm` at axis=value as a CrossSection in the other two axes, clipped to region."""
    n = np.zeros(3); n['xyz'.index(axis)] = 1
    o = np.zeros(3); o['xyz'.index(axis)] = value
    s = tm.section(plane_origin=o, plane_normal=n)
    oth = [i for i in range(3) if i != 'xyz'.index(axis)]
    loops = [s.vertices[e.points][:, oth].tolist() for e in s.entities if len(e.points) > 3]
    cs = CS(loops, m3.FillRule.EvenOdd)
    u0, u1, v0, v1 = region
    return cs ^ CS.square([u1 - u0, v1 - v0]).translate([u0, v0])


def dovetail_cs(X, yc, d=DOVETAIL):
    n, h, L = d["neck"] / 2, d["head"] / 2, d["depth"]
    return CS([[[X - 1.0, yc - n], [X, yc - n], [X + L, yc - h], [X + L, yc + h], [X, yc + n], [X - 1.0, yc + n]]])


def split_dovetail(part, X, ys, z0, z1, d=DOVETAIL):
    """z0: a height, or a function of the key's y (keys in a sloping ceiling)."""
    zb = z0 if callable(z0) else (lambda y: z0)
    keys = union(prism_z(dovetail_cs(X, y, d), zb(y) - 0.5, z1 + 0.5) for y in ys)
    keys_c = union(prism_z(dovetail_cs(X, y, d).offset(d["clr"], m3.JoinType.Miter), zb(y) - 0.5, z1 + 0.5) for y in ys)
    A = (part ^ box(-BIG, X, -BIG, BIG, -BIG, BIG)) + (part ^ keys)
    B = (part ^ box(X, BIG, -BIG, BIG, -BIG, BIG)) - keys_c
    return A, B


def split_plain(part, X):
    return part ^ box(-BIG, X, -BIG, BIG, -BIG, BIG), part ^ box(X, BIG, -BIG, BIG, -BIG, BIG)


def split_kit(part, X, ys, z0, z1, d=DOVETAIL):
    """Kit split pieces: a straight cut (SPLIT_JOINT "straight") or one with dovetail keys."""
    return split_plain(part, X) if SPLIT_JOINT == "straight" else split_dovetail(part, X, ys, z0, z1, d)


def export(man, path, check_single=True):
    man = man.simplify(0.002)                      # drop sub-micron slivers left by coplanar booleans
    assert man.status() == m3.Error.NoError and len(man.decompose()) >= 1
    mesh = man.to_mesh()
    raw = trimesh.Trimesh(np.asarray(mesh.vert_properties)[:, :3], np.asarray(mesh.tri_verts), process=False)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw.export(path)
    tm = trimesh.load(path)                        # re-load the written STL = what a slicer sees
    bodies = len(tm.split(only_watertight=False))
    ext = tm.extents
    log(f"  {os.path.relpath(path, os.path.dirname(OUT_DIR))}: bbox {ext[0]:.1f} x {ext[1]:.1f} x {ext[2]:.1f} mm, "
        f"watertight={tm.is_watertight}, winding_ok={tm.is_winding_consistent}, bodies={bodies}, vol={tm.volume:.0f} mm3")
    assert tm.is_watertight, path
    if check_single:
        assert bodies == 1, (path, bodies)
    return tm


# ------------------------------------------------------------------ derived PaperDIY positions (lid frame)
X_TOP = PD_TOP_X
X_USB = X_TOP - PD_L                                  # -59.5
Y_KEYEDGE = PD_CY - PD_W / 2                          # -31.25  (key edge faces the front wall)
KEY_X = [X_TOP - v for v in PD_KEY_FROM_TOP]          # -17.1, -29.1
KEY_TIP_Y = Y_KEYEDGE - PD_KEY_PROTRUDE
KEY_Z = PANEL_Z_BACK + PD_KEY_DEPTH
PWR_TIP_X = X_USB - PD_PWR_PROTRUDE
PWR_Y = Y_KEYEDGE + PD_PWR_FROM_KEYEDGE              # +23.4
PWR_Z = PANEL_Z_BACK + PD_PWR_DEPTH
USB_Y = Y_KEYEDGE + PD_USB_FROM_KEYEDGE              # -24.0
USB_Z = PANEL_Z_BACK + sum(PD_USB_DEPTH) / 2
SO_X, SO_Y = X_TOP - PD_M2_FROM_TOP, PD_CY            # -22.1, 0
SO_TOP = PANEL_Z_BACK + PD_M2_STANDOFF_H              # 23.4
WIN_X0, WIN_X1 = X_USB + PD_WIN_FROM_USB, X_TOP - PD_WIN_FROM_TOP
WIN_CX = (WIN_X0 + WIN_X1) / 2

# battery fit
CAVITY = LID_CEILING_Z - PANEL_Z_BACK
need = BATT_T + BATT_CLR - CAVITY
MAX_RELIEF = min(LID_CEIL_THK, PANEL_Z_BACK - PANEL_Z_FRONT) - MIN_WALL
BATT_POCKET = BATT_RELIEF = max(0.0, need / 2)
BATT_FITS = need <= 2 * MAX_RELIEF + 1e-9
BI_X0, BI_X1 = BATT_CX - BATT_W / 2 - BATT_CLR, BATT_CX + BATT_W / 2 + BATT_CLR
BI_Y0, BI_Y1 = BATT_CY - BATT_L / 2 - BATT_CLR, BATT_CY + BATT_L / 2 + BATT_CLR
BO = (BI_X0 - BATT_WALL, BI_X1 + BATT_WALL, BI_Y0 - BATT_WALL, BI_Y1 + BATT_WALL)
BATT_FRAME_TOP = LID_CEILING_Z - 0.5

# strap
STRAP_UNDER = SO_TOP + STRAP_PAD_DROP                 # 23.9
STRAP_TOP = STRAP_UNDER + STRAP_THK                   # 25.9
STRAP_ENGAGE = STRAP_SCREW_LEN - (STRAP_TOP - SO_TOP)  # countersunk: overall length minus plate under the head


def report_layout():
    log("== derived layout (lid frame, mm)")
    log(f"  PaperDIY: x {X_USB:.2f}..{X_TOP:.2f}, y {Y_KEYEDGE:.2f}..{-Y_KEYEDGE:.2f}, screen face z={PANEL_Z_BACK}")
    log(f"  window (inner face) x {WIN_X0:.2f}..{WIN_X1:.2f} ({PD_WIN_W}) , y +-{PD_WIN_H/2:.2f}")
    log(f"  M2 standoff ({SO_X:.2f},{SO_Y:.2f}) top z={SO_TOP:.2f}; keys x={KEY_X} tip y={KEY_TIP_Y:.2f} z={KEY_Z:.2f}")
    log(f"  power tip x={PWR_TIP_X:.2f} y={PWR_Y:.2f} z={PWR_Z:.2f}; USB-C centre y={USB_Y:.2f} z={USB_Z:.2f} tip x={X_USB-PD_USB_PROTRUDE:.2f}")
    log(f"  strap: underside z={STRAP_UNDER:.2f}, top z={STRAP_TOP:.2f}, plate under screw head {STRAP_TOP-SO_TOP:.2f};"
        f" M2x{STRAP_SCREW_LEN:g} countersunk -> {STRAP_ENGAGE:.2f} mm thread into standoff (limit < {PD_MAX_THREAD})")
    assert 1.0 <= STRAP_ENGAGE < PD_MAX_THREAD - 0.4, "screw engagement out of range"
    log(f"  battery {BATT_L}x{BATT_W}x{BATT_T}: lid cavity {CAVITY:.2f}, needs +{need:.2f} -> panel pocket {BATT_POCKET:.2f} + ceiling relief {BATT_RELIEF:.2f}"
        f" (max {MAX_RELIEF:.2f} each, leaves >= {MIN_WALL}) -> {'FITS' if BATT_FITS else 'DOES NOT FIT'};"
        f" cell top z={PANEL_Z_BACK-BATT_POCKET+BATT_T:.2f}, ceiling z={LID_CEILING_Z+BATT_RELIEF:.2f}")


# ------------------------------------------------------------------ PANEL
def build_panel():
    P = to_m(load("Display Panel.stl"))
    z0, z1 = PANEL_Z_FRONT, PANEL_Z_BACK
    fill = [box(-89.0, 89.0, -36.6, 36.0, z0, z1)]                 # original window + Palma slots
    if not PANEL_KEEP_VENTS:
        fill += [box(s * 81.5 if s > 0 else -92.1, s * 92.1 if s > 0 else -81.5, -26.6, -6.7, z0, z1) for s in (1, -1)]
    P = P + union(fill)
    # window (bevel opens toward the screen face)
    c = WIN_CHAMFER
    k = c * 3.5 / (z1 - z0)
    top = prism_z(rrect(WIN_CX, PD_CY, PD_WIN_W, PD_WIN_H, 1.0), z1, z1 + 0.6)
    bot = prism_z(rrect(WIN_CX, PD_CY, PD_WIN_W + 2 * k, PD_WIN_H + 2 * k, 1.0 + k), z0 - 0.6, z0 - 0.5)
    P = P - M.batch_hull([top, bot])
    # locating rim around the display glass
    iw, ih = PD_L + 2 * FIT, PD_W + 2 * FIT
    cx = (X_TOP + X_USB) / 2
    rim = prism_z(rrect(cx, PD_CY, iw + 2 * RIM_W, ih + 2 * RIM_W, 0) - rrect(cx, PD_CY, iw, ih, 0), z1 - 0.01, z1 + RIM_H)
    rim = rim - box(X_USB - 3, X_USB + 1, USB_Y - 6, USB_Y + 6, z1 - 1, z1 + 5)          # USB plug gap
    P = P + rim
    # strap posts: pilot holes for M2x8 tapping screws (or M2 heat-set insert holes)
    h = STRAP_POST_SIZE / 2
    for sy in (1, -1):
        y = sy * STRAP_POST_Y
        P = P + box(STRAP_X - h, STRAP_X + h, y - h, y + h, z1 - 0.01, STRAP_UNDER)
        if FASTENING == "tapping":    # screw passes the 2 mm strap, ~6 mm into post + panel
            P = P - cyl_z(SCREW_PILOT_D / 2, STRAP_UNDER - (TAP_SCREW_LEN - STRAP_THK) - 0.5, STRAP_UNDER + 1, STRAP_X, y)
        else:
            P = P - cyl_z(INSERT_M2_D / 2, STRAP_UNDER - INSERT_M2_L - 1.0, STRAP_UNDER + 1, STRAP_X, y)
    # push-rod cradles (open-top U)
    w = ROD_HOLE / 2 + MIN_WALL
    for x in KEY_X:
        P = P + box(x - w, x + w, -41.6, -39.6, z1 - 0.01, KEY_Z + 0.8)
        P = P - box(x - ROD_HOLE / 2, x + ROD_HOLE / 2, -42, -39, KEY_Z - ROD_FLAT - 0.1, 40)
    for x in (-92.0, -80.0):
        P = P + box(x - 1.5, x + 1.5, PWR_Y - w, PWR_Y + w, z1 - 0.01, PWR_Z + 0.8)
        P = P - box(x - 2, x + 2, PWR_Y - ROD_HOLE / 2, PWR_Y + ROD_HOLE / 2, PWR_Z - ROD_FLAT - 0.1, 40)
    # relief under the USB-C plug overmold (panel stays 2.0 thick)
    P = P - box(-90.0, X_USB - PD_USB_PROTRUDE - 0.35, USB_Y - 7.5, USB_Y + 7.5, z1 - 1.0, z1 + 0.1)
    # battery bay: pocket + frame (+ wire notch toward the PaperDIY)
    if BATT_POCKET > 0:
        P = P - prism_z(rrect((BI_X0 + BI_X1) / 2, (BI_Y0 + BI_Y1) / 2, BI_X1 - BI_X0, BI_Y1 - BI_Y0, 1.0), z1 - BATT_POCKET, z1 + 1)
    frame = box(BO[0], BO[1], BO[2], BO[3], z1 - 0.01, BATT_FRAME_TOP) - box(BI_X0, BI_X1, BI_Y0, BI_Y1, z1 - 2, 40)
    frame = frame - box(BO[0] - 1, BI_X0 + 0.1, BATT_CY - 3, BATT_CY + 3, BATT_FRAME_TOP - 5, 40)
    frame = frame - box(80.5, 88.6, BO[2] - 1, BI_Y0 + 0.05, 22.2, 40)   # clear the lid's original corner rib (flares to y=-30.2)
    P = P + frame
    return P


def build_strap():
    h = STRAP_THK
    s = box(STRAP_X - STRAP_W / 2, STRAP_X + STRAP_W / 2, -STRAP_POST_Y - 3.2, STRAP_POST_Y + 3.2, STRAP_UNDER, STRAP_TOP)
    s = s + cyl_z(3.25, SO_TOP, STRAP_UNDER + 0.01, SO_X, SO_Y)
    if STRAP_LEGS:   # arms to two legs just past the PCB's inner end: the PCB cannot turn about the standoff
        g = STRAP_LEGS
        x_pcb = X_TOP - PD_PCB_TOP_FROM_TOP                 # PCB inner end, -12.1
        x0, x1 = x_pcb + g["gap"], x_pcb + g["gap"] + g["t"]
        z_foot = PANEL_Z_BACK + 1.2 + g["foot_clear"]       # display back (glass 1.2) + clearance
        r = STRAP_RAILS
        for sgn in (1.0, -1.0):
            ya, yb = sorted((sgn * g["arm_y"][0], sgn * g["arm_y"][1]))
            yl0, yl1 = sorted((sgn * g["leg_y"][0], sgn * g["leg_y"][1]))
            s = s + box(STRAP_X + STRAP_W / 2 - 0.5, x1, ya, yb, STRAP_UNDER, STRAP_TOP)
            s = s + box(x0, x1, yl0, yl1, z_foot, STRAP_UNDER + 0.01)
            if r:   # ribbed rail from the leg to near the far end of the glass, with feet on the display's back
                yc, hw = (ya + yb) / 2, r["width"] / 2
                s = s + box(x1 - 0.5, r["x_end"], yc - hw, yc + hw, STRAP_UNDER, STRAP_TOP)
                s = s + box(x1 - 0.5, r["x_end"] - 0.3, yc - r["rib_t"] / 2, yc + r["rib_t"] / 2, r["rib_bottom"], STRAP_UNDER + 0.3)
                for xf in r["feet_x"]:
                    s = s + box(xf - r["foot_len"] / 2, xf + r["foot_len"] / 2, yc - hw + 0.05, yc + hw - 0.05, z_foot, STRAP_UNDER + 0.3)
    for (x, y, zb) in [(STRAP_X, STRAP_POST_Y, STRAP_UNDER), (STRAP_X, -STRAP_POST_Y, STRAP_UNDER), (SO_X, SO_Y, SO_TOP)]:
        s = s - cyl_z(M2_CLEAR / 2, zb - 1, STRAP_TOP + 1, x, y)
        s = s - cyl_z(M2_CLEAR / 2, STRAP_TOP - (CSK_D - M2_CLEAR) / 2, STRAP_TOP + 0.01, x, y, CSK_D / 2)  # 90 deg countersink
    return s


def magnet_hole_xs():
    return [s * (LID_INNER_X + 3.0 - d) for s in (-1.0, 1.0) for d in MAGNETS["from_end"]]


def magnet_holes(side):
    """Drill holes for the magnetic catch: side "tray" (down from the land) or "lid" (up from it)."""
    m, z = MAGNETS, MAGNETS["land_z"]
    z0, z1 = (z - m["depth"], z + 1.0) if side == "tray" else (z - 1.0, z + m["depth"])
    return [cyl_z(m["d"] / 2, z0, z1, x, m["y"]) for x in magnet_hole_xs()]


def build_magnet_jig():
    """Left-hand drilling jig for the magnetic catch, in the tray's frame at its front-left corner (x = -101). It sits on
    the front wall's land, straddles the wall with two fingers and stops against the end face with a fence; the guide bores
    are MAGNETS["from_end"] from that face. The mirror image (x -> -x) is the right-hand jig; on the lid (upside down) the
    other hand fits the same corner."""
    j, m = MAG_JIG, MAGNETS
    zl, c, w = m["land_z"], j["clr"], j["wall"]
    xe = -(LID_INNER_X + 3.0)                             # end face (x = -101)
    y_out, y_in = -(LID_INNER_Y + 3.0), -LID_INNER_Y      # front wall faces (y = -46.5, -43.5)
    x1 = xe + max(m["from_end"]) + 8.0
    yo, yi = y_out - c - w, y_in + c + w                  # outer edges of the fingers
    top = zl + j["h"]
    parts = [box(j["straight_x"], x1, yo, yi, zl, top),                                          # bar on the land
             box(xe - c - j["fence_t"], j["straight_x"], yo, j["fence_y"][1], j["corner_z"], top),  # over the corner
             box(xe - c - j["fence_t"], xe - c, *j["fence_y"], zl - 4.0, j["corner_z"]),           # fence on the end face
             box(j["straight_x"], x1, yo, y_out - c, zl - j["finger"], zl),                        # outer finger
             box(j["straight_x"], x1, y_in + c, yi, zl - j["finger"], zl)]                         # inner finger
    jig = union(parts)
    for d in m["from_end"]:
        x = xe + d
        jig = jig - cyl_z(j["guide_d"] / 2, zl - j["finger"] - 1.0, top + 1.0, x, m["y"])
        jig = jig - M.cylinder(1.2, j["guide_d"] / 2, 2.2, SEG).translate([x, m["y"], top - 1.2])  # lead-in
    return jig


def build_front_clip(lid, tray, bumps=True):
    """Accessory: push-on U clip for the front edge of the closed case (CLIP_* in params). The profile is the outline of
    the closed lid + tray at x = CLIP_X, so the clip hugs the front face and the 3 mm chamfers with CLIP_CLR."""
    to_yz = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]], float)        # (x, y, z) -> (y, z, x)
    outer = (lid + tray).transform(to_yz).slice(CLIP_X).hull()
    y0, z0, y1, z1 = outer.bounds()
    y_tip = y0 + CLIP_LIP
    keep = CS.square([CLIP_LIP + 10.0, z1 - z0 + 20.0]).translate([y_tip - CLIP_LIP - 10.0, z0 - 10.0])
    u = (outer.offset(CLIP_CLR + CLIP_T, m3.JoinType.Round, 2.0, SEG)
         - outer.offset(CLIP_CLR, m3.JoinType.Round, 2.0, SEG)) ^ keep
    if bumps:   # ridges 2 mm from the lip tips, CLIP_BUMP into the lid top / tray bottom
        for zc in (z1 + CLIP_BUMP_R - CLIP_BUMP, z0 - CLIP_BUMP_R + CLIP_BUMP):
            u = u + CS.circle(CLIP_BUMP_R, SEG).translate([y_tip - 2.0, zc])
    return prism_x(u, CLIP_X - CLIP_W / 2, CLIP_X + CLIP_W / 2)


def dflat(rod, zc):        # flat underside ROD_FLAT below the axis: prints flat, rests on the U-cradle floor
    return rod ^ box(-BIG, BIG, -BIG, BIG, zc - ROD_FLAT, BIG)


ROD_WALL = 3.0             # the lid walls the rods pass through (front y -46.5..-43.5, left side x -101..-98)


def rod_local(length):
    """Push-rod in its own frame: axis along x, x = 0 at the wall's outer face, +x inward to the tip at `length`;
    y across (the snap slot splits the rod into +y / -y halves), z up with the flat underside at z = -ROD_FLAT."""
    r0, rc = ROD_D / 2, ROD_COLLAR_D / 2
    collar = cyl_x(rc, ROD_WALL, ROD_WALL + ROD_COLLAR_T, 0, 0)
    if not ROD_SNAP:
        return dflat(cyl_x(r0, -ROD_PROUD, length, 0, 0) + collar, 0.0)
    s = ROD_SNAP
    rb = ROD_HOLE / 2
    x_catch = -s["play"]                                   # barb faces: `play` outside the wall with the collar home
    x_land = x_catch - s["land"]
    x_end = x_land - s["lead"]
    rod = cyl_x(r0, x_catch - 0.01, length, 0, 0)
    for sg in (1.0, -1.0):
        barb = M.batch_hull([cyl_x(rb, x_land, x_catch, sg * s["catch"], 0),
                             cyl_x(s["tip_r"], x_end, x_end + 0.01, 0, 0)])
        half = box(-BIG, BIG, s["slot"] / 2, BIG, -BIG, BIG) if sg > 0 else box(-BIG, BIG, -BIG, -s["slot"] / 2, -BIG, BIG)
        rod = rod + (barb ^ half)
    x_root = x_catch - s["land"] / 2 + s["slot_len"]
    rod = (rod ^ (box(x_root + s["slot"] / 2, BIG, -BIG, BIG, -BIG, BIG) + box(-BIG, BIG, -BIG, BIG, -BIG, s["top"]))) + collar
    slot = box(x_end - 1.0, x_root, -s["slot"] / 2, s["slot"] / 2, -BIG, BIG) + cyl_z(s["slot"] / 2, -10, 10, x_root, 0)
    return dflat(rod - slot, 0.0)


def build_key_rod(x):
    y_out = -(LID_INNER_Y + ROD_WALL)
    r = rod_local(KEY_TIP_Y - ROD_GAP - y_out)
    return r.rotate([0, 0, 90]).translate([x, y_out, KEY_Z])     # local x -> +y (inward), local y -> -x


def build_power_rod():
    x_out = -(LID_INNER_X + ROD_WALL)
    return rod_local(PWR_TIP_X - ROD_GAP - x_out).translate([x_out, PWR_Y, PWR_Z])


# ------------------------------------------------------------------ LID
# ------------------------------------------------------------------ HINGE REWORK (lid + tray)
def poly_cs(pts):
    """CrossSection from a (u, v) polygon, either winding."""
    pts = np.asarray(pts, float)
    area = 0.5 * np.sum(pts[:, 0] * np.roll(pts[:, 1], -1) - np.roll(pts[:, 0], -1) * pts[:, 1])
    if area < 0:
        pts = pts[::-1]
    return CS([pts.tolist()])


# back-wall profiles in (y, z), read from the original meshes at x = +-65 (outside the old hinge)
LID_BACK_PROFILE = [(40.0, 27.0), (42.26, 27.0), (43.5, 25.76), (43.5, 12.78), (44.68, 12.84), (45.5, 12.89),
                    (46.5, 13.94), (46.5, 27.0), (43.5, 30.0), (40.0, 30.0)]
TRAY_BACK_PROFILE = [(40.0, 0.0), (43.5, 0.0), (46.5, 3.0), (46.5, 11.94), (45.5, 12.89), (44.5, 12.83),
                     (43.5, 11.78), (43.5, 3.0), (40.0, 3.0)]


def rebuild_back(part, profile, z0, z1):
    """Remove the old hinge (knuckle / ears / trough) behind the back wall and rebuild a plain wall."""
    X = BACK_ZONE_X
    return (part - box(-X, X, LID_INNER_Y - 0.05, 70.0, z0, z1)) + prism_x(poly_cs(profile), -X, X)


def warp_back(part, lower_rim=0.0, extra=None):
    """Thicken the back wall outward by BACK_EXTRA: move the outer half of the wall (and the top / bottom
    chamfers and the rounded back corners) back, leave the inner pocket untouched."""
    extra = BACK_EXTRA if extra is None else extra
    tm = to_t(part)
    v = tm.vertices.copy()
    ax, y, z = np.abs(v[:, 0]), v[:, 1], v[:, 2]
    cx, cy = CORNER_C
    zc = (z < 2.95) | (z > 27.05)                      # top chamfer of the lid / bottom chamfer of the tray
    r = np.hypot(ax - cx, y - cy)
    straight = (y > 45.0) | ((y > 43.0) & zc)
    corner = (y > cy) & ((r > 4.5) | (zc & (r >= 2.9)))
    move = np.where(ax <= cx, straight, corner)
    v[move, 1] += extra
    if lower_rim:          # tray only: the warped lid / tray parting surfaces differ by <= 0.05 mm; keep a gap
        v[z > 12.3, 2] -= lower_rim
    return to_m(trimesh.Trimesh(v, tm.faces, process=False))


def hinge_centres():
    return (-HINGE_X, HINGE_X)


def housing_zone():
    """Where the thick back wall is kept with BACK_STYLE = "housings": a block behind each hinge plus a tapered rib
    (gusset) each side, in plan view; full height (the thick wall's own top / bottom chamfers shape it)."""
    zone = []
    g, y0 = HOUSING_GUSSET, LID_INNER_Y + 0.5
    for c in hinge_centres():
        x0, x1 = c - HOUSING_HALF, c + HOUSING_HALF
        zone.append(box(x0, x1, y0, Y_BACK + 2.0, -5.0, 40.0))
        for xe, s in ((x0, -1.0), (x1, 1.0)):
            pts = [(xe, y0), (xe, Y_BACK + 0.5), (xe + s * g, BACK_OLD_Y), (xe + s * g, y0)]
            zone.append(prism_z(poly_cs(pts), -5.0, 40.0))
    return union(zone)


def slim_back(thin, thick):
    """3 mm back wall with a 9.5 mm housing (and its gussets) behind each hinge."""
    if BACK_STYLE != "housings":
        return thick
    zone = housing_zone()             # each region from one source only: near-coplanar faces would leave slivers
    m = (thin - zone) + (thick ^ zone)
    # the original mesh and the rebuilt profile meet at x = +-BACK_ZONE_X with ~0.01 mm steps on the parting face;
    # cutting there can leave a zero-volume flap as a separate component: drop it
    return union([p for p in m.decompose() if p.volume() > 1.0])


def lid_ribs():
    """Triangular ribs between the lid's long walls and its ceiling (in print orientation they stand on the bed)."""
    if BACK_STYLE != "housings":
        return []
    r, out = LID_RIBS, []
    zt = LID_CEILING_Z
    for side, xs in ((1.0, r["back_x"]), (-1.0, r["front_x"])):
        w = side * LID_INNER_Y
        tri = [(w + side * 0.5, zt + 0.5), (w - side * r["depth"], zt + 0.5), (w + side * 0.5, zt - r["drop"])]
        out += [prism_x(poly_cs(tri), x - r["t"] / 2, x + r["t"] / 2) for x in xs]
    return out


def hinge_pocket_cuts():
    """Pockets for the leaves + a slot for the barrel on the axis (y = Y_BACK, z = Z_PART).
    parting: each leaf lies in a 2 mm pocket in the parting face (tray leaf below, lid leaf above), pointing forward.
    face:    both leaves in a 2 mm mortise in the outer back face."""
    cuts = []
    rc = HINGE_BARREL_D / 2 + 0.35
    for c in hinge_centres():
        x0, x1 = c - HINGE_LEN / 2 - HINGE_CLR, c + HINGE_LEN / 2 + HINGE_CLR
        if HINGE_MOUNT == "parting":
            cuts.append(box(x0, x1, Y_BACK - HINGE_WIDTH / 2 - HINGE_CLR, Y_BACK + 1.0,
                            Z_PART - HINGE_LEAF_T - 0.05, Z_PART + HINGE_LEAF_T + 0.05))
        else:
            zlo = Z_PART - HINGE_WIDTH / 2 - HINGE_CLR
            zlo = -1.0 if zlo < 1.0 else zlo          # within 1 mm of the bottom: run out through it (no 0.1 mm skin)
            cuts.append(box(x0, x1, Y_BACK - HINGE_SINK - HINGE_LEAF_T - 0.05, Y_BACK + 1.0, zlo,
                            Z_PART + HINGE_WIDTH / 2 + HINGE_CLR))
            if COVER_FLUSH:        # pockets for the flush covers (the tray's runs out through the bottom, the lid's
                k = COVER_POCKET_CLR   # through the top), with a deeper strip each side for the covers' lips
                hw = cover_half_w()
                for z0, z1 in cover_spans():
                    z0 = -1.0 if z0 <= 0.0 else z0 - k
                    z1 = z1 + k if z1 < top_z(Y_BACK) - 0.01 else z1 + 5.0
                    cuts.append(prism_y(rrect(c, (z0 + z1) / 2, 2 * hw + 2 * k, z1 - z0, COVER_R + k),
                                        Y_BACK - COVER_T, Y_BACK + 1.0))
                    if COVER_LIP:
                        lp = COVER_LIP
                        for sx in (-1, 1):
                            xa, xb = sorted((c + sx * (hw - lp["w"] - k), c + sx * (hw + k)))
                            cuts.append(box(xa, xb, Y_BACK - COVER_T - lp["d"] - lp["clr"], Y_BACK - COVER_T + 0.01, z0, z1))
        for yc in (Y_BACK, Y_BACK - 0.8):          # slot: tolerates the axis sitting up to 0.8 mm inside the face
            cuts.append(cyl_x(rc, x0, x1, yc, Z_PART))
        cuts.append(box(x0, x1, Y_BACK - 0.8, Y_BACK, Z_PART - rc, Z_PART + rc))
    return cuts


def hinge_pilots(lid):
    """Pilot holes at the catalogue hole positions, from the leaf seat into the wall."""
    if not HINGE_PILOT_HOLES:
        return []
    out = []
    for c in hinge_centres():
        for dx in (-HINGE_HOLE_PITCH_X / 2, HINGE_HOLE_PITCH_X / 2):
            x = c + dx
            if HINGE_MOUNT == "parting":    # vertical holes, M2x8: ~6 mm past the leaf seat
                y = Y_BACK - HINGE_HOLE_OFF
                if lid:
                    out.append(cyl_z(HINGE_PILOT_D / 2, Z_PART + HINGE_LEAF_T - 0.1, Z_PART + HINGE_LEAF_T + 6.5, x, y))
                else:
                    out.append(cyl_z(HINGE_PILOT_D / 2, Z_PART - HINGE_LEAF_T - 6.5, Z_PART - HINGE_LEAF_T + 0.1, x, y))
            else:
                seat = Y_BACK - HINGE_SINK - HINGE_LEAF_T
                depth = HINGE_SCREW_DEPTH        # M2x8, head flush in the back face (in the cover or the leaf countersink)
                zz = Z_PART + HINGE_HOLE_OFF if lid else Z_PART - HINGE_HOLE_OFF
                out.append(cyl_y(HINGE_PILOT_D / 2, seat - depth, seat + 0.1, x, zz))
    return out


def lid_hinge_bosses():
    behind = BACK_OLD_Y - LID_INNER_Y + BACK_EXTRA - HINGE_LEAF_T - HINGE_SINK   # wall behind the leaf seat
    if HINGE_MOUNT == "parting" or behind >= HINGE_SCREW_DEPTH + 1.0:   # wall alone holds the screws
        return []
    b = LID_HINGE_BOSS
    return [box(c - b["w"] / 2, c + b["w"] / 2, LID_INNER_Y - b["depth"], LID_INNER_Y + 0.1, b["z0"], b["z1"])
            for c in hinge_centres()]


def hinge_envelope(open_deg=0.0):
    """Simplified hinges (2 leaves + barrel each) for checks; the lid leaf follows the lid."""
    fixed, moving = [], []
    r = HINGE_BARREL_D / 2
    for c in hinge_centres():
        x0, x1 = c - HINGE_LEN / 2, c + HINGE_LEN / 2
        if HINGE_MOUNT == "parting":
            fixed.append(box(x0, x1, Y_BACK - HINGE_WIDTH / 2, Y_BACK - r, Z_PART - HINGE_LEAF_T, Z_PART))
            moving.append(box(x0, x1, Y_BACK - HINGE_WIDTH / 2, Y_BACK - r, Z_PART, Z_PART + HINGE_LEAF_T))
        else:     # flat back on the mortise floor, barrel on the front around the real axis
            seat = Y_BACK - HINGE_SINK - HINGE_LEAF_T - 0.05
            fixed.append(box(x0, x1, seat, seat + HINGE_LEAF_T, Z_PART - HINGE_WIDTH / 2, Z_PART - r))
            moving.append(box(x0, x1, seat, seat + HINGE_LEAF_T, Z_PART + r, Z_PART + HINGE_WIDTH / 2))
        fixed.append(cyl_x(r, x0, x1, HINGE_AXIS_Y if HINGE_MOUNT == "face" else Y_BACK, Z_PART))
    return union(fixed), open_lid(union(moving), open_deg)


def build_top_plate():
    x0, x1, y0, y1 = LID_LABEL_POCKET
    return prism_z(rrect((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 0.3, y1 - y0 - 0.3, 1.5), 28.5, 30.0)


def write_assembly_json():
    """Positions the README renderer needs (docs/render reads this instead of copying numbers)."""
    data = dict(Y_BACK=Y_BACK, Z_PART=Z_PART, HINGE_AXIS_Y=HINGE_AXIS_Y if HINGE_MOUNT == "face" else Y_BACK, HINGE_X=HINGE_X, HINGE_LEN=HINGE_LEN, HINGE_WIDTH=HINGE_WIDTH,
                HINGE_LEAF_T=HINGE_LEAF_T, HINGE_BARREL_D=HINGE_BARREL_D, HINGE_CLR=HINGE_CLR,
                HINGE_COVER=bool(HINGE_COVER and HINGE_MOUNT == "face"), COVER_T=COVER_T, COVER_RIM=COVER_RIM,
                COVER_R0=COVER_R0, COVER_SCREWED=bool(COVER_SCREWED and HINGE_COVER and HINGE_MOUNT == "face"),
                COVER_FLUSH=COVER_FLUSH, COVER_Y_OUT=Y_BACK if COVER_FLUSH else Y_BACK + COVER_T, HINGE_SINK=HINGE_SINK,
                TRAY_FLOOR=TRAY_FLOOR, KB_SIZE=list(KB_SIZE) if KB_SIZE else None,
                HINGE_HOLE_OFF=HINGE_HOLE_OFF, HINGE_HOLE_PITCH_X=HINGE_HOLE_PITCH_X,
                HINGE_MOUNT=HINGE_MOUNT, LABEL_POCKET=list(LID_LABEL_POCKET),
                USB_PM_Y=USB_PM_Y, USB_PM_Z=USB_PM_Z,
                BATT=dict(cx=BATT_CX, cy=BATT_CY, z0=PANEL_Z_BACK - BATT_POCKET, L=BATT_L, W=BATT_W, T=BATT_T),
                STRAP=dict(x=STRAP_X, w=STRAP_W, y=STRAP_POST_Y, top=STRAP_TOP), PD_MOUNT=PD_MOUNT)
    if PD_MOUNT == "kit":
        data.update(LID_TOP=[LID_TOP[0], LID_TOP[1]], LID_UNDER=list(LID_UNDER), PANEL=SHELL,
                    COVER_LID_Z1=min(Z_PART + HINGE_WIDTH / 2 + HINGE_CLR + COVER_TOP_RIM, top_z(Y_BACK) - LID_CHAMFER),
                    KIT=dict(cx=KIT_CX, z0=KIT_Z0, L=KIT_L, W=KIT_W, T=KIT_T, R=KIT_R, win=list(KIT_WIN), win_off=KIT_WIN_OFF,
                             usb_y=KIT_USB_Y, usb_z=list(KIT_USB_Z)))
    with open(os.path.join(OUT_DIR, "assembly.json"), "w") as f:
        json.dump(data, f, indent=1)


def cover_half_w():
    return HINGE_LEN / 2 + HINGE_CLR + COVER_RIM


def cover_spans():
    """(z0, z1) of the lid cover and of the tray cover."""
    leaf_end = HINGE_WIDTH / 2 + HINGE_CLR + COVER_RIM
    z_top = (min(Z_PART + HINGE_WIDTH / 2 + HINGE_CLR + COVER_TOP_RIM, top_z(Y_BACK) - LID_CHAMFER) if PD_MOUNT == "kit"
             else min(Z_PART + leaf_end, 26.8))                                 # stop below the lid's top chamfer
    z_bot = 0.0 if COVER_FLUSH else max(0.3, Z_PART - leaf_end)                 # flush: down to the tray bottom
    return (Z_PART + COVER_R0, z_top), (z_bot, Z_PART - COVER_R0)


def hinge_covers(ribs=True):
    """Cover plates over the leaves (face mounting), in the closed assembly position: (lid covers, tray covers).
    Kit: flush in the back face (y Y_BACK - COVER_T .. Y_BACK), a countersunk hole at each leaf hole and under it a cone
    that fills the leaf's countersink; the hinge screw then clamps cover and leaf; crush ribs on the side edges hold it
    in its pocket before the screws go in (ribs=False: without them, for the clearance checks). Bare: glued on."""
    if HINGE_MOUNT != "face" or not HINGE_COVER:
        return [], []
    lid_c, tray_c = [], []
    half_w = cover_half_w()
    y0 = Y_BACK - COVER_T if COVER_FLUSH else Y_BACK
    y1 = y0 + COVER_T
    for c in hinge_centres():
        for side, (z0, z1) in zip((1, -1), cover_spans()):
            ch = COVER_EDGE_CHAMFER if COVER_FLUSH else 0.0    # round the outer face (on the bed in print)
            outline = rrect(c, (z0 + z1) / 2, 2 * half_w, z1 - z0, COVER_R)
            cov = prism_y(outline, y0, y1 - ch)
            if ch:
                cov = cov + M.batch_hull([prism_y(outline, y1 - ch - 0.01, y1 - ch),
                                          prism_y(outline.offset(-ch, m3.JoinType.Round, 2.0, SEG), y1 - 0.01, y1)])
            yb = y0                    # back of the cover (deepest point of its sides)
            if COVER_LIP:              # lips along both side edges, into the pocket's deeper strips
                lp = COVER_LIP
                yb = y0 - lp["d"]
                for sx in (-1, 1):
                    xa, xb = sorted((c + sx * (half_w - lp["w"]), c + sx * half_w))
                    cov = cov + (box(xa, xb, yb, y0 + 0.01, z0, z1) ^ prism_y(rrect(c, (z0 + z1) / 2, 2 * half_w, z1 - z0,
                                                                                    COVER_R), yb - 1.0, y1))
            if COVER_RIBS and ribs:    # tapered crush ribs on the straight part of both side edges
                rb = COVER_RIBS
                n = rb["per_side"]
                for sx in (-1, 1):
                    xc = c + sx * (half_w - (rb["r"] - rb["h"]))
                    for i in range(n):
                        zr = z0 + 1.0 + (z1 - z0 - 2.0) * (i + 0.5) / n
                        # protrusion COVER_POCKET_CLR at the back (just touches) -> h where the outer chamfer starts
                        cov = cov + (M.cylinder(y1 - ch - yb, rb["r"] - rb["h"] + COVER_POCKET_CLR, rb["r"], SEG)
                                     .rotate([-90, 0, 0]).translate([xc, yb, zr]))
            if COVER_SCREWED:
                k = COVER_CSK
                zc = Z_PART + side * HINGE_HOLE_OFF
                for dx in (-HINGE_HOLE_PITCH_X / 2, HINGE_HOLE_PITCH_X / 2):
                    x = c + dx
                    cone_r1 = k["cone_d"] / 2 - k["cone_h"]                       # 90 deg
                    cov = cov + (M.cylinder(k["cone_h"] + 0.01, cone_r1, k["cone_d"] / 2, SEG)
                                 .rotate([-90, 0, 0]).translate([x, y0 - k["cone_h"], zc]))
                    csk_h = (k["top_d"] - k["hole_d"]) / 2
                    cov = cov - cyl_y(k["hole_d"] / 2, y0 - k["cone_h"] - 0.1, y1 + 0.1, x, zc)
                    cov = cov - (M.cylinder(csk_h + 0.01, k["hole_d"] / 2, k["top_d"] / 2 + 0.01, SEG)
                                 .rotate([-90, 0, 0]).translate([x, y1 - csk_h, zc]))
                    cov = cov - cyl_y(k["top_d"] / 2 + 0.01, y1, y1 + 1.0, x, zc)
            (lid_c if side > 0 else tray_c).append(cov)
    return lid_c, tray_c


def first_contact(lidset, traset, axis_shift=0.0, tol=0.05):
    """First opening angle (2 deg steps) at which lid and tray overlap by more than tol mm3, with the hinge axis moved
    by axis_shift along y; None if they stay clear to 180 deg."""
    global HINGE_AXIS_Y
    saved = HINGE_AXIS_Y
    try:
        HINGE_AXIS_Y = saved + axis_shift
        return next((d for d in range(0, 181, 2) if (open_lid(lidset, d) ^ traset).volume() > tol), None)
    finally:
        HINGE_AXIS_Y = saved


def table_angle(verts, step=0.1):
    """First opening angle (deg) at which a lid-side vertex goes below the table (z = -FOOT_H: on the TPU feet), or None."""
    y, z = np.asarray(verts)[:, 1] - HINGE_AXIS_Y, np.asarray(verts)[:, 2] - Z_PART
    for i in range(int(round(180.0 / step)) + 1):
        a = np.radians(-i * step)
        if (Z_PART + y * np.sin(a) + z * np.cos(a)).min() < -FOOT_H:
            return round(i * step, 1)
    return None


def open_lid(part, deg):
    """Rotate a lid-side part about the real hinge axis (HINGE_AXIS_Y, Z_PART); positive = opening."""
    return part.translate([0, -HINGE_AXIS_Y, -Z_PART]).rotate([-deg, 0, 0]).translate([0, HINGE_AXIS_Y, Z_PART])


def kb_port_bay():
    """Recess in the back face around the keyboard charge port, back to the original 3 mm wall (lid and tray)."""
    if not KB_PORT_BAY or BACK_STYLE == "housings":
        return []
    x0, x1 = KB_PORT_BAY_X
    z0, z1 = KB_PORT_BAY_Z
    return [prism_y(rrect((x0 + x1) / 2, (z0 + z1) / 2, x1 - x0, z1 - z0, KB_PORT_BAY_R), BACK_OLD_Y, Y_BACK + 1.0)]


def kb_plug_envelope():
    p = KB_PLUG
    return box(p["x"] - p["w"] / 2, p["x"] + p["w"] / 2, p["y0"], p["y0"] + p["len"], p["z"] - p["h"] / 2, p["z"] + p["h"] / 2)


def usb_pm_opening_w(spacing):
    if spacing <= 0:
        return USB_PM_W
    return min(USB_PM_W, spacing - USB_PM_SCREW_D - 2 * USB_PM_WEB)


def usb_pm_cuts(spacing):
    """Opening + two ear-screw holes for a panel-mount USB-C on the left end wall (spacing 0 = opening only)."""
    w = usb_pm_opening_w(spacing)
    cuts = [prism_x(rrect(USB_PM_Y, USB_PM_Z, w, USB_PM_H, USB_PM_R), -102, -96.5)]
    if spacing > 0:
        for dy in (-spacing / 2, spacing / 2):
            cuts.append(cyl_x(USB_PM_SCREW_D / 2, -102, -96.5, USB_PM_Y + dy, USB_PM_Z))
    # square the inner wall/ceiling fillet where the ears sit, so ears up to the full 9 mm cavity height seat flat
    half = (spacing / 2 if spacing > 0 else USB_PM_BODY["w"] / 2) + USB_PM_EAR["beyond_hole"] + 0.5
    cuts.append(box(-98.0, -94.0, USB_PM_Y - half, USB_PM_Y + half, USB_PM_Z, LID_CEILING_Z))
    return cuts


def usb_pm_envelope(spacing):
    """Screw-ear female USB-C end seated against the inside of the left wall (rough, for the fit check)."""
    e, b = USB_PM_EAR, USB_PM_BODY
    half = (spacing / 2 + e["beyond_hole"]) if spacing > 0 else b["w"] / 2
    ears = box(-98.0, -98.0 + e["t"], USB_PM_Y - half, USB_PM_Y + half, USB_PM_Z - e["h"] / 2, USB_PM_Z + e["h"] / 2)
    body = box(-98.0 + e["t"], -98.0 + e["t"] + b["len"], USB_PM_Y - b["w"] / 2, USB_PM_Y + b["w"] / 2,
               USB_PM_Z - b["h"] / 2, USB_PM_Z + b["h"] / 2)
    return ears + body


def usb_variant_name(spacing):
    return "lid_A_left_usb_noscrew" if spacing <= 0 else f"lid_A_left_usb{spacing:g}mm"


def build_lid(with_pads, usb_spacing=None):
    tl = load("Display.stl")
    L = to_m(tl)
    # restore the front wall + ceiling edge where the Palma side-button slot was (profile copied from x=-3)
    xa, xb = LID_FRONT_SLOT_X[0] - 2.0, LID_FRONT_SLOT_X[1] + 2.0   # slot edges carry ~1 mm fillets
    prof = section_cs(tl, "x", -3.0, (-47.5, -38.0, 17.5, 31.0))
    L = (L - box(xa, xb, -47.5, -38.0, 17.5, 31.0)) + prism_x(prof, xa, xb)   # clear region, then rebuild it
    # restore the right end wall where the Palma USB opening was (profile copied from y=+10)
    ya, yb = LID_RIGHT_OPEN_Y[0] - 2.0, LID_RIGHT_OPEN_Y[1] + 2.0
    prof = section_cs(tl, "y", 10.0, (95.0, 102.0, 17.5, 31.0))
    L = (L - box(95.0, 102.0, ya, yb, 17.5, 31.0)) + prism_y(prof, ya, yb)
    if LID_FILL_CAMERA:      # the Palma camera window has no use here and would show the PaperDIY board
        x0, x1, y0, y1 = CAMERA_FILL
        L = L + box(x0, x1, y0, y1, LID_CEILING_Z, LID_CEILING_Z + 3.0)
    if FASTENING == "tapping":   # panel screws: refill the insert holes, leave a pilot for M2x8 (3 mm panel + 5 mm)
        for (x, y) in LID_CORNER_HOLES:
            L = L + cyl_z(1.75, PANEL_Z_BACK, LID_CEILING_Z + 0.05, x, y)
    # hinge rework: remove the knuckle, rebuild + thicken the back wall, screw bosses for the hinge leaves
    L = rebuild_back(L, LID_BACK_PROFILE, -1.0, 31.0)
    L = slim_back(L, warp_back(L))
    if lid_ribs():
        L = L + union(lid_ribs())
    if lid_hinge_bosses():
        L = L + union(lid_hinge_bosses())
    if with_pads:
        p = LID_PAD
        for sy in (-1, 1):
            yw = sy * LID_INNER_Y
            y0, y1 = sorted([yw + sy * 0.1, yw - sy * p["depth"]])
            L = L + box(SPLIT_X_LID - p["half_len"], SPLIT_X_LID + p["half_len"], y0, y1, p["z0"], LID_CEILING_Z + 0.05)
    cuts = []
    # panel-mount USB-C on the left end wall
    cuts += usb_pm_cuts(USB_PM_SCREW_SPACING if usb_spacing is None else usb_spacing)
    # keyboard charge-port bay (upper part, in the lid's back wall)
    cuts += kb_port_bay()
    # push-rod bores
    cuts.append(cyl_x(ROD_HOLE / 2, -102, -96.5, PWR_Y, PWR_Z))
    for x in KEY_X:
        cuts.append(cyl_y(ROD_HOLE / 2, -47.5, -42.0, x, KEY_Z))
    # ceiling relief over the battery
    if BATT_RELIEF > 0:
        cuts.append(prism_z(rrect((BI_X0 + BI_X1) / 2, (BI_Y0 + BI_Y1) / 2, BI_X1 - BI_X0, BI_Y1 - BI_Y0, 1.0),
                            LID_CEILING_Z - 0.1, LID_CEILING_Z + BATT_RELIEF))
    cuts += hinge_pocket_cuts() + hinge_pilots(True)
    if FASTENING == "tapping":
        for (x, y) in LID_CORNER_HOLES:
            cuts.append(cyl_z(SCREW_PILOT_D / 2, PANEL_Z_BACK - 0.1, PANEL_Z_BACK + TAP_SCREW_LEN - 3.0 + 0.5, x, y))
    if with_pads:
        p, X = LID_PAD, SPLIT_X_LID
        for sy in (-1, 1):
            yw = sy * LID_INNER_Y
            yd, yi = yw - sy * p["dowel_off"], yw - sy * p["ins_off"]
            cuts.append(cyl_x(DOWEL_D / 2, X - p["half_len"] - 1, X + p["half_len"] + 1, yd, p["dowel_z"]))
            cuts.append(cyl_x(INSERT_M2_D / 2, X - p["ins_depth"], X + 0.01, yi, p["ins_z"]))          # insert in piece A
            cuts.append(cyl_x(M2_CLEAR / 2, X - 0.01, X + p["half_len"] + 1, yi, p["ins_z"]))          # clearance in B
            cuts.append(cyl_x(p["cb_d"] / 2, X + p["half_len"] - p["cb_depth"], X + p["half_len"] + 1, yi, p["ins_z"]))
    if MAGNET_HOLES:
        cuts += magnet_holes("lid")
    return L - union(cuts)


# ------------------------------------------------------------------ TRAY
def build_tray():
    T = to_m(load("Keyboard.stl"))
    # hinge rework: remove ears + trough, rebuild + thicken the back wall
    T = rebuild_back(T, TRAY_BACK_PROFILE, -1.0, 20.0)
    T = slim_back(warp_back(T, lower_rim=0.08, extra=0.0), warp_back(T, lower_rim=0.08))
    # square the bottom-back chamfer under each tray leaf so the whole leaf sits in a pocket (kit: under the whole flush
    # cover + a COVER_RIM frame each side, so the cover, which runs out through the bottom, is flush down to the table)
    sq = (cover_half_w() + COVER_POCKET_CLR + COVER_RIM) if COVER_FLUSH else (HINGE_LEN / 2 + HINGE_CLR)
    for c in (hinge_centres() if HINGE_MOUNT == "face" else ()):
        T = T + box(c - sq, c + sq, LID_INNER_Y + 0.5, Y_BACK, 0.0, 3.2)
    T = T - union(hinge_pocket_cuts() + hinge_pilots(False) + kb_port_bay() + (magnet_holes("tray") if MAGNET_HOLES else [])
                  + ([latch_tray_cut()] if PD_MOUNT == "kit" else []))
    if kb_pads():
        T = T + union(kb_pads())
    if not KB_CUTS_ENABLED:
        return T
    sx = -1 if KB_PORT_WALL == "left" else 1
    xa, xb = sorted([sx * 102.0, sx * 96.5])
    T = T - prism_x(rrect(KB_PORT_Y, KB_PORT_Z, KB_PORT_W, KB_PORT_H, 1.0), xa, xb)
    T = T - prism_x(rrect(KB_SW_Y, KB_SW_BOTTOM_Z + 10, KB_SW_W, 20, 1.0), xa, xb)
    return T


def splice_parts(kind, X):
    """Splice plates for a split piece: [(name, plate, pocket)] in the assembly position. kind: tray (top of the floor),
    lid (inside the ceiling) or panel (on its back). The pockets are cut from both halves after splitting."""
    g = SPLICE[kind]
    t, c = g["t"], SPLICE["clr"]
    out = []
    for i, (y0, y1) in enumerate(g["y"]):
        xa, xb = X + g["x0"], X + g["x1"]
        name = f"{kind}_splice_{i + 1}"
        if kind == "tray":      # on top of the floor, under the keyboard
            pocket = box(xa - c, xb + c, y0 - c, y1 + c, TRAY_FLOOR - t, TRAY_FLOOR + 0.01)
            plate = box(xa, xb, y0, y1, TRAY_FLOOR - t, TRAY_FLOOR)
        elif kind == "panel":
            pocket = box(xa - c, xb + c, y0 - c, y1 + c, PANEL_Z1 - t, PANEL_Z1 + 1.0)
            plate = box(xa, xb, y0, y1, PANEL_Z1 - t, PANEL_Z1)
        else:   # lid: between the ceiling's inner face and t into the ceiling (planes parallel to the sloping top)
            a, b = LID_TOP[:2]
            inner = a - SHELL_CEIL
            pocket = box(xa - c, xb + c, y0 - c, y1 + c, -BIG, BIG) ^ half_space(inner - 1.0, b) ^ half_space(inner + t, b, False)
            plate = box(xa, xb, y0, y1, -BIG, BIG) ^ half_space(inner, b) ^ half_space(inner + t, b, False)
        out.append((name, plate, pocket))
    return out


def build_kit_tray():
    """Kit design: the keyboard tray as a thin shell (WALL walls and floor) with the original outline and parting, a deck
    round the keyboard with the original tray's room as its opening (nothing stands into it), hinge pads and bosses, the
    charge-port opening and the snap-tab recess on a local pad."""
    bottom = LID_UNDER
    plan = CS.batch_boolean(lid_plan_pieces(), m3.OpType.Add)
    outer = prism_z(plan, 0.0, 60.0) ^ half_space(bottom[0], bottom[1], False) ^ box(-BIG, BIG, -BIG, BIG, -BIG, Z_PART)
    T = outer - prism_z(plan.offset(-WALL, m3.JoinType.Round, 2.0, SEG), TRAY_FLOOR, 60.0)
    yi0, yi1 = -BACK_OLD_Y + WALL, Y_BACK - WALL                                          # inner faces
    adds = hinge_mounts(False)
    p = TRAY_PORT
    d = TRAY_DECK
    if d:                                    # the deck: flush with the rim around the keyboard
        cav = plan.offset(-WALL, m3.JoinType.Round, 2.0, SEG)
        # the opening runs on past the back strip's face (y = KB_FACE_Y), which the solid strip makes: square corners
        opening = rrect(0.0, d["r"] / 2, 2 * KB_FACE_X, 2 * KB_FACE_Y + d["r"], d["r"])
        port = box(p["x"][0], p["x"][1], 0.0, BIG, -BIG, BIG)

        def below(off):                      # under the parting surface lowered by off
            return half_space(bottom[0] - off, bottom[1], False) ^ box(-BIG, BIG, -BIG, BIG, -BIG, Z_PART - off)
        inside = plan.offset(-WALL / 2, m3.JoinType.Round, 2.0, SEG)        # into the walls; cut to the rim below
        ring = prism_z(inside - opening, 0.0, 60.0) ^ below(-1.0)
        deck = ring - below(d["t"])
        # a 45 deg fillet under it along the front and end walls, so it prints without supports; it starts 0.05 mm
        # short of the deck's edge (no shared edge)
        ye, xe, zb = KB_FACE_Y - 0.05, KB_FACE_X - 0.05, bottom[0] - d["t"]
        r2 = np.sqrt(2.0)
        fil = [ring.trim_by_plane((0.0, -1.0 / r2, 1.0 / r2), (zb - bottom[1] * ye + ye) / r2)]          # front wall
        for sx in (-1.0, 1.0):                                                                           # end walls
            n = np.array([sx, -bottom[1], 1.0])
            fil.append(ring.trim_by_plane(tuple(n / np.linalg.norm(n)), (zb + xe) / np.linalg.norm(n)))
        back = box(-BIG, BIG, KB_FACE_Y, BIG, -BIG, BIG)              # behind the keyboard: solid from the floor up
        deck = deck + union(fil) + (prism_z(inside, 0.0, 60.0) ^ below(-1.0) ^ back)         # overlapping, not touching
        T = outer - (prism_z(cav, TRAY_FLOOR, 60.0) - (deck - port))  # left out of the cavity: its top is the rim's own face
    l = LATCH                                # pad behind the snap-tab recess, out to the original inner face
    adds.append(box(l["x"] - l["w"] / 2 - 0.3 - WALL, l["x"] + l["w"] / 2 + 0.3 + WALL, yi0 - 0.1, -LID_INNER_Y, 0.0,
                    under_z(-BACK_OLD_Y)))
    T = T + (union(adds) ^ outer)
    cuts = hinge_pocket_cuts() + hinge_pilots(False) + [latch_tray_cut(), back_edge_relief(False)]
    cuts.append(box(p["x"][0], p["x"][1], yi1 - 1.0, Y_BACK + 1.0, TRAY_FLOOR + p["above_floor"], 60.0))
    cuts += [foot_pocket(o) for o in foot_outlines()]
    return T - union(cuts)


# ------------------------------------------------------------------ TPU feet (kit)
def foot_outlines():
    """Plan outlines of the TPU feet's pockets: rounded rectangles in the tray's bottom corners, concentric with the
    corner radius and TPU_FEET["inset"] from the outer edges."""
    f = TPU_FEET
    if not f:
        return []
    x_out, r = 101.0 - f["inset"], CORNER_R - f["inset"]
    out = []
    for sx in (-1.0, 1.0):
        for y_edge, sy in ((Y_BACK - f["inset"], -1.0), (-BACK_OLD_Y + f["inset"], 1.0)):
            out.append(rrect(sx * (x_out - f["w"] / 2), y_edge + sy * f["d"] / 2, f["w"], f["d"], r))
    return out


def foot_pocket(outline):
    f = TPU_FEET
    c = f["chamfer"] - 0.1                    # mouth chamfer (the pocket's first layers spread less than the pad's)
    return prism_z(outline, -1.0, f["pocket"]) + M.batch_hull([
        prism_z(outline.offset(c, m3.JoinType.Round, 2.0, SEG), -1.0, 0.0), prism_z(outline, c - 0.01, c)])


def tpu_foot(outline):
    """The pad, in place (its top in the pocket's floor, its bottom FOOT_H under the tray); chamfered on the table side."""
    f = TPU_FEET
    o = outline.offset(f["fit"], m3.JoinType.Round, 2.0, SEG)
    z0, z1, c = -FOOT_H, f["pocket"], f["chamfer"]
    return prism_z(o, z0 + c, z1) + M.batch_hull([prism_z(o.offset(-c, m3.JoinType.Round, 2.0, SEG), z0, z0 + 0.01),
                                                  prism_z(o, z0 + c - 0.01, z0 + c)])


# ------------------------------------------------------------------ KIT LID (PaperDIY Complete Kit in its own case)
def half_space(a, b, above=True):
    """z >= a + b * y (above) or z <= a + b * y."""
    hs = box(-BIG, BIG, -BIG, BIG, 0.0, BIG) if above else box(-BIG, BIG, -BIG, BIG, -BIG, 0.0)
    return hs.rotate([float(np.degrees(np.arctan(b))), 0.0, 0.0]).translate([0.0, 0.0, a])


def under_z(y):
    """The lid's underside (parting) at y."""
    return LID_UNDER[0] + LID_UNDER[1] * y


def kit_x(d):
    """Lid x of a point d mm from the kit's centre toward its USB end."""
    return KIT_CX - d


KIT_X0, KIT_X1 = KIT_CX - KIT_L / 2 - KIT_FIT, KIT_CX + KIT_L / 2 + KIT_FIT      # pocket (USB end at x0)
KIT_Y0, KIT_Y1 = -(KIT_W / 2 + KIT_FIT), KIT_W / 2 + KIT_FIT                      # KEY edge at y0
SHELL = KIT_LID == "shell"
PANEL_Z0 = max(KB_TOP_Z + KB_CLR, Z_PART + 0.3)          # bezel panel's visible face (shell lid)
PANEL_Z1 = PANEL_Z0 + PANEL_T
KIT_Z0 = PANEL_Z1 if SHELL else max(KB_TOP_Z + KB_CLR, under_z(KIT_Y1) + 0.3)   # the kit's front face
KIT_Z1 = KIT_Z0 + KIT_T + KIT_GAP                          # pocket floor / ceiling inside over the kit
SKIN = SHELL_CEIL if SHELL else LID_SKIN


def kit_lid_top():
    """Top plane z = a + b * y, as low as possible: it passes through what the hinge needs at the back face (leaf +
    cover rim + chamfer) and through the most demanding of the kit pocket and the USB-C channel."""
    z_back = Z_PART + HINGE_WIDTH / 2 + HINGE_CLR + COVER_TOP_RIM + LID_CHAMFER
    ch = KIT_Z0 + USB_CH["h"] + (USB_CEIL if SHELL else SKIN)
    need = [(KIT_Y0, KIT_Z1 + SKIN, "kit pocket (front edge)"), (KIT_Y1, KIT_Z1 + SKIN, "kit pocket (back edge)"),
            (KIT_USB_Y - USB_CH["w"] / 2, ch, "USB-C channel"), (KIT_USB_Y + USB_CH["w"] / 2, ch, "USB-C channel")]
    b, why = min(((z_back - z) / (Y_BACK - y), w) for y, z, w in need)
    return z_back - b * Y_BACK, b, why


LID_TOP = kit_lid_top()


def top_z(y):
    return LID_TOP[0] + LID_TOP[1] * y


def lid_plan_pieces():
    """Plan outline of the case as convex pieces: the body (r = 6 corners) and, behind each hinge, a housing block
    with a tapered rib each side (the same plan as the tray's back)."""
    r = CORNER_R
    if BACK_STYLE != "housings":          # whole back face at the hinge plane (y = Y_BACK)
        return [rrect(0.0, (Y_BACK - BACK_OLD_Y) / 2, 202.0, BACK_OLD_Y + Y_BACK, r)]
    pieces = [rrect(0.0, 0.0, 202.0, 2 * BACK_OLD_Y, r)]
    if BACK_STYLE == "housings":
        g, y0 = HOUSING_GUSSET, LID_INNER_Y + 0.5
        for c in hinge_centres():
            x0, x1 = c - HOUSING_HALF, c + HOUSING_HALF
            pieces.append(poly_cs([(x0, y0), (x1, y0), (x1, Y_BACK), (x0, Y_BACK)]))
            for xe, s in ((x0, -1.0), (x1, 1.0)):
                pieces.append(poly_cs([(xe, y0), (xe, Y_BACK), (xe + s * g, BACK_OLD_Y), (xe + s * g, y0)]))
    return pieces


def chamfered_slab(cs, bottom, top, c):
    """Prism of a convex outline between two planes (a, b), top and bottom edges chamfered by c (hull of 3 prisms)."""
    p = prism_z(cs, -10.0, 60.0)
    pi = prism_z(cs.offset(-c, m3.JoinType.Round, 2.0, SEG), -10.0, 60.0)
    (ab, bb), (at, bt) = bottom, top
    mid = p ^ half_space(ab + c, bb) ^ half_space(at - c, bt, False)
    up = pi ^ half_space(ab + c, bb) ^ half_space(at, bt, False)
    lo = pi ^ half_space(ab, bb) ^ half_space(at - c, bt, False)
    return M.batch_hull([mid, up, lo])


def latch_bump_cs(grow=0.0):
    """Bump on the inside of the tab, in (y, z) at the closed position; grow > 0 gives the tray's groove."""
    l = LATCH
    y0 = -BACK_OLD_Y + l["t"]
    zb = under_z(-BACK_OLD_Y) - l["bump_at"]
    h = l["bump"]
    dc, do = h / np.tan(np.radians(l["close_deg"])), h / np.tan(np.radians(l["open_deg"]))
    cs = poly_cs([(y0 - 0.3, zb - 0.1 - dc), (y0 + h, zb - 0.1), (y0 + h, zb + 0.1), (y0 - 0.3, zb + 0.1 + do)])
    return cs.offset(grow, m3.JoinType.Miter) if grow else cs


def latch_lid_parts():
    """(cut, lip): the cut thins the lid's front wall from inside over the flex zone (45 deg chamfers at its ends and
    top), so that zone bends as a plate; the lip (with the bump) carries on below the parting into the tray's recess.
    Nothing is slit."""
    l, g = LATCH, LATCH["flex"]
    zf, yo = under_z(-BACK_OLD_Y), -BACK_OLD_Y
    x0, x1 = l["x"] - l["w"] / 2, l["x"] + l["w"] / 2
    ch, e = SHELL_WALL - g["t"], 0.3                 # chamfer run; carried e past the inner face (no coplanar faces)
    zr = top_z(yo + SHELL_WALL) - SHELL_CEIL - g["top"]
    floor = box(g["x0"], g["x1"], yo + g["t"], yo + g["t"] + 0.01, zf - 1.0, zr)
    mouth = box(g["x0"] - ch - e, g["x1"] + ch + e, yo + SHELL_WALL + e, yo + SHELL_WALL + e + 0.01, zf - 1.0, zr + ch + e)
    cut = M.batch_hull([floor, mouth])
    lip = box(x0, x1, yo, yo + l["t"], zf - l["below"], zf + 0.5)
    lip = lip - prism_x(poly_cs([(yo + l["t"] - 0.5, zf - l["below"] - 0.01), (yo + l["t"] + 0.01, zf - l["below"] - 0.01),
                                 (yo + l["t"] + 0.01, zf - l["below"] + 0.5)]), x0 - 1, x1 + 1)     # lead-in at the tip
    lip = lip + prism_x(latch_bump_cs(), x0, x1)
    return cut, lip


def latch_plate():
    """The flex zone as a plate (src/latch_plate.py): (stiffness N/mm at the bump, strain per N, where it peaks)."""
    from latch_plate import wall_plate
    l, g = LATCH, LATCH["flex"]
    yo = -BACK_OLD_Y
    return wall_plate(under_z(yo), top_z(yo + SHELL_WALL) - SHELL_CEIL, 202.0 / 2 - SHELL_WALL, SHELL_WALL, (g["x0"], g["x1"], g["t"], g["top"]), (l["x"] - l["w"] / 2, l["x"] + l["w"] / 2),
                      l["bump_at"])


def kb_pads():
    """Pads on the tray's inner walls that take up the keyboard's play (KB_SIZE measured), lead-in at the top."""
    if not KB_SIZE:
        return []
    g = KB_PAD
    px = LID_INNER_X - KB_SIZE[0] / 2 - g["clr"]           # stand-off from the end walls
    py = LID_INNER_Y - KB_SIZE[1] / 2 - g["clr"]           # from the front / back walls
    out = []
    for sy, xs in ((-1.0, g["front_x"]), (1.0, g["back_x"])):
        if py <= 0.05:
            break
        w = sy * LID_INNER_Y
        zt = under_z(w) - g["top_below_rim"]
        prof = poly_cs([(w + sy * 0.1, g["z0"] - 0.1), (w - sy * py, g["z0"] - 0.1), (w - sy * py, zt - g["lead"]),
                        (w + sy * 0.1, zt)])                # (y, z), extruded along x
        out += [prism_x(prof, x - g["w"] / 2, x + g["w"] / 2) for x in xs]
    for sx in (-1.0, 1.0):
        if px <= 0.05:
            break
        w = sx * LID_INNER_X
        for y in g["end_y"]:
            zt = under_z(y) - g["top_below_rim"]
            prof = poly_cs([(w + sx * 0.1, g["z0"] - 0.1), (w - sx * px, g["z0"] - 0.1), (w - sx * px, zt - g["lead"]),
                            (w + sx * 0.1, zt)])            # (x, z), extruded along y
            out.append(prism_y(prof, y - g["w"] / 2, y + g["w"] / 2))
    return out


def latch_tray_cut():
    """Recess in the tray's front face for the tab, with the groove the bump drops into."""
    l = LATCH
    zf, yo = under_z(-BACK_OLD_Y), -BACK_OLD_Y
    x0, x1 = l["x"] - l["w"] / 2 - 0.3, l["x"] + l["w"] / 2 + 0.3
    recess = box(x0, x1, yo - 1.0, yo + l["t"] + l["clr"], zf - l["below"] - 0.4, zf + 2.0)
    return recess + prism_x(latch_bump_cs(0.05), x0, x1)


def shell_inner():
    """The shell lid's inside outline: the plan offset inward by the wall."""
    return CS.batch_boolean(lid_plan_pieces(), m3.OpType.Add).offset(-SHELL_WALL, m3.JoinType.Round, 2.0, SEG)


def usb_pm_low_y():
    """Lowest y the widest ears reach (the ceiling slopes down toward the front)."""
    return USB_PM_Y_KIT - (max(USB_PM_VARIANTS) / 2 + USB_PM_EAR["beyond_hole"])


def usb_pm_zc():
    """Centre height for a panel-mount female at the left end: halfway between the panel's back and the ceiling."""
    return (PANEL_Z1 + top_z(usb_pm_low_y()) - SHELL_CEIL) / 2


def usb_end_cuts(usb):
    """Left end wall of the shell lid. "direct": an opening for a straight plug in line with the kit's port.
    A number: opening (+ M3 holes that far apart, 0 = none) for a screw-ear panel-mount female at y = USB_PM_Y_KIT."""
    xo = -101.0
    if usb == "direct":
        w = USB_CH["w"]
        return [box(xo - 1.0, xo + SHELL_WALL + 0.5, KIT_USB_Y - w / 2, KIT_USB_Y + w / 2, KIT_Z0 - 0.01, KIT_Z0 + USB_CH["h"])]
    zc = usb_pm_zc()
    cuts = [prism_x(rrect(USB_PM_Y_KIT, zc, usb_pm_opening_w(usb), USB_PM_H, USB_PM_R), xo - 1.0, xo + SHELL_WALL + 0.5)]
    if usb > 0:
        for dy in (-usb / 2, usb / 2):
            cuts.append(cyl_x(USB_PM_SCREW_D / 2, xo - 1.0, xo + SHELL_WALL + 0.5, USB_PM_Y_KIT + dy, zc))
    return cuts


def usb_pm_envelope_kit(spacing):
    """Screw-ear female USB-C against the inside of the left end wall (rough, for the fit check)."""
    e, b = USB_PM_EAR, USB_PM_BODY
    zc, x0 = usb_pm_zc(), -101.0 + SHELL_WALL
    half = (spacing / 2 + e["beyond_hole"]) if spacing > 0 else b["w"] / 2
    h = min(e["h"], usb_pm_room() - 0.2)
    ears = box(x0, x0 + e["t"], USB_PM_Y_KIT - half, USB_PM_Y_KIT + half, zc - h / 2, zc + h / 2)
    body = box(x0 + e["t"], x0 + e["t"] + b["len"], USB_PM_Y_KIT - b["w"] / 2, USB_PM_Y_KIT + b["w"] / 2, zc - b["h"] / 2, zc + b["h"] / 2)
    return ears + body


def usb_pm_room():
    return top_z(usb_pm_low_y()) - SHELL_CEIL - PANEL_Z1


def hinge_pad_extent():
    """(half width, front y) of the pad behind each hinge in the thin kit shells: the cover pocket + WALL wide, the
    mortise + WALL deep."""
    return cover_half_w() + COVER_POCKET_CLR + WALL, Y_BACK - (HINGE_SINK + HINGE_LEAF_T + 0.05 + WALL)


def back_edge_relief(lid):
    """Material to remove so the back edge along the parting (lid: lower, tray: upper) is rounded with HINGE_EDGE_R."""
    r = HINGE_EDGE_R
    if r <= 0:
        return M()
    s = 1.0 if lid else -1.0
    zc = Z_PART + s * r
    corner = box(-BIG, BIG, Y_BACK - r, Y_BACK + 1.0, min(Z_PART - 1.0 * s, zc), max(Z_PART - 1.0 * s, zc))
    return corner - cyl_x(r, -BIG, BIG, Y_BACK - r, zc)


def hinge_mounts(lid):
    """Thin kit shells: behind each hinge a pad and a screw boss per pilot hole, out to the screw tip + skin, with a rib
    from the boss to the ceiling (lid) or the floor (tray). Clip to the part's outer shape."""
    hw, y_pad = hinge_pad_extent()
    g = HINGE_PAD
    rb = HINGE_PILOT_D / 2 + g["boss_wall"]
    y_tip = Y_BACK - HINGE_SCREW_LEN - g["skin"]
    out = []
    for c in hinge_centres():
        out.append(box(c - hw, c + hw, y_pad, Y_BACK, Z_PART - 0.01, 60.0) if lid else
                   box(c - hw, c + hw, y_pad, Y_BACK, -10.0, Z_PART + 0.01))
        zc = Z_PART + (HINGE_HOLE_OFF if lid else -HINGE_HOLE_OFF)
        for dx in (-HINGE_HOLE_PITCH_X / 2, HINGE_HOLE_PITCH_X / 2):
            x = c + dx
            out.append(cyl_y(rb, y_tip, y_pad + 0.1, x, zc))
            out.append(box(x - RIB_T / 2, x + RIB_T / 2, y_tip, y_pad + 0.1, zc, 60.0) if lid else
                       box(x - RIB_T / 2, x + RIB_T / 2, y_tip, y_pad + 0.1, -10.0, zc))
    return out


PANEL_RIB_INFO = []          # filled by build_kit_lid_shell, for the log


def panel_boss_keepout():
    """Plan boxes the boss ribs stay out of: the kit with the panel's rim round it, the lid's splice-plate pockets
    (they go in from below, flush with the ceiling) and the USB-C plug path."""
    w, c = PANEL_RIM["w"] + 0.5, SPLICE["clr"] + 0.5
    g = SPLICE["lid"]
    out = [(KIT_X0 - w, KIT_X1 + w, KIT_Y0 - w, KIT_Y1 + w)]
    out += [(SPLIT_X_LID + g["x0"] - c, SPLIT_X_LID + g["x1"] + c, ya - c, yb + c) for ya, yb in g["y"]]
    out.append((-BIG, KIT_X0, KIT_USB_Y - USB_CH["w"] / 2 - 0.5, KIT_USB_Y + USB_CH["w"] / 2 + 0.5))
    return out


def panel_boss_ribs(L):
    """[(rib, (x, y, direction, kind, length))] for the panel's screw bosses in lid L (shell, bosses, hinge mounts):
    toward material closer than `tie` a full-height rib into it, else a gusset; shortened at the keep-out boxes."""
    g = PANEL_BOSS_RIBS
    rb, h, z0 = PANEL_BOSS_R, g["t"] / 2, PANEL_Z1 + g["gap"]
    keep = panel_boss_keepout()
    out = []
    for x, y in PANEL_SCREWS:
        zm = (z0 + top_z(y) - SHELL_CEIL) / 2
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            # gap to the nearest material along the ray, at mid-height
            r0, r1 = rb + 0.2, rb + g["tie"] + 0.2
            ray = box(*sorted((x + dx * r0, x + dx * r1)) if dx else (x - 0.3, x + 0.3),
                      *sorted((y + dy * r0, y + dy * r1)) if dy else (y - 0.3, y + 0.3), zm - 0.3, zm + 0.3) ^ L
            gap = None
            if not ray.is_empty():
                bb = ray.bounding_box()
                gap = (bb[0] - x if dx > 0 else x - bb[3]) if dx else (bb[1] - y if dy > 0 else y - bb[4])
                gap -= rb
            reach = (gap + 0.6) if gap is not None else g["len"]          # past the boss's surface
            for kx0, kx1, ky0, ky1 in keep:                               # stop at a keep-out box
                if dx and ky0 < y + h and y - h < ky1:
                    d = (kx0 - x if dx > 0 else x - kx1) - rb
                elif dy and kx0 < x + h and x - h < kx1:
                    d = (ky0 - y if dy > 0 else y - ky1) - rb
                else:
                    continue
                if d >= 0:
                    reach = min(reach, d)
            if reach < g["min_len"]:
                continue
            tie = gap is not None and reach >= gap + 0.5
            zc = top_z(y + dy * (rb + reach)) - SHELL_CEIL
            if tie:          # full height into the wall / pad
                prof = [(rb - 0.5, z0), (rb + reach, z0), (rb + reach, 60.0), (rb - 0.5, 60.0)]
            else:            # gusset: edge from the boss's foot to the ceiling, carried 0.4 past it into the ceiling
                u = np.array([rb + reach, zc]) - np.array([rb - 0.5, z0])
                e = np.array([rb + reach, zc]) + 0.4 * u / np.linalg.norm(u)
                prof = [(rb - 0.5, z0), tuple(e), (e[0], 60.0), (rb - 0.5, 60.0)]
            if dx:
                cs = poly_cs([(x + dx * r, z) for r, z in prof])
                rib = prism_y(cs, y - h, y + h)
            else:
                cs = poly_cs([(y + dy * r, z) for r, z in prof])
                rib = prism_x(cs, x - h, x + h)
            out.append((rib, (x, y, (dx, dy), "tie" if tie else "gusset", reach)))
    return out


def build_kit_lid_shell(usb="direct", blocks=True):
    """blocks: the thicker ceiling around the dovetail keys, only needed when the lid is split."""
    bottom, top = LID_UNDER, LID_TOP[:2]
    plan = lid_plan_pieces()
    outer = union(chamfered_slab(cs, bottom, top, LID_CHAMFER) for cs in plan)
    y_flat = (Z_PART - bottom[0]) / bottom[1]
    outer = outer + (prism_z(CS.batch_boolean(plan, m3.OpType.Add), Z_PART, 20.0) ^ box(-BIG, BIG, y_flat, BIG, -BIG, BIG)
                     ^ half_space(bottom[0] + 0.01, bottom[1], False))
    L = outer - (prism_z(shell_inner(), -10.0, 60.0) ^ half_space(top[0] - SHELL_CEIL, top[1], False))
    adds = hinge_mounts(True)                                                                        # hinges
    adds += [cyl_z(PANEL_BOSS_R, PANEL_Z1, 60.0, x, y) for x, y in PANEL_SCREWS]                     # panel bosses
    adds += [box(x - 0.8, x + 0.8, -30.0, 30.0, KIT_Z0 + KIT_T + 0.1, 60.0) for x in KIT_RIBS_X]      # on the kit's back
    gx0 = USB_GUIDE_X[0] if usb == "direct" else SPLIT_X_LID       # guides stay in lid B for a panel-mount lid A
    w = USB_CH["w"] / 2 + 0.6
    for sy in (-1.0, 1.0):
        y0, y1 = sorted((KIT_USB_Y + sy * w, KIT_USB_Y + sy * (w + RIB_T)))
        adds.append(box(gx0, KIT_X0 - PANEL_RIM["w"] - 0.3, y0, y1, PANEL_Z1 + 0.1, 60.0))   # stop short of the rim
    g = SPLIT_BLOCK
    adds += [box(SPLIT_X_LID - g["dx"], SPLIT_X_LID + g["dx"], y - g["dy"], y + g["dy"], -10.0, 60.0)
             ^ half_space(top[0] - g["h"], top[1]) for y in DOVETAIL_Y_KIT] if (blocks and g) else []
    L = L + (union(adds) ^ outer)
    if PANEL_BOSS_RIBS:
        ribs = panel_boss_ribs(L)
        if usb == "direct":
            PANEL_RIB_INFO[:] = [i for _, i in ribs]
        L = L + (union(r for r, _ in ribs) ^ outer)
    cut, tab = latch_lid_parts()
    L = (L - cut) + tab
    cuts = usb_end_cuts(usb) + hinge_pocket_cuts() + hinge_pilots(True) + [back_edge_relief(True)]
    cuts.append(box(-101.0 + SHELL_WALL, KIT_X0 + KIT_FIT + 1.0, KIT_USB_Y - USB_CH["w"] / 2, KIT_USB_Y + USB_CH["w"] / 2,
                    -10.0, 60.0) ^ half_space(top[0] - USB_CEIL, top[1], False))   # thinner ceiling over the plug path
    cuts += [cyl_z(SCREW_PILOT_D / 2, PANEL_Z1 - 0.1, PANEL_Z1 + TAP_SCREW_LEN - PANEL_T + 0.5, x, y) for x, y in PANEL_SCREWS]
    cuts.append(panel_snaps(groove=True))                                    # grooves for the panel's snap bumps
    return L - union(cuts)


def panel_snaps(groove=False):
    """Snap detents on the panel's front and back edges (groove=False: the bumps, to add to the panel) or the grooves
    for them in the lid's walls (groove=True: to cut from the lid), as prisms along x."""
    g = PANEL_SNAP
    if not (SHELL and g):
        return M()
    xb = shell_inner().bounds()                          # (x0, y0, x1, y1) of the lid's inner faces
    h = g["h"] if groove else g["bump"]
    half = g["len"] / 2 + (0.5 if groove else 0.0)
    parts = []
    for side, y_wall, xs in ((-1, xb[1], g["x_front"]), (1, xb[3], g["x_back"])):
        y_e = y_wall - side * PANEL_CLR                  # the panel's edge
        e = 0.05     # the flanks start 0.3 mm inside the panel, so they cross its edge face away from any vertex
        peak = PANEL_T / 2
        uv = [(-0.6, PANEL_Z0 + e), (-0.3, PANEL_Z0 + e), (h, PANEL_Z0 + peak), (-0.3, PANEL_Z1 - e), (-0.6, PANEL_Z1 - e)]
        pts = [(y_e + side * u, v) for u, v in uv]
        if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) < 0:
            pts = pts[::-1]
        cs = CS([pts])
        if groove:
            cs = cs.offset(g["clr"], m3.JoinType.Miter)
        parts += [prism_x(cs, x - half, x + half) for x in xs]
    return union(parts)


def build_kit_panel():
    """Bezel panel: fills the lid's opening, holds the kit from the screen side, window over the e-paper."""
    P = prism_z(shell_inner().offset(-PANEL_CLR, m3.JoinType.Round, 2.0, SEG), PANEL_Z0, PANEL_Z1)
    r = PANEL_RIM
    kit_cs = lambda grow: rrect(KIT_CX, 0.0, KIT_L + 2 * grow, KIT_W + 2 * grow, KIT_R + grow)
    P = P + prism_z(kit_cs(KIT_FIT + r["w"]) - kit_cs(KIT_FIT), PANEL_Z1 - 0.01, PANEL_Z1 + r["h"])
    hw, y_pad = hinge_pad_extent()
    cuts = [box(c - hw - PANEL_CLR, c + hw + PANEL_CLR, y_pad - PANEL_CLR, BIG, -BIG, BIG) for c in hinge_centres()]
    wx = KIT_CX + KIT_WIN_OFF
    ww, wh = KIT_WIN[0] + 2 * PANEL_WIN_CLR, KIT_WIN[1] + 2 * PANEL_WIN_CLR
    cuts.append(prism_z(rrect(wx, 0.0, ww, wh, 0.5), PANEL_Z0 - 1.0, PANEL_Z1 + 1.0))   # square edges (no chamfer)
    g = PANEL_SLOT
    z0, z1 = PANEL_Z0 - 1.0, PANEL_Z1 + r["h"] + 1.0
    xs = [kit_x(d) for cap in KIT_KEY_CAPS for d in cap]
    xa, xb, ya, yb = min(xs) - g["end"], max(xs) + g["end"], -KIT_W / 2 - g["out"], -KIT_W / 2 + 0.5
    cuts.append(prism_z(rrect((xa + xb) / 2, (ya + yb) / 2, xb - xa, yb - ya, g["r"]), z0, z1))
    if PANEL_GUARD:     # guard ring round the KEY slot, from the panel's back up to the kit's back; the kit closes it
        gd = PANEL_GUARD
        slot = lambda grow: rrect((xa + xb) / 2, (ya + yb) / 2, xb - xa + 2 * grow, yb - ya + 2 * grow, g["r"] + grow)
        ring = (slot(gd["clr"] + gd["t"]) - slot(gd["clr"])) - kit_cs(KIT_FIT)
        P = P + (prism_z(ring, PANEL_Z1 - 0.01, KIT_Z0 + KIT_T) ^ prism_z(shell_inner().offset(-PANEL_CLR, m3.JoinType.Round,
                                                                                               2.0, SEG), -BIG, BIG)
                 ^ half_space(LID_TOP[0] - SHELL_CEIL - PANEL_CLR, LID_TOP[1], False))   # and under the ceiling
    xe = KIT_CX - KIT_L / 2
    xa, xb, ya, yb = xe - g["out"], xe + 0.5, KIT_PWR_CAP_Y[0] - g["end"], KIT_PWR_CAP_Y[1] + g["end"]
    cuts.append(prism_z(rrect((xa + xb) / 2, (ya + yb) / 2, xb - xa, yb - ya, g["r"]), z0, z1))
    cuts.append(box(KIT_X0 - r["w"] - 1.0, KIT_X0 + 0.01, KIT_USB_Y - 6.6, KIT_USB_Y + 6.6, PANEL_Z1, z1))  # plug
    if PANEL_USB_SLOT:  # open over the plug path, from a frame at the panel's left edge to the kit's end
        u = PANEL_USB_SLOT
        xa, xb = -101.0 + SHELL_WALL + PANEL_CLR + u["frame"], KIT_X0
        cuts.append(prism_z(rrect((xa + xb) / 2, KIT_USB_Y, xb - xa, 2 * u["half"], u["r"]), z0, z1))
    for x, y in PANEL_SCREWS:
        cuts += [cyl_z(M2_CLEAR / 2, z0, z1, x, y), cyl_z(CSK_D / 2, PANEL_Z0 - 0.01, PANEL_Z0 + 1.2, x, y, M2_CLEAR / 2 - 0.2)]
    return (P + panel_snaps()) - union(cuts)


def build_kit_lid():
    if SHELL:
        return build_kit_lid_shell()
    bottom = LID_UNDER
    top = LID_TOP[:2]
    L = union(chamfered_slab(cs, bottom, top, LID_CHAMFER) for cs in lid_plan_pieces())
    # the back strip of the parting is flat at Z_PART where the plane would rise above it (housings): fill down to it
    y_flat = (Z_PART - bottom[0]) / bottom[1]
    L = L + (prism_z(CS.batch_boolean(lid_plan_pieces(), m3.OpType.Add), Z_PART + 0.0, 20.0) ^ box(-BIG, BIG, y_flat, BIG, -BIG, BIG)
             ^ half_space(bottom[0] + 0.01, bottom[1], False))
    # keyboard space: inside the walls, up to the kit's front face (and never below the parting + 0.3)
    inner = rrect(0.0, 0.0, 2 * LID_INNER_X, 2 * LID_INNER_Y, 3.0)
    L = L - (prism_z(inner, -10.0, KIT_Z0) + (prism_z(inner, -10.0, 60.0) ^ half_space(bottom[0] + 0.3, bottom[1], False)))
    cut, tab = latch_lid_parts()
    L = (L - cut) + tab
    cuts = [prism_z(rrect(KIT_CX, 0.0, KIT_L + 2 * KIT_FIT, KIT_W + 2 * KIT_FIT, KIT_R + KIT_FIT), KIT_Z0 - 1.0, KIT_Z1)]
    n = KIT_NOTCH
    zn = KIT_Z0 + n["depth"]
    xs = [kit_x(d) for cap in KIT_KEY_CAPS for d in cap]                   # KEY caps: one notch over both
    xa, xb = min(xs) - n["end"], max(xs) + n["end"]
    ya, yb = KIT_Y0 - n["out"], KIT_Y0 + 1.0
    cuts.append(prism_z(rrect((xa + xb) / 2, (ya + yb) / 2, xb - xa, yb - ya, n["r"]), KIT_Z0 - 1.0, zn))
    ya, yb = KIT_PWR_CAP_Y[0] - n["end"], KIT_PWR_CAP_Y[1] + n["end"]      # power cap on the USB end
    xa, xb = KIT_X0 - n["out"], KIT_X0 + 1.0
    cuts.append(prism_z(rrect((xa + xb) / 2, (ya + yb) / 2, xb - xa, yb - ya, n["r"]), KIT_Z0 - 1.0, zn))
    w = USB_CH["w"]                                                       # USB-C plug channel through the left end
    cuts.append(box(-BIG, KIT_X0 + 1.0, KIT_USB_Y - w / 2, KIT_USB_Y + w / 2, KIT_Z0 - 1.0, KIT_Z0 + USB_CH["h"]))
    # one M2x4 countersunk screw from the top into the kit's standoff (through the hole in its back plate)
    sx = kit_x(KIT_SCREW_D)
    seat = min(KIT_Z1 + KIT_SCREW_SEAT, top_z(0.0))
    cuts += [cyl_z(M2_CLEAR / 2, KIT_Z1 - 0.5, seat, sx, 0.0), cyl_z(M2_CLEAR / 2 - 0.2, seat - 1.2, seat, sx, 0.0, CSK_D / 2),
             cyl_z(CSK_D / 2 + 0.2, seat, 60.0, sx, 0.0)]
    cuts += hinge_pocket_cuts() + hinge_pilots(True) + kb_port_bay()
    return L - union(cuts)


def kit_envelope():
    """The kit in its case, as placed in the lid (for checks and renders): case, KEY caps, power cap."""
    z0 = KIT_Z0
    parts = [prism_z(rrect(KIT_CX, 0.0, KIT_L, KIT_W, KIT_R), z0, z0 + KIT_T)]
    zc0, zc1 = z0 + KIT_CAP_Z[0], z0 + KIT_CAP_Z[1]
    for a, b in KIT_KEY_CAPS:
        parts.append(box(kit_x(b), kit_x(a), -KIT_W / 2 - KIT_CAP_OUT, -KIT_W / 2 + 0.5, zc0, zc1))
    xe = KIT_CX - KIT_L / 2
    parts.append(box(xe - KIT_PWR_CAP_OUT, xe + 0.5, KIT_PWR_CAP_Y[0], KIT_PWR_CAP_Y[1], zc0, zc1))
    return union(parts)


def kit_plug_envelope(length=24.0):
    """A straight USB-C plug in the kit's port: overmold 12 x 6.5 from the case end outward."""
    zc = KIT_Z0 + sum(KIT_USB_Z) / 2
    xe = KIT_CX - KIT_L / 2
    return box(xe - length, xe, KIT_USB_Y - 6.0, KIT_USB_Y + 6.0, zc - 3.25, zc + 3.25)


def latch_path(lid, tray):
    """Rigid-tab overlap with the tray while the lid opens from closed: the deflection the tab has to take."""
    l = LATCH
    x0, x1 = l["x"] - l["w"] / 2, l["x"] + l["w"] / 2
    zone = box(x0 + 1.0, x1 - 1.0, -BACK_OLD_Y - 1.0, -LID_INNER_Y, under_z(-BACK_OLD_Y) - 6.0, under_z(-BACK_OLD_Y) + 3.0)
    tab = lid ^ zone
    t_near = tray ^ zone.translate([0, 0, 0])
    worst, at = 0.0, 0.0
    for i in range(0, 61):
        deg = i * 0.1
        ov = open_lid(tab, deg) ^ t_near
        if ov.volume() > 1e-4:
            lo, hi = ov.bounding_box()[:3], ov.bounding_box()[3:]
            d = hi[1] - lo[1]
            if d > worst:
                worst, at = d, deg
    return worst, at


# ------------------------------------------------------------------ test coupons
def build_coupons(lid, tray, panel, ta, tb):
    """Small test prints cut from the real parts (same print orientation as the part they come from), to check the
    fits on your printer before the long prints: hinge seat + screws, dovetail key, panel corner screw, push-rod bore.
    Returns {name: (manifold, source part)}."""
    hx = HINGE_X
    hinge_box = box(hx - 13.5, hx + 13.5, 36.0, Y_BACK + 1.0, -1.0, 31.0)
    X = SPLIT_X_TRAY
    dt_box = box(X - 12.0, X + 14.0, -9.0, 9.0, -1.0, 3.5)
    cx, cy = max(LID_CORNER_HOLES)                        # back-right panel screw (92.8, 38.78)
    kx = KEY_X[0]
    return {
        "coupon_hinge_tray": (tray ^ hinge_box, "tray"),
        "coupon_hinge_lid": (lid ^ hinge_box, "lid"),
        "coupon_dovetail_A": (ta ^ dt_box, "tray"),
        "coupon_dovetail_B": (tb ^ dt_box, "tray"),
        "coupon_corner_lid": (lid ^ box(cx - 7.0, 102.0, cy - 7.0, Y_BACK + 1.0, 14.0, 31.0), "lid"),
        "coupon_corner_panel": (panel ^ box(cx - 7.0, 99.0, cy - 7.0, 44.0, 14.0, 19.5), "panel"),
        "coupon_keywall_lid": (lid ^ box(kx - 8.0, kx + 8.0, -48.0, -33.0, 12.0, 31.0), "lid"),
    }


# ------------------------------------------------------------------ verification models
def paperdiy_envelope():
    z = PANEL_Z_BACK
    parts = [box(X_USB, X_TOP, -PD_W / 2, PD_W / 2, z, z + 1.2),                                     # glass/EPD
             box(X_TOP - 108.9, X_TOP - PD_PCB_TOP_FROM_TOP, -PD_W / 2, PD_W / 2, z + 1.4, z + 2.4),          # PCB
             box(X_USB, X_TOP - 108.9, -PD_W / 2 - PD_PCB_OVERHANG, PD_W / 2 + PD_PCB_OVERHANG, z + 1.4, z + 2.4),  # PCB ears (64.2 wide, v>=108.9)
             box(X_TOP - 87.9, X_TOP - 69.9, 31.25 - 24.75, 31.25 - 0.3, z + 2.4, z + 5.45),             # ESP32-S3 module
             cyl_z(PD_M2_STANDOFF_OD / 2, z + 2.4, SO_TOP, SO_X, SO_Y),
             box(X_USB - PD_USB_PROTRUDE, X_USB + 6, USB_Y - PD_USB_W / 2, USB_Y + PD_USB_W / 2, z + PD_USB_DEPTH[0], z + PD_USB_DEPTH[1])]
    for x in KEY_X:
        parts.append(box(x - 0.86, x + 0.86, KEY_TIP_Y, Y_KEYEDGE + 3, KEY_Z - 0.28, KEY_Z + 0.28))
    parts.append(box(PWR_TIP_X, X_USB + 3, PWR_Y - 0.86, PWR_Y + 0.86, PWR_Z - 0.42, PWR_Z + 0.42))
    return union(parts)


def battery_envelope():
    zb = PANEL_Z_BACK - BATT_POCKET
    return box(BATT_CX - BATT_W / 2, BATT_CX + BATT_W / 2, BATT_CY - BATT_L / 2, BATT_CY + BATT_L / 2, zb, zb + BATT_T)


def interference(a, b, name, tol=0.5):
    v = (a ^ b).volume()
    log(f"  interference {name}: {v:.3f} mm3 {'OK' if v <= tol else '<-- CHECK'}")
    return v


# ------------------------------------------------------------------ main
def clean_outputs():
    """Remove generated STLs and renders first, so a part that is no longer built does not linger in out/."""
    for pat in ("out/*.stl", "out/split/*.stl", "out/split/usb_variants/*.stl", "out/split/splice/*.stl", "out/whole/*.stl",
                "out/whole/usb_variants/*.stl", "out/coupons/*.stl", "renders/*.png"):
        for f in glob.glob(os.path.join(CAD_DIR, pat)):
            os.remove(f)


def build_kit_coupons(lid, tray, ta, tb):
    """Test prints for the kit design: hinge seat (lid + tray), dovetail key (if any), and the snap tab with its recess."""
    hx = HINGE_X
    hw = hinge_pad_extent()[0] + 1.0 if SHELL else 13.5
    hinge_box = box(hx - hw, hx + hw, 36.0, Y_BACK + 1.0, -1.0, 40.0)
    X = SPLIT_X_TRAY
    dt_box = box(X - 12.0, X + 14.0, -9.0, 9.0, -1.0, 3.5)
    l = LATCH
    zf = under_z(-BACK_OLD_Y)
    hw = max(l["w"] / 2 + 4.0, 13.0)                      # at least 26 mm wide: stands on the bed without a brim
    lx0, lx1 = l["x"] - hw, l["x"] + hw
    out = {
        "coupon_hinge_tray": (tray ^ hinge_box, "tray"),
        "coupon_hinge_lid": (lid ^ hinge_box, "lid"),
        "coupon_dovetail_A": (ta ^ dt_box, "tray"),
        "coupon_dovetail_B": (tb ^ dt_box, "tray"),
        "coupon_latch_lid": (lid ^ box(lx0, lx1, -BACK_OLD_Y - 1.0, -BACK_OLD_Y + 12.0, zf - 6.0, 60.0), "lid"),
        "coupon_latch_tray": (tray ^ box(lx0, lx1, -BACK_OLD_Y - 1.0, -BACK_OLD_Y + 12.0, -1.0, 20.0), "tray"),
    }
    if SPLIT_JOINT == "straight":            # no keys to try
        del out["coupon_dovetail_A"], out["coupon_dovetail_B"]
    return out


def main_kit():
    os.makedirs(SPLIT_DIR, exist_ok=True); os.makedirs(RENDER_DIR, exist_ok=True)
    clean_outputs()
    a, b, why = LID_TOP
    zf = under_z(-BACK_OLD_Y)
    log("== layout (PD_MOUNT = 'kit': the PaperDIY Complete Kit in its own case, front face down in a pocket in the lid)")
    log(f"  kit pocket x {KIT_X0:.1f}..{KIT_X1:.1f}, y {KIT_Y0:.1f}..{KIT_Y1:.1f}; window centre x = {KIT_CX + KIT_WIN_OFF:.1f}")
    if SHELL:
        log(f"  shell lid (walls {SHELL_WALL}, ceiling {SHELL_CEIL}); bezel panel z {PANEL_Z0:.2f}..{PANEL_Z1:.2f} (keyboard top "
            f"{KB_TOP_Z} + {KB_CLR}; MEASURE the keyboard); kit front z = {KIT_Z0:.2f}, back + gap z = {KIT_Z1:.2f}")
    else:
        log(f"  kit front face = lid inner face z = {KIT_Z0:.2f} (keyboard top {KB_TOP_Z} + {KB_CLR}; MEASURE the keyboard), pocket floor z = {KIT_Z1:.2f}")
    log(f"  lid top plane z = {a:.3f} + {b:.5f} y, set by the hinge at the back and the {why}")
    log(f"  lid {top_z(-BACK_OLD_Y) - zf:.1f} mm thick at the front face, {top_z(BACK_OLD_Y) - Z_PART:.1f} at the back; "
        f"closed case {top_z(-BACK_OLD_Y):.1f} mm tall at the front, {top_z(Y_BACK):.1f} at the back (was 30.0 / 30.0)")
    log("== building")
    lid = build_kit_lid()
    tray = build_kit_tray() if SHELL else build_tray()
    panel = build_kit_panel() if SHELL else None
    kit, plug = kit_envelope(), kit_plug_envelope()
    log("== exports (bounding boxes are axis-aligned in the assembly frame)")
    export(lid, f"{OUT_DIR}/display_lid_usbc.stl")
    export(tray, f"{OUT_DIR}/keyboard_tray.stl")
    export(kit, f"{OUT_DIR}/paperdiy_kit_envelope.stl")
    if SHELL:
        export(panel, f"{OUT_DIR}/display_panel_kit.stl")
    lid_cov, tray_cov = hinge_covers()
    export(lid_cov[0], f"{OUT_DIR}/hinge_cover_lid_x2.stl")
    export(tray_cov[0], f"{OUT_DIR}/hinge_cover_tray_x2.stl")
    feet = [tpu_foot(o) for o in foot_outlines()]
    if feet:
        export(feet[0].translate([0, 0, FOOT_H]), f"{OUT_DIR}/tpu_foot.stl")       # table side down, as printed
    write_assembly_json()
    log("== split pieces for A1 mini (limit %.0f mm)" % MAX_PIECE)
    if not SHELL:
        kz0 = KIT_Z0 + 0.3
    elif SPLIT_BLOCK:
        kz0 = top_z(max(DOVETAIL_Y_KIT) + SPLIT_BLOCK["dy"]) - SPLIT_BLOCK["h"] + 0.3
    else:               # keys through the plain ceiling, from its inner face (which slopes with the top)
        kz0 = lambda y: top_z(y - DOVETAIL["head"] / 2) - SHELL_CEIL - 0.01
    la, lb = split_kit(lid, SPLIT_X_LID, DOVETAIL_Y_KIT, kz0, 60.0)
    ta, tb = split_kit(tray, SPLIT_X_TRAY, DOVETAIL_Y, 0.0, TRAY_FLOOR)
    splices = {"lid": splice_parts("lid", SPLIT_X_LID), "tray": splice_parts("tray", SPLIT_X_TRAY)} if SPLICE else {}
    pocket = lambda kind: union(p for _, _, p in splices[kind]) if kind in splices else M()
    la, lb, ta, tb = la - pocket("lid"), lb - pocket("lid"), ta - pocket("tray"), tb - pocket("tray")
    pieces = {"lid_A_left": la, "lid_B_main": lb, "tray_A_left": ta, "tray_B_main": tb}
    if SHELL:
        pa, pb = split_kit(panel, SPLIT_X_PANEL, PANEL_DOVETAIL_Y, PANEL_Z0, PANEL_Z1, PANEL_DOVETAIL)
        if SPLICE:
            splices["panel"] = splice_parts("panel", SPLIT_X_PANEL)
            pa, pb = pa - pocket("panel"), pb - pocket("panel")
        pieces.update(panel_A_left=pa, panel_B_main=pb)
    for k, v in pieces.items():
        tm = export(v, f"{SPLIT_DIR}/{k}.stl")
        assert max(tm.extents) <= MAX_PIECE, (k, tm.extents)
    if SHELL:   # no part of a panel piece may hang on a web narrower than 2 mm (eroded by 1 mm it must stay in one piece)
        for k in ("panel_A_left", "panel_B_main"):
            n = len(pieces[k].slice(PANEL_Z0 + 0.5).offset(-1.0, m3.JoinType.Miter).decompose())
            log(f"  {k}: eroded by 1 mm (visible half) -> {n} piece(s)")
            assert n == 1, (k, "a web narrower than 2 mm", n)
    if splices:
        log("== splice plates for the split pieces (" + ", ".join(f"{k} {SPLICE[k]['t']:g} mm" for k in ("tray", "lid", "panel"))
            + "; glued from the hidden side into pockets in both halves)")
        for kind, items in splices.items():
            for name, plate, _ in items:
                export(plate, f"{SPLIT_DIR}/splice/{name}.stl")
                for k, v in pieces.items():
                    if k.startswith(kind):
                        interference(plate, v, f"{name} vs {k}", tol=0.01)
    usb_variants = {}
    if SHELL:
        log(f"== lid A for a screw-ear panel-mount female USB-C (swap only lid A; room inside the end wall {usb_pm_room():.1f} mm)")
        for sp in USB_PM_VARIANTS:
            va, vb = split_kit(build_kit_lid_shell(usb=sp), SPLIT_X_LID, DOVETAIL_Y_KIT, kz0, 60.0)
            va, vb = va - pocket("lid"), vb - pocket("lid")
            assert abs(vb.volume() - lb.volume()) < 0.01, ("lid B must not depend on the USB-C end", sp)
            name = usb_variant_name(sp)
            tm = export(va, f"{SPLIT_DIR}/usb_variants/{name}.stl")
            assert max(tm.extents) <= MAX_PIECE
            usb_variants[sp] = va + lb
            log(f"    {name}: opening {usb_pm_opening_w(sp):.1f} x {USB_PM_H:.1f} mm at y = {USB_PM_Y_KIT:g}, z = {usb_pm_zc():.1f}"
                + (f", M3 holes {sp:g} mm apart" if sp > 0 else ", no screw holes (glue)"))
        # Whole parts for printers with a bed of WHOLE_BED or more (or a print service): no split, no dovetail keys, no splice
        # pockets (and no SPLIT_BLOCK ceiling blocks, if any). Each is the checked part minus material (asserted), so the
        # interference checks below hold for them too.
        log(f"== whole parts for printers with a {WHOLE_BED:.0f} mm bed or bigger (no split, no dovetails, nothing to glue)")
        os.makedirs(os.path.join(WHOLE_DIR, "usb_variants"), exist_ok=True)
        whole = {"lid": (build_kit_lid_shell(blocks=False), lid), "tray": (tray, tray), "panel": (panel, panel)}
        whole_pm = {sp: build_kit_lid_shell(usb=sp, blocks=False) for sp in USB_PM_VARIANTS}
        whole.update({f"usb_variants/{usb_variant_name(sp).replace('lid_A_left', 'lid')}":
                      (v, build_kit_lid_shell(usb=sp)) for sp, v in whole_pm.items()})
        for k, (v, checked) in whole.items():
            assert (v - checked).volume() < 0.01, (k, "a whole part must not add material to its full-block version")
            tm = export(v, f"{WHOLE_DIR}/{k}.stl")
            assert max(tm.extents[:2]) <= WHOLE_BED - 6.0, (k, tm.extents)
        log(f"  one-piece lid {whole['lid'][0].volume() / 1000:.2f} cm3 (the checked lid {lid.volume() / 1000:.2f} cm3)")
    log("== test coupons (cut from the real parts; print these first)")
    coupon_src = {}
    for k, (v, src) in build_kit_coupons(lid, tray, ta, tb).items():
        export(v, f"{OUT_DIR}/coupons/{k}.stl")
        coupon_src[k] = src
    with open(os.path.join(OUT_DIR, "coupons", "orientation.json"), "w") as f:
        json.dump(coupon_src, f, indent=1)

    log("== interference checks (closed)")
    interference(kit, lid, "kit (case + caps) vs lid")
    interference(plug, lid, "USB-C plug in the kit's port vs lid")
    interference(lid, tray, "lid vs tray")
    kb = prism_z(rrect(0.0, 0.0, 2 * KB_FACE_X - 0.3, 2 * KB_FACE_Y - 0.3, 2.7), TRAY_FLOOR, KB_TOP_Z)
    interference(kb, lid, f"keyboard space (tray floor {TRAY_FLOOR} to z {KB_TOP_Z}) vs lid")
    interference(kb, tray, "keyboard space vs tray (deck, pads, hinge bosses)")
    if SHELL and TRAY_DECK:
        d = TRAY_DECK
        log(f"  keyboard room {2 * KB_FACE_X:g} x {2 * KB_FACE_Y:g} mm from the floor up (the original tray's; nothing "
            f"stands into it: no ribs), {KB_FACE_X - KB_SIZE[0] / 2:g} / {KB_FACE_Y - KB_SIZE[1] / 2:g} mm a side round the "
            f"estimated {KB_SIZE[0]:g} x {KB_SIZE[1]:g} mm keyboard (MEASURE); deck {d['t']:g} mm flush with the rim, "
            f"{BACK_OLD_Y - WALL - KB_FACE_Y:.2f} mm wide at the front and the ends (45 deg under), "
            f"solid {Y_BACK - WALL - KB_FACE_Y:.2f} mm behind it, open over the charge port "
            f"(x {TRAY_PORT['x'][0]:g}..{TRAY_PORT['x'][1]:g})")
        assert (kb ^ tray).volume() < 1e-3 and (tray ^ lid).volume() < 1e-3
    if feet:
        log("== TPU feet")
        f = TPU_FEET
        fit = sum((ft ^ tray).volume() for ft in feet) / max(len(feet), 1)
        log(f"  feet: {len(feet)} pads {f['w']:g} x {f['d']:g} mm, {f['t']:g} thick in {f['pocket']:g} mm pockets "
            f"(press fit {f['fit']:g} mm a side, {fit:.1f} mm3 each), {FOOT_H:g} mm proud; the rear ones end "
            f"{f['inset']:g} mm in from the back edge (y = {Y_BACK - f['inset']:.1f}: the tipping edge); closed case "
            f"on its feet {top_z(-BACK_OLD_Y) + FOOT_H:.1f} mm tall at the front, {top_z(Y_BACK) + FOOT_H:.1f} at the back")
        for ft in feet:
            interference(ft, lid, "foot vs lid")
    if SHELL:
        interference(kit, panel, "kit vs bezel panel"); interference(panel, lid, "bezel panel vs lid")
        interference(panel, tray, "bezel panel vs tray"); interference(plug, panel, "USB-C plug vs bezel panel")
        interference(kb, panel, "keyboard space vs bezel panel"); interference(pa, pb, f"panel A vs B ({SPLIT_JOINT})")
        for sp, full in usb_variants.items():
            env = usb_pm_envelope_kit(sp)
            interference(env, full, f"{usb_variant_name(sp)}: panel-mount female vs lid", tol=0.05)
            interference(env, panel, f"{usb_variant_name(sp)}: panel-mount female vs panel", tol=0.05)
            interference(env, kit, f"{usb_variant_name(sp)}: panel-mount female vs kit", tol=0.05)
            interference(env, whole_pm[sp], f"{usb_variant_name(sp)}: panel-mount female vs the one-piece lid", tol=0.05)
        log(f"  panel-mount female: ears and body up to {usb_pm_room() - 0.2:.1f} mm tall fit between the panel and the ceiling")
        if PANEL_SNAP:
            g = PANEL_SNAP
            log(f"  panel snaps: {len(g['x_front']) + len(g['x_back'])} bumps ({g['len']:g} mm long; front edge x = "
                f"{', '.join(f'{x:+g}' for x in g['x_front'])}, back edge x = {', '.join(f'{x:+g}' for x in g['x_back'])}) "
                f"{g['bump'] - PANEL_CLR:.2f} mm past the wall on the way in, then in "
                f"{g['h'] - PANEL_CLR + g['clr']:.2f} mm grooves in the lid's {SHELL_WALL} mm walls; seated, they touch nothing")
    interference(la, lb, f"lid A vs B ({SPLIT_JOINT})"); interference(ta, tb, f"tray A vs B ({SPLIT_JOINT})")
    h_fixed, h_moving = hinge_envelope(0.0)
    interference(h_fixed, tray, "hinge (tray leaf + barrel) vs tray"); interference(h_moving, lid, "hinge (lid leaf) vs lid")
    interference(h_fixed, lid, "hinge barrel vs lid", tol=1.0)
    plain_lid_cov, plain_tray_cov = hinge_covers(ribs=False)        # clearance checks without the crush ribs
    for i, cv in enumerate(plain_lid_cov):
        interference(cv, lid, f"lid hinge cover {i} vs lid"); interference(cv, tray, f"lid hinge cover {i} vs tray")
    for i, cv in enumerate(plain_tray_cov):
        interference(cv, tray, f"tray hinge cover {i} vs tray"); interference(cv, lid, f"tray hinge cover {i} vs lid")
    if COVER_RIBS:
        rb = COVER_RIBS
        press = [(lid_cov[0] ^ lid).volume(), (tray_cov[0] ^ tray).volume()]
        log(f"  cover crush ribs: {rb['per_side']} per side edge, tapered {COVER_POCKET_CLR:g} -> {rb['h']:g} mm over the {COVER_T:g} mm "
            f"thickness, up to {rb['h'] - COVER_POCKET_CLR:.2f} mm into the pocket wall (pressed in: lid cover "
            f"{press[0]:.2f} mm3, tray cover {press[1]:.2f} mm3 of rib in the wall; nothing else touches)")
        assert 0.0 < min(press) and max(press) < 1.0, press
    if not SHELL:
        sx = kit_x(KIT_SCREW_D)
        seat = min(KIT_Z1 + KIT_SCREW_SEAT, top_z(0.0))
        log(f"  kit screw at x = {sx:.1f}: M2x4 countersunk, {seat - KIT_Z1:.1f} mm of lid under the head + {KIT_GAP} gap -> "
            f"{STRAP_SCREW_LEN - (seat - KIT_Z1) - KIT_GAP:.1f} mm into the kit (M5Stack: under 3 mm)")
    else:
        log(f"  the panel holds the kit: rim {PANEL_RIM['h']} mm around it ({KIT_FIT} clear), ribs 0.1 mm above its back; "
            f"{len(PANEL_SCREWS)} x M2x8 countersunk through the {PANEL_T} mm panel, {TAP_SCREW_LEN - PANEL_T:.1f} mm into the bosses")
        if PANEL_RIB_INFO:
            hs = [top_z(y) - SHELL_CEIL - PANEL_Z1 for _, y in PANEL_SCREWS]
            log(f"  panel bosses Ø{2 * PANEL_BOSS_R:g} (pilot {SCREW_PILOT_D}), {min(hs):.1f}..{max(hs):.1f} mm from the ceiling "
                f"down to the panel; ribs {PANEL_BOSS_RIBS['t']:g} thick, {PANEL_BOSS_RIBS['gap']:g} above the panel's back:")
            names = {(1, 0): "+x", (-1, 0): "-x", (0, 1): "+y", (0, -1): "-y"}
            for x, y in PANEL_SCREWS:
                rs = [f"{names[d]} {k} {r:.1f}" for bx, by, d, k, r in PANEL_RIB_INFO if (bx, by) == (x, y)]
                log(f"    ({x:g}, {y:g}): " + ", ".join(rs))
    skin = min(top_z(y) - KIT_Z1 for y in (KIT_Y0, KIT_Y1))
    log(f"  skin over the kit {skin:.2f}..{max(top_z(y) - KIT_Z1 for y in (KIT_Y0, KIT_Y1)):.2f} mm, over the USB-C channel "
        f"{min(top_z(KIT_USB_Y + s * USB_CH['w'] / 2) for s in (-1, 1)) - KIT_Z0 - USB_CH['h']:.2f} mm")

    log("== snap (latch): a lip on a thinned zone of the front wall, no slits")
    l, g = LATCH, LATCH["flex"]
    k, eps_n, (ex, ez, et) = latch_plate()
    d_static = l["bump"] - l["clr"]
    d_path, at = latch_path(lid, tray)
    mu = 0.3
    to, tc = np.tan(np.radians(l["open_deg"])), np.tan(np.radians(l["close_deg"]))
    f_open = k * d_static * (to + mu) / (1 - mu * to)
    f_close = k * d_path * (tc + mu) / (1 - mu * tc)
    eps = 100 * eps_n * k * max(d_static, d_path)
    log(f"  lip {l['w']:g} wide, {l['t']:g} thick, {l['below']:g} below the parting, not slit: the front wall is thinned "
        f"from inside to {g['t']:g} over x {g['x0']:g}..{g['x1']:g} (to {g['top']:g} below the ceiling, 45 deg chamfers) and "
        f"bends as a plate")
    log(f"  plate model (Kirchhoff, ceiling and end walls rigid, so the real wall is somewhat softer): {k:.1f} N/mm at the "
        f"bump; bump {l['bump']} - clearance {l['clr']} = {d_static:.2f} mm; on the real opening arc the lip moves out at "
        f"most {d_path:.2f} mm (at {at:.1f} deg)")
    log(f"  peak strain {eps:.2f} % (x {ex:.1f}, z {ez:.1f}, {et:.2f} thick; across the print layers: keep < 0.5 %), "
        f"spread over the zone, no slit ends; an outward pull of ~{0.714 / (100 * eps_n):.0f} N at the bump reaches ~25 MPa; "
        f"to open ~{f_open:.1f} N at the lip (+ the hinges' friction), to close ~{f_close:.1f} N")
    assert eps < 0.5, "latch strain"
    recess_back = -BACK_OLD_Y + l["t"] + l["clr"]
    log(f"  tray front wall left behind the recess {-LID_INNER_Y - recess_back:.2f} mm, behind the groove "
        f"{-LID_INNER_Y - recess_back - (l['bump'] - l['clr'] + 0.05):.2f} mm")

    log(f"== hinge motion (lid + kit + {'panel + ' if SHELL else ''}covers rotated about the real axis y={HINGE_AXIS_Y:.2f}, z={Z_PART}; tray fixed)")
    lidset = lid + kit + union(lid_cov) + (panel if SHELL else M())
    traset = tray + union(tray_cov)
    hits = []
    for deg in range(0, 181, 5):
        v = (open_lid(lidset, deg) ^ traset).volume()
        if v > 0.5:
            hits.append((deg, v))
    max_open = table_angle(to_t(lidset).vertices)
    log("  no collision with the tray from 0 to 180 deg" if not hits else f"  first contact at {hits[0][0]} deg ({hits[0][1]:.1f} mm3)")
    log(f"  on a table the lid reaches the table at {max_open:.1f} deg (opening limit)" if max_open else "  the lid never reaches the table")
    if COVER_FLUSH:
        k = COVER_CSK
        log(f"  covers {COVER_T:g} mm, flush in the back face; leaves {HINGE_SINK:g} mm deeper, axis "
            f"{HINGE_AXIS_Y - Y_BACK:.2f} mm outside the back face")
        log(f"  hinge screws M2x{HINGE_SCREW_LEN:g}: head in the cover (Ø{k['top_d']:g} x 90°), cone Ø{k['cone_d']:g} x "
            f"{k['cone_h']:g} in the leaf countersink, {HINGE_SCREW_DEPTH:g} mm past the leaf seat, tip "
            f"{HINGE_PAD['skin']:g} mm short of the end of its boss (Ø{HINGE_PILOT_D + 2 * HINGE_PAD['boss_wall']:g})")
        # tolerance: the axis height is read off the maker's 3D viewer (not in the catalogue): move it further in
        for sh in (-0.15, -0.3):
            fc = first_contact(lidset, traset, sh)
            log(f"  axis {-sh:g} mm further in ({HINGE_AXIS_Y + sh - Y_BACK:+.2f} mm from the back face): "
                + (f"lid meets tray at {fc} deg" if fc is not None else "still clear to 180 deg"))
            assert fc is None or max_open is None or fc > max_open, ("hinge tolerance: contact before the table limit", sh, fc)
    if hits and max_open is not None and hits[0][0] < max_open:
        log("  <-- CHECK: parts collide before the table limit")
    p = KB_PLUG
    log(f"== keyboard charge port (straight plug, overmold {p['w']:g} x {p['h']:g} mm, centred at x={p['x']:g} z={p['z']:g})")
    kplug = kb_plug_envelope()
    interference(kplug, tray, "charge plug vs tray")
    interference(kplug, lid, "charge plug vs lid (closed)")
    plug_limit = next((deg - 1 for deg in range(0, 181) if (open_lid(lidset, deg) ^ kplug).volume() > 0.05), None)
    log(f"  with that plug in, the lid opens to {plug_limit} deg; beyond that its back face meets the plug"
        if plug_limit is not None else "  the plug never meets the lid")

    log("== renders")
    C = dict(lid=(55, 75, 150), tray=(230, 220, 190), kit=(200, 200, 205), red=(210, 60, 50))
    def rend(name, items, view):
        R.render([(to_t(m) if isinstance(m, M) else m, c) for m, c in items], f"{RENDER_DIR}/{name}.png", view=view, title=name)
    rend("display_lid_inside", [(lid, C["lid"])], (-60, -45))
    rend("display_lid_outside", [(lid, C["lid"])], (-130, 30))
    rend("display_lid_with_kit", [(lid, C["lid"]), (kit, C["kit"])] + ([(panel, (225, 215, 185))] if SHELL else []), (-60, -45))
    if SHELL:
        rend("display_panel_kit_back", [(panel, (225, 215, 185))], (-60, 45))
    rend("keyboard_tray", [(tray, C["tray"])], (-130, 40))
    rend("split_lid", [(la.translate([-12, 0, 0]), C["lid"]), (lb, (90, 110, 180))], (-60, -45))
    rend("split_tray", [(ta.translate([-12, 0, 0]), C["tray"]), (tb, (200, 190, 160))], (-60, 45))
    with open(os.path.join(OUT_DIR, "build_log.txt"), "w") as f:
        f.write("\n".join(LOG) + "\n")


def main():
    if PD_MOUNT == "kit":
        return main_kit()
    os.makedirs(SPLIT_DIR, exist_ok=True); os.makedirs(RENDER_DIR, exist_ok=True)
    clean_outputs()
    report_layout()
    if not BATT_FITS:
        log("  !! battery does not fit; reduce BATT_T")

    log("== building")
    panel = build_panel(); strap = build_strap()
    krods = [build_key_rod(x) for x in KEY_X]; prod = build_power_rod()
    lid = build_lid(False)
    tray = build_tray()

    log("== exports (bounding boxes are axis-aligned in the original assembly frame)")
    out = {}
    out["display_panel_paperdiy"] = export(panel, f"{OUT_DIR}/display_panel_paperdiy.stl")
    out["paperdiy_strap"] = export(strap, f"{OUT_DIR}/paperdiy_strap.stl")
    out["key_pushrod"] = export(krods[0], f"{OUT_DIR}/key_pushrod_x2.stl")
    out["power_pushrod"] = export(prod, f"{OUT_DIR}/power_pushrod.stl")
    out["display_lid_usbc"] = export(lid, f"{OUT_DIR}/display_lid_usbc.stl")
    out["keyboard_tray"] = export(tray, f"{OUT_DIR}/keyboard_tray.stl")
    lid_cov, tray_cov = hinge_covers()
    if TOP_PLATE:
        out["top_plate_blank"] = export(build_top_plate(), f"{OUT_DIR}/top_plate_blank.stl")
    write_assembly_json()
    clip = build_front_clip(lid, tray)
    out["front_clip"] = export(clip, f"{OUT_DIR}/front_clip.stl")
    jig_l = build_magnet_jig()
    jig_r = jig_l.mirror([1, 0, 0])
    out["magnet_jig_L"] = export(jig_l, f"{OUT_DIR}/magnet_jig_L.stl")
    out["magnet_jig_R"] = export(jig_r, f"{OUT_DIR}/magnet_jig_R.stl")
    if lid_cov:
        out["hinge_cover_lid"] = export(lid_cov[0], f"{OUT_DIR}/hinge_cover_lid_x2.stl")
        out["hinge_cover_tray"] = export(tray_cov[0], f"{OUT_DIR}/hinge_cover_tray_x2.stl")

    log("== split pieces for A1 mini (limit %.0f mm)" % MAX_PIECE)
    la, lb = split_dovetail(lid, SPLIT_X_LID, DOVETAIL_Y, LID_CEILING_Z, LID_CEILING_Z + 3.0)
    ta, tb = split_dovetail(tray, SPLIT_X_TRAY, DOVETAIL_Y, 0.0, 3.0)
    pa, pb = split_dovetail(panel, SPLIT_X_PANEL, DOVETAIL_Y, PANEL_Z_FRONT, PANEL_Z_BACK)
    pieces = {"lid_A_left": la, "lid_B_main": lb, "tray_A_left": ta, "tray_B_main": tb, "panel_A_left": pa, "panel_B_main": pb}
    for k, v in pieces.items():
        tm = export(v, f"{SPLIT_DIR}/{k}.stl")
        assert max(tm.extents) <= MAX_PIECE, (k, tm.extents)
        out[k] = tm

    log("== lid A variants for other USB-C panel-mount hole spacings (only lid A changes)")
    usb_variants = {}
    for s in USB_PM_VARIANTS:
        name = usb_variant_name(s)
        if s == USB_PM_SCREW_SPACING:
            va, vb = la, lb
        else:
            va, vb = split_dovetail(build_lid(False, usb_spacing=s), SPLIT_X_LID, DOVETAIL_Y, LID_CEILING_Z, LID_CEILING_Z + 3.0)
            dv = abs(vb.volume() - lb.volume())
            assert dv < 0.01, (name, "lid B must not depend on the USB-C variant", dv)
        tm = export(va, f"{SPLIT_DIR}/usb_variants/{name}.stl")
        assert max(tm.extents) <= MAX_PIECE
        usb_variants[s] = va
        w = usb_pm_opening_w(s)
        log(f"    {name}: opening {w:.1f} x {USB_PM_H:.1f} mm" + (f", M3 holes {s:g} mm apart" if s > 0 else ", no screw holes (glue)"))

    log("== test coupons (cut from the real parts; print these first, ~1 h)")
    coupons = build_coupons(lid, tray, panel, ta, tb)
    coupon_src = {}
    for k, (v, src) in coupons.items():
        export(v, f"{OUT_DIR}/coupons/{k}.stl")
        coupon_src[k] = src
    with open(os.path.join(OUT_DIR, "coupons", "orientation.json"), "w") as f:
        json.dump(coupon_src, f, indent=1)

    log("== interference checks (assembled, closed lid)")
    pd, bat = paperdiy_envelope(), battery_envelope()
    interference(pd, panel, "PaperDIY envelope vs panel")
    interference(pd, strap, "PaperDIY envelope vs strap")
    if STRAP_LEGS:
        x_pcb = X_TOP - PD_PCB_TOP_FROM_TOP
        log(f"  strap legs stand {STRAP_LEGS['gap']} mm past the PCB's inner end (x = {x_pcb:.1f}), feet "
            f"{STRAP_LEGS['foot_clear']} mm above the display: the PCB cannot turn about its single standoff")
        if STRAP_RAILS:
            log(f"  strap rails reach x = {STRAP_RAILS['x_end']} (glass ends at {X_TOP}) with feet at x = "
                f"{', '.join(f'{x:g}' for x in STRAP_RAILS['feet_x'])} on the display's back: its far end cannot lift")
    interference(pd, lid, "PaperDIY envelope vs lid")
    interference(bat, panel, "battery vs panel")
    interference(bat, lid, "battery vs lid")
    interference(strap, lid, "strap vs lid"); interference(strap, panel, "strap vs panel")
    for i, r in enumerate(krods):
        interference(r, lid, f"key rod {i} vs lid"); interference(r, panel, f"key rod {i} vs panel"); interference(r, pd, f"key rod {i} vs PaperDIY")
    interference(prod, lid, "power rod vs lid"); interference(prod, panel, "power rod vs panel"); interference(prod, pd, "power rod vs PaperDIY")
    if ROD_SNAP:
        s = ROD_SNAP
        log(f"  rods pushed fully in ({s['play']} mm, barbs on the outer face) before the panel goes in:")
        for i, r in enumerate(krods):
            interference(r.translate([0, s["play"], 0]), panel, f"    key rod {i} pushed in vs panel cradle")
        interference(prod.translate([s["play"], 0, 0]), panel, "    power rod pushed in vs panel cradle")
        loc = rod_local(15.0)
        rb = ROD_HOLE / 2
        squeezed = sum(((loc ^ box(-BIG, 0.0, sg * s["slot"] / 2 if sg > 0 else -BIG, BIG if sg > 0 else -s["slot"] / 2, -BIG, BIG))
                        .translate([0, -sg * s["catch"], 0]) - cyl_x(rb, -10.0, 0.5, 0, 0)).volume() for sg in (1.0, -1.0))
        t, d = ROD_D / 2 - s["slot"] / 2, s["catch"] + 0.1
        log(f"  snap tip: barbs reach {rb + s['catch']:.2f} mm off the axis ({s['catch']} past the {ROD_HOLE} bore); halves squeezed "
            f"{s['catch']} mm each leave {squeezed:.3f} mm3 outside the bore; prong strain {150 * t * d / s['slot_len'] ** 2:.1f} % "
            f"(bore 0.1 small); press travel {s['play']} mm to the barb stop (rest gap {ROD_GAP})")
    interference(panel, lid, "panel vs lid", tol=1.0)
    interference(pa, pb, "panel A vs B (dovetail)"); interference(ta, tb, "tray A vs B (dovetail)"); interference(la, lb, "lid A vs B")
    h_fixed, h_moving = hinge_envelope(0.0)
    interference(h_fixed, tray, "hinge (tray leaf + barrel) vs tray"); interference(h_moving, lid, "hinge (lid leaf) vs lid")
    interference(h_fixed, lid, "hinge barrel vs lid", tol=1.0)
    log("== front clip (accessory; checked without its ridges at several places along the front)")
    clip0 = build_front_clip(lid, tray, bumps=False)
    for xc in (-75.0, -50.0, CLIP_X, 50.0, 80.0):
        c = clip0.translate([xc - CLIP_X, 0, 0])
        interference(c, lid, f"front clip at x={xc:.0f} vs lid"); interference(c, tray, f"front clip at x={xc:.0f} vs tray")
        for i, r in enumerate(krods):
            interference(c, r, f"front clip at x={xc:.0f} vs key rod {i}")
    log(f"  ridges: {(clip ^ lid).volume() + (clip ^ tray).volume():.2f} mm3 of intended overlap "
        f"({CLIP_BUMP} mm into the lid top and the tray bottom, the clip's spring preload)")
    log("== magnetic catch (retrofit): drilling jigs and the 2 x 3 mm magnet holes in the front walls")
    zt, zl = MAGNETS["land_z"], MAGNETS["land_z"] - 0.05      # land: tray top up to 8.05, lid bottom down to 8.00
    for nm, j in (("L", jig_l), ("R", jig_r)):
        interference(j.translate([0, 0, 0.01]), tray, f"jig {nm} on the tray")
        lid_j = j.translate([0, 0, -zt]).mirror([0, 0, 1]).translate([0, 0, zl - 0.01])
        interference(lid_j, lid, f"jig {'R' if nm == 'L' else 'L'} on the lid (upside down)")
    xs = magnet_hole_xs()
    for side, part in (("tray", tray), ("lid", lid)):
        holes = magnet_holes(side)
        inside = sum((h ^ part).volume() for h in holes)
        want = len(holes) * np.pi * (MAGNETS["d"] / 2) ** 2 * MAGNETS["depth"]
        log(f"  {side}: {len(holes)} holes at x = {', '.join(f'{x:+.0f}' for x in xs)}, y = {MAGNETS['y']}, "
            f"{MAGNETS['depth']} mm deep: {inside:.1f} of {want:.1f} mm3 in material "
            f"(the rest is the 0.5 mm seam chamfer the rim cuts through)")
    y_out, y_in = -(LID_INNER_Y + 3.0), -LID_INNER_Y
    log(f"  skin beside each hole: {MAGNETS['y'] - MAGNETS['d'] / 2 - y_out:.2f} mm to the front face, "
        f"{y_in - MAGNETS['y'] - MAGNETS['d'] / 2:.2f} mm to the inner face (hidden); lid and tray holes are coaxial")
    log(f"== hinge motion (lid + panel rotated about the real axis y={HINGE_AXIS_Y:.2f}, z={Z_PART}; tray fixed)")
    lidset = lid + panel
    traset = tray
    if lid_cov:
        for i, cv in enumerate(lid_cov):
            interference(cv, lid, f"lid hinge cover {i} vs lid"); interference(cv, tray, f"lid hinge cover {i} vs tray")
        for i, cv in enumerate(tray_cov):
            interference(cv, tray, f"tray hinge cover {i} vs tray"); interference(cv, lid, f"tray hinge cover {i} vs lid")
        lidset = lidset + union(lid_cov)
        traset = tray + union(tray_cov)
    max_open, hits = None, []
    for deg in range(0, 181, 5):
        moved = open_lid(lidset, deg)
        v = (moved ^ traset).volume()
        if v > 0.5:
            hits.append((deg, v))
    max_open = table_angle(to_t(lidset).vertices)
    first_hit = hits[0][0] if hits else None
    if first_hit is None:
        log("  no collision with the tray from 0 to 180 deg")
    else:
        log(f"  first contact at {first_hit} deg ({hits[0][1]:.1f} mm3)")
    log(f"  on a table the lid's top-back edge reaches the table at {max_open:.1f} deg (opening limit)"
        if max_open else "  the lid never reaches the table")
    if first_hit is not None and max_open is not None and first_hit < max_open:
        log("  <-- CHECK: parts collide before the table limit")
    # gaps that should be small but positive
    for i, x in enumerate(KEY_X):
        log(f"  key {i}: rod tip y={KEY_TIP_Y-ROD_GAP:.2f}, actuator tip y={KEY_TIP_Y:.2f}")

    p = KB_PLUG
    log(f"== keyboard charge port (straight plug, overmold {p['w']:g} x {p['h']:g} mm, centred at x={p['x']:g} z={p['z']:g})")
    plug = kb_plug_envelope()
    interference(plug, tray, "charge plug vs tray")
    interference(plug, lid, "charge plug vs lid (closed)")
    plug_limit = None
    for deg in range(0, 181):
        if (open_lid(lidset, deg) ^ plug).volume() > 0.05:
            plug_limit = deg - 1
            break
    log(f"  with that plug in, the lid opens to {plug_limit} deg; beyond that its back face meets the plug"
        if plug_limit is not None else "  the plug never meets the lid")

    log("== USB-C panel-mount fit per lid-A variant (rough screw-ear envelope: ears 4 mm past the holes, 8 tall, 3 thick)")
    for s, va in usb_variants.items():
        env = usb_pm_envelope(s)
        full = lid if s == USB_PM_SCREW_SPACING else (va + lb)
        worst = max(interference(env, full, f"{usb_variant_name(s)}: connector vs lid", tol=1.0),
                    interference(env, prod, f"{usb_variant_name(s)}: connector vs power push-rod", tol=0.05),
                    interference(env, panel, f"{usb_variant_name(s)}: connector vs panel", tol=0.05))
        if worst > 1.0:
            log(f"    <-- {usb_variant_name(s)}: check the ear size of your cable")

    log("== renders")
    C = dict(lid=(55, 75, 150), panel=(225, 215, 185), tray=(230, 220, 190), red=(210, 60, 50), grey=(120, 120, 125),
             pd=(40, 120, 70), bat=(200, 170, 40))
    def rend(name, items, view):
        R.render([(to_t(m) if isinstance(m, M) else m, c) for m, c in items], f"{RENDER_DIR}/{name}.png", view=view, title=name)
    rend("display_panel_paperdiy_back", [(panel, C["panel"])], (-60, 45))
    rend("display_panel_paperdiy_front", [(panel, C["panel"])], (-60, -45))
    rend("display_lid_usbc_inside", [(lid, C["lid"])], (-60, -45))
    rend("display_lid_usbc_outside", [(lid, C["lid"])], (-130, 30))
    rend("keyboard_tray", [(tray, C["tray"])], (-130, 40))
    rend("paperdiy_strap", [(strap, C["grey"])], (-60, 40))
    rend("pushrods", [(krods[0], C["red"]), (krods[1], C["red"]), (prod, C["red"])], (-60, 40))
    rend("assembly_panel_side", [(panel, C["panel"]), (strap, C["grey"]), (krods[0], C["red"]), (krods[1], C["red"]),
                                 (prod, C["red"]), (pd, C["pd"]), (bat, C["bat"])], (-60, 50))
    rend("split_lid", [(la.translate([-12, 0, 0]), C["lid"]), (lb, (90, 110, 180))], (-60, -45))
    rend("split_tray", [(ta.translate([-12, 0, 0]), C["tray"]), (tb, (200, 190, 160))], (-60, 45))
    rend("split_panel", [(pa.translate([-12, 0, 0]), C["panel"]), (pb, (200, 190, 160))], (-60, 45))
    rend("split_panel_front", [(pa.translate([-12, 0, 0]), C["panel"]), (pb, (200, 190, 160))], (-60, -45))
    with open(os.path.join(OUT_DIR, "build_log.txt"), "w") as f:
        f.write("\n".join(LOG) + "\n")


if __name__ == "__main__":
    main()
