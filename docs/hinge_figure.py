"""Draw docs/images/hinge_screws.png: how the hinges are screwed on (back view + section through one pair of screws).

The section is cut from the built STLs (cad/out), the hinge, screws and covers are drawn from cad/src/params.py.
Usage: python3 docs/hinge_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
"""
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
from params import (COVER_R0, COVER_T, HINGE_AXIS_Y, HINGE_BARREL_D, HINGE_HOLE_OFF, HINGE_HOLE_PITCH_X,  # noqa: E402
                    HINGE_LEAF_T, HINGE_LEN, HINGE_WIDTH, HINGE_X, HOUSING_HALF, TAP_SCREW_LEN, Y_BACK, Z_PART)

LID_C, LID_E = "#33508f", "#1d2f57"
TRAY_C, TRAY_E = "#ece6d6", "#8f8770"
METAL, METAL_E, BARREL = "#b9c0c8", "#5b636c", "#9aa2ab"
SCREW, SCREW_E = "#5a5f66", "#2b2e33"
INK = "#222222"
COVER_H_LID, COVER_H_TRAY = 10.3, 8.9          # cover heights (cad/README.md, outputs table)


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in os.path.basename(f) or "NotoSansJP" in os.path.basename(f):
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
            if f.endswith(".ttc"):
                plt.rcParams["font.family"] = "Noto Sans CJK JP"
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def section(mesh, x):
    """Polygons of the cut at plane x, in (y, z)."""
    s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    to_yz = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
    p2, _ = s.to_planar(to_2D=to_yz, check=False)
    return p2.polygons_full


def add_polygon(ax, poly, fc, ec):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=1.0, zorder=1))


def screw_side(ax, zc, y_face=Y_BACK, length=TAP_SCREW_LEN, head_d=3.8, head_h=1.2, d=2.0):
    """Countersunk screw along -y, head flush with the leaf face."""
    tip = y_face - length
    shank = [(y_face - head_h, zc + d / 2), (tip + 0.6, zc + d / 2), (tip, zc), (tip + 0.6, zc - d / 2),
             (y_face - head_h, zc - d / 2)]
    head = [(y_face, zc + head_d / 2), (y_face - head_h, zc + d / 2), (y_face - head_h, zc - d / 2),
            (y_face, zc - head_d / 2)]
    ax.add_patch(Polygon(shank, closed=True, fc=SCREW, ec=SCREW_E, lw=0.8, zorder=6))
    ax.add_patch(Polygon(head, closed=True, fc=SCREW, ec=SCREW_E, lw=0.8, zorder=6))
    for yy in np.arange(tip + 1.0, y_face - head_h - 0.2, 0.45):
        ax.plot([yy, yy - 0.25], [zc + d / 2, zc - d / 2], color="#8b9096", lw=0.5, zorder=7)


