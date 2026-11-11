#!/usr/bin/env python3
"""Simulate the lid closing onto its snap, and the hinges' spring-back lifting it again (kit design).

What the build checks is the drawn geometry with the lid exactly where it was drawn. This asks the other question: what
happens when the lid does not sit there (it hangs on the hinges 100 mm behind the snap), and when the printed gaps come
out a little wider or tighter than drawn.

Model (quasi-static, a section front to back):
- Geometry: sections of the built lid and tray (out/*.stl) through the middle of the lip and through a stop tongue. The
  lid is rigid and turns about the real hinge axis. For every angle of the last 3 degrees: how far the lip has to move
  outward to clear the tray (A), and how far forward the tongue lets the lid sit (B).
- Springs: the lid's front wall is the plate of src/latch_plate.py with two load cases, the lip pushed outward and the
  tongues pushed inward (stiffness of each, and how much one moves the other).
- The lid may sit off its drawn position front to back (`at`, - = forward), may shift freely by +-`play` about that
  (against a slip force), and resists being pushed further with `k_seat` (the hinges and their seats; not known).
- Coulomb friction (mu) on the ramps. Closing force and hold are forces at the front edge.
- After closing, the hinges' spring-back pushes the front edge up (HINGE_TORQUE, less the lid's weight): the lid is
  "held" if the snap carries that push before the lip is over the bump.

What it cannot know: where the lid really sits on the hinges and how freely it shifts, how the printed gaps come out,
and the give of the hinges. Those are inputs here; the tables show how the answer depends on them.

    python3 tools/snap_sim.py [--figure ../docs/images/snap_sim.png] [--gif snap.gif]
Writes out/snap_sim.md and out/snap_sim.json (after src/build.py).
"""
import argparse
import contextlib
import io
import json
import os
import sys

import numpy as np
import trimesh
from shapely.affinity import rotate, translate
from shapely.geometry import Polygon
from shapely.geometry import box as sbox
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                    # noqa: E402
from latch_plate import wall_compliance, wall_plate      # noqa: E402

YZ = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
AXIS = (B.HINGE_AXIS_Y, B.Z_PART)
Y_FRONT = -B.BACK_OLD_Y
Z_EDGE = B.under_z(Y_FRONT)                              # the parting line at the front
LEVER = B.HINGE_AXIS_Y + B.BACK_OLD_Y                    # axis to the front face
SKIN = 0.004                                             # bodies closer than this count as touching, not overlapping
STEP = 0.01                                              # deg
DEG0 = 3.0
FREE = 0.8                                               # |A|, |B| beyond this = no contact in reach
MU = 0.3
K_SEAT_STIFF = 1000.0                                    # N/mm: "the lid does not give front to back"


def section(mesh, x, erode=0.0):
    s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    p2, _ = s.to_planar(to_2D=YZ, check=False)
    g = unary_union(list(p2.polygons_full)).intersection(sbox(Y_FRONT - 3.0, Z_EDGE - 9.0, Y_FRONT + 9.0, Z_EDGE + 16.0))
    return g.buffer(-erode) if erode else g


def at_angle(g, deg):
    return rotate(g, -deg, origin=AXIS)


