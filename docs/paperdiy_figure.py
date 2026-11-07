"""Draw docs/images/paperdiy_mount.png: how the PaperDIY is held on the screen panel (back view of the panel + a section
along the strap).

Panel, strap and posts are cut from the built STLs (cad/out); the PaperDIY and the screws are drawn from
cad/src/params.py. Usage: python3 docs/paperdiy_figure.py [out.png]   (needs matplotlib and a Japanese font)
"""
import contextlib
import io
import os
import sys

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib import font_manager                                 # noqa: E402
from matplotlib.patches import Circle, PathPatch, Polygon, Rectangle  # noqa: E402
from matplotlib.path import Path                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                              # noqa: E402  (derived positions: SO_X, X_USB, ...)

PANEL_C, PANEL_E = "#ece6d6", "#8f8770"
FEAT_C = "#d9d0b8"
STRAP_C, STRAP_E = "#e8a33d", "#9a6512"
PD_GLASS, PD_PCB, PD_E = "#7d8791", "#3f7f5f", "#2f3a44"
SCREW, SCREW_E = "#5a5f66", "#2b2e33"
RED = "#c0392b"
INK = "#222222"


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        base = os.path.basename(f)
        if "NotoSansCJK-Regular" in base or "NotoSansJP" in base:
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = "Noto Sans CJK JP" if f.endswith(".ttc") else \
                font_manager.FontProperties(fname=f).get_name()
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def cut(mesh, origin, normal, to2d):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return []
    p2, _ = s.to_planar(to_2D=to2d, check=False)
    return p2.polygons_full


XY = np.eye(4)                                                         # (x, y)
YZ = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)   # (y, z)


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1, alpha=1.0):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def screw_top(ax, x, y, r=1.9, z=8):
    ax.add_patch(Circle((x, y), r, fc=SCREW, ec=SCREW_E, lw=0.8, zorder=z))
    ax.plot([x - 1.1, x + 1.1], [y, y], color="#c9cdd2", lw=1.0, zorder=z + 1)
    ax.plot([x, x], [y - 1.1, y + 1.1], color="#c9cdd2", lw=1.0, zorder=z + 1)


def screw_side(ax, yc, z_face, length, head_d=3.8, head_h=1.2, d=2.0):
    """Countersunk screw pointing down (-z), head flush with z_face."""
    tip = z_face - length
    shank = [(yc - d / 2, z_face - head_h), (yc - d / 2, tip + 0.5), (yc, tip), (yc + d / 2, tip + 0.5),
             (yc + d / 2, z_face - head_h)]
    head = [(yc - head_d / 2, z_face), (yc - d / 2, z_face - head_h), (yc + d / 2, z_face - head_h),
            (yc + head_d / 2, z_face)]
    ax.add_patch(Polygon(shank, closed=True, fc=SCREW, ec=SCREW_E, lw=0.8, zorder=8))
    ax.add_patch(Polygon(head, closed=True, fc=SCREW, ec=SCREW_E, lw=0.8, zorder=8))
    for zz in np.arange(tip + 0.9, z_face - head_h - 0.2, 0.45):
        ax.plot([yc - d / 2, yc + d / 2], [zz, zz - 0.25], color="#8b9096", lw=0.5, zorder=9)


def note(ax, xy, txt, xytext, ha="left", fs=10.5, color=INK):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=fs, ha=ha, va="center", color=color,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def Polygon_area(ring):
    c = np.asarray(ring.coords)
    return 0.5 * abs(np.dot(c[:-1, 0], c[1:, 1]) - np.dot(c[1:, 0], c[:-1, 1]))


