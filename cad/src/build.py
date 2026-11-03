#!/usr/bin/env python3
"""Build every output STL + renders for the PaperDIY PDA clamshell.

Run:  python3 ~/cad/src/build.py          (needs: trimesh manifold3d numpy shapely rtree pillow)
Booleans are done with manifold3d on the ORIGINAL phone-enclosure meshes (read-only, never modified).
"""
import os, sys, json, hashlib
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


def split_dovetail(part, X, ys, z0, z1):
    keys = union(prism_z(dovetail_cs(X, y), z0 - 0.5, z1 + 0.5) for y in ys)
    keys_c = union(prism_z(dovetail_cs(X, y).offset(DOVETAIL["clr"], m3.JoinType.Miter), z0 - 0.5, z1 + 0.5) for y in ys)
    A = (part ^ box(-BIG, X, -BIG, BIG, -BIG, BIG)) + (part ^ keys)
    B = (part ^ box(X, BIG, -BIG, BIG, -BIG, BIG)) - keys_c
    return A, B


def split_plain(part, X):
    return part ^ box(-BIG, X, -BIG, BIG, -BIG, BIG), part ^ box(X, BIG, -BIG, BIG, -BIG, BIG)


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
    for (x, y, zb) in [(STRAP_X, STRAP_POST_Y, STRAP_UNDER), (STRAP_X, -STRAP_POST_Y, STRAP_UNDER), (SO_X, SO_Y, SO_TOP)]:
        s = s - cyl_z(M2_CLEAR / 2, zb - 1, STRAP_TOP + 1, x, y)
        s = s - cyl_z(M2_CLEAR / 2, STRAP_TOP - (CSK_D - M2_CLEAR) / 2, STRAP_TOP + 0.01, x, y, CSK_D / 2)  # 90 deg countersink
    return s


def dflat(rod, zc):        # flat underside ROD_FLAT below the axis: prints flat, rests on the U-cradle floor
    return rod ^ box(-BIG, BIG, -BIG, BIG, zc - ROD_FLAT, BIG)


def build_key_rod(x):
    y_in, y_out = KEY_TIP_Y - ROD_GAP, -46.5 - ROD_PROUD
    r = cyl_y(ROD_D / 2, y_out, y_in, x, KEY_Z) + cyl_y(ROD_COLLAR_D / 2, -LID_INNER_Y, -LID_INNER_Y + ROD_COLLAR_T, x, KEY_Z)
    return dflat(r, KEY_Z)


def build_power_rod():
    x_in, x_out = PWR_TIP_X - ROD_GAP, -101.0 - ROD_PROUD
    r = cyl_x(ROD_D / 2, x_out, x_in, PWR_Y, PWR_Z) + cyl_x(ROD_COLLAR_D / 2, -LID_INNER_X, -LID_INNER_X + ROD_COLLAR_T, PWR_Y, PWR_Z)
    return dflat(r, PWR_Z)


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


def warp_back(part, lower_rim=0.0):
    """Thicken the back wall outward by BACK_EXTRA: move the outer half of the wall (and the top / bottom
    chamfers and the rounded back corners) back, leave the inner pocket untouched."""
    tm = to_t(part)
    v = tm.vertices.copy()
    ax, y, z = np.abs(v[:, 0]), v[:, 1], v[:, 2]
    cx, cy = CORNER_C
    zc = (z < 2.95) | (z > 27.05)                      # top chamfer of the lid / bottom chamfer of the tray
    r = np.hypot(ax - cx, y - cy)
    straight = (y > 45.0) | ((y > 43.0) & zc)
    corner = (y > cy) & ((r > 4.5) | (zc & (r >= 2.9)))
    move = np.where(ax <= cx, straight, corner)
    v[move, 1] += BACK_EXTRA
    if lower_rim:          # tray only: the warped lid / tray parting surfaces differ by <= 0.05 mm; keep a gap
        v[z > 12.3, 2] -= lower_rim
    return to_m(trimesh.Trimesh(v, tm.faces, process=False))