class Geometry:
    """A(angle), B(angle), C(angle) from the sections: the lip must sit A further out than drawn; the lid must sit
    between B and C (front to back) for the tongue to clear the tray."""

    def __init__(self, lid, tray):
        l, st = B.LATCH, B.LATCH["stop"]
        self.lip, self.tray_lip = section(lid, l["x"], SKIN), section(tray, l["x"])
        self.ton, self.tray_ton = section(lid, st["x"][1], SKIN), section(tray, st["x"][1])
        ya, yb = Y_FRONT - 3.0, Y_FRONT + 9.0            # the tongue proper: what hangs below the parting (the lid's
        self.ton = self.ton.intersection(Polygon([(ya, Z_EDGE - 9.0), (yb, Z_EDGE - 9.0), (yb, B.under_z(yb) - 0.02),
                                                  (ya, B.under_z(ya) - 0.02)]))    # wall resting on the tray is no stop)
        self.lip_draw, self.ton_draw = section(lid, l["x"]), section(lid, st["x"][1])
        self.deg = np.round(np.arange(0.0, DEG0 + STEP / 2, STEP), 4)
        self.A = np.array([self._lip_need(d) for d in self.deg])
        bc = np.array([self._lid_range(d) for d in self.deg])
        self.B, self.C = np.maximum(bc[:, 0], -FREE), np.minimum(bc[:, 1], FREE)
        arc = np.radians(self.deg) * float(np.hypot(AXIS[0] - Y_FRONT, AXIS[1] - (Z_EDGE - l["bump_at"])))
        self.dA = np.gradient(self.A, arc)               # per mm of lift at the bump
        self.dB = np.gradient(self.B, arc)
        self.crest = int(np.argmax(self.A))

    def _lip_need(self, deg):
        g = at_angle(self.lip, deg)
        hit = lambda t: translate(g, -t, 0).intersects(self.tray_lip)       # noqa: E731
        if not hit(-FREE):
            return -FREE
        lo, hi = -FREE, 1.6                              # hit at lo, clear at hi
        for _ in range(14):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if hit(mid) else (lo, mid)
        return hi

    def _lid_range(self, deg):
        g = at_angle(self.ton, deg)
        hit = lambda u: translate(g, u, 0).intersects(self.tray_ton)        # noqa: E731
        us = np.round(np.arange(-FREE, FREE + 1e-9, 0.02), 3)
        ok = [not hit(u) for u in us]
        if not any(ok):
            raise SystemExit(f"no room for the stop tongue at {deg} deg")
        i = min((j for j in range(len(us)) if ok[j]), key=lambda j: abs(us[j]))
        lo = hi = i
        while lo > 0 and ok[lo - 1]:
            lo -= 1
        while hi < len(us) - 1 and ok[hi + 1]:
            hi += 1

        def edge(u_ok, u_hit):
            for _ in range(8):
                mid = (u_ok + u_hit) / 2
                u_ok, u_hit = (u_ok, mid) if hit(mid) else (mid, u_hit)
            return u_ok
        return (edge(us[lo], us[lo] - 0.02) if lo > 0 else -9.0, edge(us[hi], us[hi] + 0.02) if hi < len(us) - 1 else 9.0)


def springback():
    """(low, typical, high) push at the front edge, N: the print report's figure if it is there."""
    try:
        with open(os.path.join(B.OUT_DIR, "print_report.json")) as f:
            return tuple(json.load(f)["springback_push_n"])
    except (OSError, KeyError):
        return (0.5, 0.9, 1.3)


def plate():
    """Stiffness of the lip and of the two tongues' backing, their coupling, and the strain per newton at the lip."""
    l, g, st = B.LATCH, B.LATCH["flex"], B.LATCH["stop"]
    args = (Z_EDGE, B.top_z(Y_FRONT + B.SHELL_WALL) - B.SHELL_CEIL, 202.0 / 2 - B.SHELL_WALL, B.SHELL_WALL,
            (g["x0"], g["x1"], g["t"], g["top"]))
    lip = (l["x"] - l["w"] / 2, l["x"] + l["w"] / 2)
    C = wall_compliance(*args, [[lip + (l["bump_at"],)],
                                [(x - st["w"] / 2, x + st["w"] / 2, st["lead"] + 0.2) for x in st["x"]]])
    return C, wall_plate(*args, lip, l["bump_at"])[1]


def contact(a, b, C):
    """Lip must move out by a, tongues in by b (either may be negative = a gap). Returns the two contact forces."""
    cll, clt, ctt = C[0, 0], C[0, 1], C[1, 1]
    if a <= 0 and b <= 0:
        return 0.0, 0.0
    if a > 0 and -clt * a / cll >= b:
        return a / cll, 0.0
    if b > 0 and -clt * b / ctt >= a:
        return 0.0, b / ctt
    det = cll * ctt - clt * clt
    return (ctt * a + clt * b) / det, (clt * a + cll * b) / det


def wedge(n, slope, mu):
    """Force along the motion needed to push a contact carrying n up a ramp of this slope."""
    return n * (slope + mu) / max(1.0 - mu * slope, 0.05)