def back_view(ax, panel, strap):
    for p in cut(panel, [0, 0, 16.5], [0, 0, 1], XY):                   # panel plate with its window
        add_polygon(ax, p, PANEL_C, PANEL_E)
    for p in cut(panel, [0, 0, 18.5], [0, 0, 1], XY):                   # what stands up from the back
        add_polygon(ax, p, FEAT_C, PANEL_E, lw=0.8, z=2)
    x0, x1, hw = B.X_USB, B.X_TOP, B.PD_W / 2
    ax.add_patch(Rectangle((x0, -hw), x1 - x0, 2 * hw, fc=PD_GLASS, ec=PD_E, lw=1.2, alpha=0.88, zorder=3))
    pcb_x1 = B.X_TOP - B.PD_PCB_TOP_FROM_TOP
    ax.add_patch(Rectangle((x0, -hw), pcb_x1 - x0, 2 * hw, fc=PD_PCB, ec=PD_E, lw=1.0, alpha=0.9, zorder=4))
    for p in cut(strap, [0, 0, 24.9], [0, 0, 1], XY):
        add_polygon(ax, p, STRAP_C, STRAP_E, lw=1.2, z=6)
    for p in cut(strap, [0, 0, 21.0], [0, 0, 1], XY):                  # the two legs past the PCB's inner end
        add_polygon(ax, p, "#b5651d", STRAP_E, lw=1.2, z=7)
    if B.STRAP_LEGS:
        x_leg = B.X_TOP - B.PD_PCB_TOP_FROM_TOP + B.STRAP_LEGS["gap"] + B.STRAP_LEGS["t"]
        note(ax, (x_leg, 25.5), "脚：基板の端に当てて、\n基板が回らないようにする", (8.0, 37.0))
    if B.STRAP_RAILS:
        note(ax, (B.STRAP_RAILS["feet_x"][1], -24.75), "レールの足：画面の右側を押さえる", (20.0, -47.5))
    for y in (B.STRAP_POST_Y, -B.STRAP_POST_Y):
        screw_top(ax, B.STRAP_X, y)
    screw_top(ax, B.SO_X, B.SO_Y)
    note(ax, (B.STRAP_X + 2.0, B.STRAP_POST_Y), "M2×8 皿タッピングねじ（柱へ）", (-4.0, 53.0))
    note(ax, (B.STRAP_X + 2.0, -B.STRAP_POST_Y), "M2×8 皿タッピングねじ（柱へ）", (-4.0, -53.0))
    note(ax, (B.SO_X + 2.0, B.SO_Y + 0.6), "M2×4 皿小ねじ（PaperDIY の\nスタンドオフへ）", (6.0, 12.0), color="white")
    note(ax, (B.STRAP_X - 4.0, 20.0), "ストラップ", (-50.0, 46.5))
    note(ax, (x1 - 6.0, hw - 6.0), "PaperDIY（ガラスを下にして\n枠の中に置く）", (36.0, 47.0))
    note(ax, (x1 + 1.6, -10.0), "位置決めの枠", (60.0, -53.0))
    ax.text(x0 + 2.5, B.USB_Y, "← USB-C", color="white", fontsize=9.5, va="center", zorder=7)
    ax.text(x0 + 2.5, hw - 4.0, "基板", color="white", fontsize=9.5, va="center", zorder=7)
    ax.text(77.0, -4.5, "電池枠", color=INK, fontsize=10, ha="center", va="center", zorder=7)
    ax.text(-62.0, -47.5, "↓ 手前（KEY ボタン側）", ha="center", va="center", fontsize=9.5, color="#666")
    holes = [h for p in cut(panel, [0, 0, 16.5], [0, 0, 1], XY) for h in p.interiors
             if Polygon_area(h) < 20.0]
    if holes:
        hx, hy = min((np.asarray(h.coords).mean(axis=0) for h in holes), key=lambda c: c[0] - c[1])
        note(ax, (hx - 1.5, hy + 1.5), "四隅の穴：パネルを蓋に留める M2×8", (-98.0, 53.0))
    ax.set_xlim(-100, 100)
    ax.set_ylim(-58, 58.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("画面パネルの裏（PaperDIY を付けたところ）", fontsize=12.5, color=INK, loc="left")


def section_view(ax, panel, strap):
    xs = B.STRAP_X
    for p in cut(panel, [xs, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, PANEL_C, PANEL_E)
    for p in cut(strap, [xs, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, STRAP_C, STRAP_E, lw=1.0, z=6)
    zb, hw = B.PANEL_Z_BACK, B.PD_W / 2
    pcb_back = zb + 2.4                                                # PCB back 2.4 mm from the screen face
    ax.add_patch(Rectangle((-hw, zb), 2 * hw, 1.4, fc=PD_GLASS, ec=PD_E, lw=1.0, zorder=3))
    ax.add_patch(Rectangle((-hw, zb + 1.4), 2 * hw, pcb_back - zb - 1.4, fc=PD_PCB, ec=PD_E, lw=1.0, zorder=3))
    ax.add_patch(Rectangle((B.SO_Y - B.PD_M2_STANDOFF_OD / 2, pcb_back), B.PD_M2_STANDOFF_OD, B.SO_TOP - pcb_back,
                           fc="#c8b37a", ec="#6d5d2c", lw=1.0, zorder=4))
    for y in (B.STRAP_POST_Y, -B.STRAP_POST_Y):
        screw_side(ax, y, B.STRAP_TOP, B.TAP_SCREW_LEN)
    screw_side(ax, B.SO_Y, B.STRAP_TOP, B.STRAP_SCREW_LEN)
    note(ax, (-B.STRAP_POST_Y + 1.0, B.STRAP_TOP - 4.0), "M2×8 皿タッピングねじ\n（下穴は印刷済み）", (-40.0, 31.0))
    note(ax, (-B.STRAP_POST_Y - 3.2, 21.0), "柱（パネルと一体）", (-59.5, 24.0))
    note(ax, (-hw - 0.8, zb + 0.6), "位置決めの枠（高さ 1 mm）", (-59.5, 12.2))
    note(ax, (-12.0, B.STRAP_TOP - 0.6), "ストラップ（厚さ 2 mm）", (-14.0, 31.0))
    note(ax, (B.SO_Y + 1.1, B.STRAP_TOP - 2.6), f"M2×4 皿小ねじ：PaperDIY に {B.STRAP_ENGAGE:.1f} mm だけ入る\n"
         f"（{B.PD_MAX_THREAD:.0f} mm 以上入れると画面を傷めるので、長くても M2×5 まで）", (6.0, 31.0))
    note(ax, (B.SO_Y - 1.6, 22.0), "スタンドオフ（PaperDIY の M2 ねじ穴）", (-9.0, 11.8), ha="right")
    note(ax, (14.0, zb + 0.7), "PaperDIY の画面（ガラス）", (20.0, 11.8))
    note(ax, (24.0, zb + 1.9), "基板", (34.0, 14.0))
    note(ax, (36.5, 16.0), "画面パネル", (44.0, 11.8))
    ax.text(0, 9.2, "↓ 画面側（表）", ha="center", fontsize=9.5, color="#666")
    ax.set_xlim(-60, 58)
    ax.set_ylim(8, 33.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("断面（ストラップに沿って切ったところ）", fontsize=12.5, color=INK, loc="left")


def main(out):
    use_japanese_font()
    panel = trimesh.load(os.path.join(CAD, "out", "display_panel_paperdiy.stl"))
    strap = trimesh.load(os.path.join(CAD, "out", "paperdiy_strap.stl"))
    fig = plt.figure(figsize=(12.5, 10.2))
    ax_top = fig.add_axes([0.02, 0.33, 0.96, 0.64])
    ax_sec = fig.add_axes([0.02, 0.0, 0.96, 0.31])
    back_view(ax_top, panel, strap)
    section_view(ax_sec, panel, strap)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "paperdiy_mount.png"))