def hinge_centres():
    return (-HINGE_X, HINGE_X)


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
            cuts.append(box(x0, x1, Y_BACK - HINGE_LEAF_T - 0.05, Y_BACK + 1.0, zlo, Z_PART + HINGE_WIDTH / 2 + HINGE_CLR))
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
                seat = Y_BACK - HINGE_LEAF_T
                depth = TAP_SCREW_LEN - HINGE_LEAF_T                # M2x8, head in the leaf countersink: 6 mm past the seat
                zz = Z_PART + HINGE_HOLE_OFF if lid else Z_PART - HINGE_HOLE_OFF
                out.append(cyl_y(HINGE_PILOT_D / 2, seat - depth, seat + 0.1, x, zz))
    return out


def lid_hinge_bosses():
    behind = BACK_OLD_Y - LID_INNER_Y + BACK_EXTRA - HINGE_LEAF_T          # wall behind the leaf seat
    if HINGE_MOUNT == "parting" or behind >= TAP_SCREW_LEN - HINGE_LEAF_T + 1.0:   # wall alone holds the screws
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
        else:
            fixed.append(box(x0, x1, Y_BACK - HINGE_LEAF_T, Y_BACK, Z_PART - HINGE_WIDTH / 2, Z_PART - r))
            moving.append(box(x0, x1, Y_BACK - HINGE_LEAF_T, Y_BACK, Z_PART + r, Z_PART + HINGE_WIDTH / 2))
        fixed.append(cyl_x(r, x0, x1, Y_BACK, Z_PART))
    return union(fixed), open_lid(union(moving), open_deg)