def run(geo, C, eps_n, stops=True, at=0.0, play=0.0, slip=0.5, k_seat=K_SEAT_STIFF, gap_lip=0.0, gap_stop=0.0, mu=MU,
        push=None, frames=None):
    """Close from DEG0 to 0, then let the spring-back lift the front edge. Returns a dict of results."""
    push = springback()[2] if push is None else push
    kc = 1.0 / C[1, 1]

    def forces(i, u):
        a = geo.A[i] + u - gap_lip
        if not stops:
            return max(a, 0.0) / C[0, 0], 0.0, 0.0, -k_seat * (u - min(max(u, at - play), at + play))
        nl, nt = contact(a, (geo.B[i] - gap_stop) - u, C)
        nb = kc * max(u - (geo.C[i] + gap_stop), 0.0)     # the tongue's back against the notch in the deck
        return nl, nt, nb, -k_seat * (u - min(max(u, at - play), at + play))

    def settle(i, u):
        def net(v):
            nl, nt, nb, seat = forces(i, v)
            return -nl + nt - nb + seat
        n0 = net(u)
        if abs(n0) <= slip:
            return u
        target = slip if n0 > 0 else -slip               # net falls as u rises
        lo, hi = (u, u + 2.0) if n0 > 0 else (u - 2.0, u)
        for _ in range(40):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if net(mid) > target else (lo, mid)
        return (lo + hi) / 2

    def lip_out(nl, nt):
        return C[0, 0] * nl - C[0, 1] * nt

    out, u = {}, at
    n = len(geo.deg)
    f_close, d_max, nl_max, nt_max = 0.0, 0.0, 0.0, 0.0
    for i in range(n - 1, -1, -1):                       # closing
        u = settle(i, u)
        nl, nt, nb, _ = forces(i, u)
        f = wedge(nl, -geo.dA[i], mu) + wedge(nt, -geo.dB[i], mu) + mu * nb
        f_close, d_max, nl_max, nt_max = max(f_close, f), max(d_max, lip_out(nl, nt)), max(nl_max, nl), max(nt_max, nt)
        if frames is not None:
            frames.append(("close", float(geo.deg[i]), u, lip_out(nl, nt), f))
    nl0, nt0, _, _ = forces(0, u)
    out.update(close_n=f_close, lip_bend_max=d_max, strain_pct=100 * eps_n * nl_max, tongue_n=nt_max, lid_at=u,
               lip_bend_closed=lip_out(nl0, nt0))
    hold, gap, held = 0.0, None, False
    for i in range(0, n):                                # the spring-back lifts the front edge
        u = settle(i, u)
        nl, nt, nb, _ = forces(i, u)
        f = wedge(nl, geo.dA[i], mu) + wedge(nt, geo.dB[i], mu) + mu * nb
        hold = max(hold, f)
        if not held and f >= push and i <= geo.crest:
            held, gap = True, LEVER * np.radians(geo.deg[i])
        if frames is not None and (not held or gap == LEVER * np.radians(geo.deg[i])):
            frames.append(("lift", float(geo.deg[i]), u, lip_out(nl, nt), f))
        if i > geo.crest and nl <= 0.0 and nt <= 0.0:
            break
    out.update(hold_n=hold, held=held, seam_gap=gap)
    return out


# ------------------------------------------------------------------ report
HOLD_OK = 4.0                                            # N: about three times the spring-back's push


def verdict(r):
    if r["close_n"] > 40:
        return "does not close by hand"
    if not r["held"]:
        return "does not hold"
    if r["hold_n"] < HOLD_OK:
        return "weak: opens when handled"
    return "holds" + (", hard to close" if r["close_n"] > 20 else "") + (", strain over 0.5 %" if r["strain_pct"] > 0.5 else "")


def row(label, r):
    gap = f"{r['seam_gap']:.2f}" if r["seam_gap"] is not None else "-"
    return (f"| {label} | {r['lip_bend_max']:.2f} | {r['close_n']:.1f} | {r['lid_at']:+.2f} | {r['hold_n']:.1f} | {gap} | "
            f"{r['strain_pct']:.2f} | {verdict(r)} |")


HEAD = ["| | lip bends, mm | to close, N | lid ends at, mm | holds, N | seam, mm | strain, % | |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |"]