def back_view(ax):
    hw = HOUSING_HALF
    ax.add_patch(Rectangle((-hw - 9, Z_PART), 2 * hw + 18, 30 - Z_PART, fc=LID_C, ec=LID_E, lw=1.2, zorder=1))
    ax.add_patch(Rectangle((-hw - 9, 0), 2 * hw + 18, Z_PART, fc=TRAY_C, ec=TRAY_E, lw=1.2, zorder=1))
    ax.plot([-hw - 9, hw + 9], [Z_PART, Z_PART], color=INK, lw=0.8, ls=(0, (4, 3)), zorder=2)
    ax.add_patch(Rectangle((-HINGE_LEN / 2, Z_PART - HINGE_WIDTH / 2), HINGE_LEN, HINGE_WIDTH,
                           fc=METAL, ec=METAL_E, lw=1.2, zorder=3))
    ax.add_patch(Rectangle((-HINGE_LEN / 2, Z_PART - HINGE_BARREL_D / 2), HINGE_LEN, HINGE_BARREL_D,
                           fc=BARREL, ec=METAL_E, lw=1.0, zorder=4))
    for zc in (Z_PART + HINGE_HOLE_OFF, Z_PART - HINGE_HOLE_OFF):
        for dx in (-HINGE_HOLE_PITCH_X / 2, HINGE_HOLE_PITCH_X / 2):
            ax.add_patch(Circle((dx, zc), 1.9, fc=SCREW, ec=SCREW_E, lw=0.8, zorder=5))
            ax.plot([dx - 1.1, dx + 1.1], [zc, zc], color="#c9cdd2", lw=1.0, zorder=6)
            ax.plot([dx, dx], [zc - 1.1, zc + 1.1], color="#c9cdd2", lw=1.0, zorder=6)
    for zc, txt in ((Z_PART + HINGE_HOLE_OFF, "蓋側に 2 本"), (Z_PART - HINGE_HOLE_OFF, "トレイ側に 2 本")):
        ax.annotate(txt, xy=(HINGE_HOLE_PITCH_X / 2 + 1.9, zc), xytext=(hw + 11, zc), color=INK, fontsize=11,
                    ha="left", va="center", arrowprops=dict(arrowstyle="-", color=INK, lw=0.9))
    ax.text(0, Z_PART, "筒（回る軸）", fontsize=9.5, ha="center", va="center", color=INK, zorder=7)
    ax.text(-hw - 7.5, 28.2, "蓋", color="white", fontsize=12, va="center")
    ax.text(-hw - 7.5, 1.6, "トレイ", color=INK, fontsize=12, va="center")
    ax.annotate("", xy=(-HINGE_LEN / 2, -2.6), xytext=(HINGE_LEN / 2, -2.6),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
    ax.text(0, -4.1, f"ヒンジ {HINGE_LEN:.0f} mm（ねじの間隔 {HINGE_HOLE_PITCH_X:.0f} mm）", ha="center", va="top",
            fontsize=9.5, color=INK)
    ax.set_xlim(-hw - 10, hw + 27)
    ax.set_ylim(-7, 31.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("背面から見たところ（カバーを外した状態）", fontsize=12.5, color=INK, pad=8)


def section_view(ax, lid, tray):
    xs = HINGE_X - HINGE_HOLE_PITCH_X / 2                 # through one pair of screws
    for poly in section(tray, xs):
        add_polygon(ax, poly, TRAY_C, TRAY_E)
    for poly in section(lid, xs):
        add_polygon(ax, poly, LID_C, LID_E)
    ax.add_patch(Rectangle((Y_BACK - HINGE_LEAF_T, Z_PART - HINGE_WIDTH / 2), HINGE_LEAF_T, HINGE_WIDTH,
                           fc=METAL, ec=METAL_E, lw=1.0, zorder=4))
    ax.add_patch(Circle((HINGE_AXIS_Y, Z_PART), HINGE_BARREL_D / 2, fc=BARREL, ec=METAL_E, lw=1.0, zorder=5))
    ax.add_patch(Rectangle((Y_BACK, Z_PART + COVER_R0), COVER_T, COVER_H_LID, fc=LID_C, ec=LID_E, lw=0.9, zorder=5))
    ax.add_patch(Rectangle((Y_BACK, Z_PART - COVER_R0 - COVER_H_TRAY), COVER_T, COVER_H_TRAY,
                           fc=TRAY_C, ec=TRAY_E, lw=0.9, zorder=5))
    for zc in (Z_PART + HINGE_HOLE_OFF, Z_PART - HINGE_HOLE_OFF):
        screw_side(ax, zc)
    depth = TAP_SCREW_LEN - HINGE_LEAF_T
    skin = Y_BACK - HINGE_LEAF_T - depth - 43.5           # 43.5 = inner face of the back wall

    def note(xy, txt, xytext):
        ax.annotate(txt, xy=xy, xytext=xytext, fontsize=10.5, ha="left", va="center", color=INK,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=1))
    note((46.0, Z_PART - HINGE_HOLE_OFF - 0.9),
         f"M2×{TAP_SCREW_LEN:.0f} 皿タッピングねじ（下穴 Ø1.8 は印刷済み）\n"
         f"ねじ先は内側の面の {skin:.1f} mm 手前で止まる", (34.8, -4.6))
    note((Y_BACK - 1.0, Z_PART - 11.6), "ヒンジの板（溝に面一）", (57.2, -1.2))
    note((HINGE_AXIS_Y + 2.3, Z_PART + 1.5), "筒", (58.5, 16.5))
    note((Y_BACK + 0.6, Z_PART + COVER_R0 + 8.8), f"カバー（{COVER_T:.0f} mm・接着）", (57.2, 27.0))
    ax.annotate("", xy=(Y_BACK - 9.5, 31.6), xytext=(Y_BACK, 31.6), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
    ax.text(Y_BACK - 4.75, 32.4, "ヒンジ受け（壁の厚い部分）9.5 mm", ha="center", va="bottom", fontsize=10.5, color=INK)
    ax.text(36.0, 19.0, "蓋", color=LID_E, fontsize=12, va="center")
    ax.text(36.0, 7.0, "トレイ", color="#6f6852", fontsize=12, va="center")
    ax.text(35.0, 13.0, "← 内側", fontsize=9.5, color="#666", va="center")
    ax.text(66.8, 13.0, "外（背面）→", fontsize=9.5, color="#666", va="center", ha="right")
    ax.set_xlim(34.5, 67)
    ax.set_ylim(-8.5, 35.5)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("断面（ねじの位置で切ったところ）", fontsize=12.5, color=INK, pad=8)


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    tray = trimesh.load(os.path.join(CAD, "out", "keyboard_tray.stl"))
    fig, (ax_back, ax_sec) = plt.subplots(1, 2, figsize=(12.5, 6.2), gridspec_kw=dict(width_ratios=[1, 1.08]))
    back_view(ax_back)
    section_view(ax_sec, lid, tray)
    fig.tight_layout(w_pad=2.5)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "hinge_screws.png"))