def build_top_plate():
    x0, x1, y0, y1 = LID_LABEL_POCKET
    return prism_z(rrect((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0 - 0.3, y1 - y0 - 0.3, 1.5), 28.5, 30.0)


def write_assembly_json():
    """Positions the README renderer needs (docs/render reads this instead of copying numbers)."""
    data = dict(Y_BACK=Y_BACK, Z_PART=Z_PART, HINGE_X=HINGE_X, HINGE_LEN=HINGE_LEN, HINGE_WIDTH=HINGE_WIDTH,
                HINGE_LEAF_T=HINGE_LEAF_T, HINGE_BARREL_D=HINGE_BARREL_D, HINGE_CLR=HINGE_CLR,
                HINGE_COVER=bool(HINGE_COVER and HINGE_MOUNT == "face"), COVER_T=COVER_T, COVER_RIM=COVER_RIM,
                COVER_R0=COVER_R0, HINGE_MOUNT=HINGE_MOUNT, LABEL_POCKET=list(LID_LABEL_POCKET),
                USB_PM_Y=USB_PM_Y, USB_PM_Z=USB_PM_Z,
                BATT=dict(cx=BATT_CX, cy=BATT_CY, z0=PANEL_Z_BACK - BATT_POCKET, L=BATT_L, W=BATT_W, T=BATT_T),
                STRAP=dict(x=STRAP_X, w=STRAP_W, y=STRAP_POST_Y, top=STRAP_TOP))
    with open(os.path.join(OUT_DIR, "assembly.json"), "w") as f:
        json.dump(data, f, indent=1)


def hinge_covers():
    """Cover plates over the leaves (face mounting), in the closed assembly position: (lid covers, tray covers)."""
    if HINGE_MOUNT != "face" or not HINGE_COVER:
        return [], []
    lid_c, tray_c = [], []
    half_w = HINGE_LEN / 2 + HINGE_CLR + COVER_RIM
    leaf_end = HINGE_WIDTH / 2 + HINGE_CLR + COVER_RIM
    for c in hinge_centres():
        z0, z1 = Z_PART + COVER_R0, min(Z_PART + leaf_end, 26.8)            # stop below the lid's top chamfer
        lid_c.append(prism_y(rrect(c, (z0 + z1) / 2, 2 * half_w, z1 - z0, 1.0), Y_BACK, Y_BACK + COVER_T))
        z0, z1 = max(0.3, Z_PART - leaf_end), Z_PART - COVER_R0
        tray_c.append(prism_y(rrect(c, (z0 + z1) / 2, 2 * half_w, z1 - z0, 1.0), Y_BACK, Y_BACK + COVER_T))
    return lid_c, tray_c


def open_lid(part, deg):
    """Rotate a lid-side part about the hinge axis; positive = opening."""
    return part.translate([0, -Y_BACK, -Z_PART]).rotate([-deg, 0, 0]).translate([0, Y_BACK, Z_PART])


def kb_port_bay():
    """Recess in the back face around the keyboard charge port, back to the original 3 mm wall (lid and tray)."""
    if not KB_PORT_BAY:
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
    L = warp_back(rebuild_back(L, LID_BACK_PROFILE, -1.0, 31.0))
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
    return L - union(cuts)


# ------------------------------------------------------------------ TRAY
def build_tray():
    T = to_m(load("Keyboard.stl"))
    # hinge rework: remove ears + trough, rebuild + thicken the back wall
    T = warp_back(rebuild_back(T, TRAY_BACK_PROFILE, -1.0, 20.0), lower_rim=0.08)
    # square the bottom-back chamfer under each tray leaf so the whole leaf sits in a pocket
    for c in (hinge_centres() if HINGE_MOUNT == "face" else ()):
        T = T + box(c - HINGE_LEN / 2 - HINGE_CLR, c + HINGE_LEN / 2 + HINGE_CLR, LID_INNER_Y + 0.5, Y_BACK, 0.0, 3.2)
    T = T - union(hinge_pocket_cuts() + hinge_pilots(False) + kb_port_bay())
    if not KB_CUTS_ENABLED:
        return T
    sx = -1 if KB_PORT_WALL == "left" else 1
    xa, xb = sorted([sx * 102.0, sx * 96.5])
    T = T - prism_x(rrect(KB_PORT_Y, KB_PORT_Z, KB_PORT_W, KB_PORT_H, 1.0), xa, xb)
    T = T - prism_x(rrect(KB_SW_Y, KB_SW_BOTTOM_Z + 10, KB_SW_W, 20, 1.0), xa, xb)
    return T


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
def main():
    os.makedirs(SPLIT_DIR, exist_ok=True); os.makedirs(RENDER_DIR, exist_ok=True)
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
    interference(pd, lid, "PaperDIY envelope vs lid")
    interference(bat, panel, "battery vs panel")
    interference(bat, lid, "battery vs lid")
    interference(strap, lid, "strap vs lid"); interference(strap, panel, "strap vs panel")
    for i, r in enumerate(krods):
        interference(r, lid, f"key rod {i} vs lid"); interference(r, panel, f"key rod {i} vs panel"); interference(r, pd, f"key rod {i} vs PaperDIY")
    interference(prod, lid, "power rod vs lid"); interference(prod, panel, "power rod vs panel"); interference(prod, pd, "power rod vs PaperDIY")
    interference(panel, lid, "panel vs lid", tol=1.0)
    interference(pa, pb, "panel A vs B (dovetail)"); interference(ta, tb, "tray A vs B (dovetail)"); interference(la, lb, "lid A vs B")
    h_fixed, h_moving = hinge_envelope(0.0)
    interference(h_fixed, tray, "hinge (tray leaf + barrel) vs tray"); interference(h_moving, lid, "hinge (lid leaf) vs lid")
    interference(h_fixed, lid, "hinge barrel vs lid", tol=1.0)
    log("== hinge motion (lid + panel rotated about the new axis; tray fixed)")
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
        if max_open is None and to_t(moved).bounds[0][2] < 0:
            max_open = deg
    first_hit = hits[0][0] if hits else None
    if first_hit is None:
        log("  no collision with the tray from 0 to 180 deg")
    else:
        log(f"  first contact at {first_hit} deg ({hits[0][1]:.1f} mm3): the hinge covers meet there and act as the stop")
    log(f"  on a table the lid's top-back edge reaches the table at about {max_open} deg (opening limit)"
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