def report(geo, C, eps_n):
    l, st = B.LATCH, B.LATCH["stop"]
    lo, _, hi = springback()
    res = {}
    L = ["# Snap simulation", "",
         "Generated by `tools/snap_sim.py` from the built lid and tray (see its header for the model). Forces are at the "
         f"front edge. The hinges' spring-back pushes the closed lid's front edge up with {lo:.1f}..{hi:.1f} N: under {hi:.1f} N the "
         f"snap \"does not hold\", under {HOLD_OK:g} N it is \"weak\" (the lid comes open when the device is handled). "
         f"Friction {MU:g}. Seam = how far the front edge comes up before the snap carries the push.", "",
         f"Springs (plate model): lip {1 / C[0, 0]:.1f} N/mm, the two stop tongues' backing {1 / C[1, 1]:.0f} N/mm; pushing "
         f"the tongues in by 1 mm draws the lip in by {C[0, 1] / C[1, 1]:.2f} mm. Drawn: bump {l['bump']:g} mm, lip "
         f"{l['clr']:g} mm off the tray, tongues {st['clr']:g} mm off the wall's inner face (the lowest point the lid can "
         f"reach forward is {-geo.B[0]:.2f} mm, because the tongue's face leans back with the closing arc).", ""]

    def table(title, note, rows):
        L.extend([f"## {title}", "", note, ""] + HEAD)
        for key, label, kw in rows:
            res[key] = run(geo, C, eps_n, **kw)
            L.append(row(label, res[key]))
        L.append("")

    free = dict(play=0.3, k_seat=K_SEAT_STIFF)
    table("1. The lid is free to shift front to back (+-0.3 mm, 0.5 N to move it)",
          "What the stops were added for. Without them the ramp pushes the lid forward and the lip hardly bends.",
          [("free_nostop", "without stops", dict(stops=False, **free)), ("free_stop", "with stops", free)])
    offs = (-0.5, -0.4, -0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.3)
    table("2. The lid sits off its drawn position and does not give (- = forward)",
          "Seat depths of the hinge leaves and the print's scale decide this; it cannot be computed. Without stops the "
          "engagement is simply the bump less the gap. With stops a lid that sits forward squeezes the tongues against "
          "the tray's wall.",
          [(f"fixed_{'stop' if st_ else 'nostop'}_{o:+.1f}", f"{'with' if st_ else 'without'} stops, lid at {o:+.1f}",
            dict(stops=st_, at=o)) for st_ in (False, True) for o in offs])
    table("2b. The same, but the lid gives a little when pushed (with stops, lid 0.4 mm forward)",
          "How stiffly the hinges and their seats hold the lid front to back is not known either. If it gives, the "
          "tongues push it back into place and the lip catches.",
          [(f"give_{k:g}", f"gives {k:g} N/mm", dict(at=-0.4, k_seat=k)) for k in (300.0, 100.0, 30.0)])
    gaps = (-0.10, -0.05, 0.0, 0.05, 0.10, 0.15)
    table("3. The printed gaps differ from the drawing (with stops; + = wider, both the lip's and the tongues')",
          "Two cases each: the lid exactly in place and rigid, and free to shift as in 1.",
          [(f"gap_{g:+.2f}_{name}", f"gaps {g:+.2f}, lid {name}", dict(gap_lip=g, gap_stop=g, **kw))
           for g in gaps for name, kw in (("in place", {}), ("free", free))])
    return L, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure")
    ap.add_argument("--gif")
    a = ap.parse_args()
    if B.PD_MOUNT != "kit" or not B.SHELL:
        sys.exit("snap_sim: the kit design with the shell lid only")
    lid = trimesh.load(os.path.join(B.OUT_DIR, "display_lid_usbc.stl"))
    tray = trimesh.load(os.path.join(B.OUT_DIR, "keyboard_tray.stl"))
    C, eps_n = plate()
    geo = Geometry(lid, tray)
    L, res = report(geo, C, eps_n)
    with open(os.path.join(B.OUT_DIR, "snap_sim.md"), "w") as f:
        f.write("\n".join(L) + "\n")
    with open(os.path.join(B.OUT_DIR, "snap_sim.json"), "w") as f:
        json.dump({k: {kk: (None if v is None else round(float(v), 3) if not isinstance(v, bool) else v)
                       for kk, v in r.items()} for k, r in res.items()}, f, indent=1)
    print("\n".join(L))
    if a.figure or a.gif:
        import snap_sim_figure
        snap_sim_figure.make(sys.modules[__name__], geo, C, eps_n, a.figure, a.gif)


if __name__ == "__main__":
    main()
