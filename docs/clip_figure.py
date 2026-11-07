"""Draw docs/images/front_clip.png: where the optional front clip goes (front view of the closed case) and how it holds
(section through the clip, cut from the built STLs).

Usage: python3 docs/clip_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
"""
import contextlib
import io
import os
import sys

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib import font_manager                   # noqa: E402
from matplotlib.patches import Circle, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                # noqa: E402

LID_C, LID_E = "#33508f", "#1d2f57"
TRAY_C, TRAY_E = "#ece6d6", "#8f8770"
CLIP_C, CLIP_E = "#e8a33d", "#9a6512"
ROD_C = "#d9d0b8"
RED = "#c0392b"
INK = "#222222"
YZ = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        base = os.path.basename(f)
        if "NotoSansCJK-Regular" in base or "NotoSansJP" in base:
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = "Noto Sans CJK JP" if f.endswith(".ttc") else \
                font_manager.FontProperties(fname=f).get_name()
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def cut_yz(mesh, x):
    s = mesh.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    p2, _ = s.to_planar(to_2D=YZ, check=False)
    return p2.polygons_full


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z))


def note(ax, xy, txt, xytext, ha="left", color=INK, fs=10.5):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=fs, ha=ha, va="center", color=color,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def front_view(ax, clip):
    """Looking at the front face of the closed case (x to the right, z up)."""
    z_part = 8.0                                                   # parting line on the front face
    ax.add_patch(Rectangle((-101, z_part), 202, 30 - z_part, fc=LID_C, ec=LID_E, lw=1.2, zorder=1))
    ax.add_patch(Rectangle((-101, 0), 202, z_part, fc=TRAY_C, ec=TRAY_E, lw=1.2, zorder=1))
    for z in (3.0, 27.0):                                         # edges of the 3 mm chamfers
        ax.plot([-101, 101], [z, z], color="#ffffff" if z > z_part else TRAY_E, lw=0.6, alpha=0.6, zorder=2)
    for x in B.KEY_X:
        ax.add_patch(Circle((x, B.KEY_Z), B.ROD_D / 2, fc=ROD_C, ec=INK, lw=0.8, zorder=3))
    lo, hi = clip.bounds
    ax.add_patch(Rectangle((lo[0], lo[2]), hi[0] - lo[0], hi[2] - lo[2], fc=CLIP_C, ec=CLIP_E, lw=1.4, zorder=4))
    x0, x1 = min(B.KEY_X) - 6, max(B.KEY_X) + 6
    ax.add_patch(Rectangle((x0, -4), x1 - x0, 38, fc="none", ec=RED, lw=1.2, ls=(0, (4, 3)), zorder=5))
    ax.text((x0 + x1) / 2, 37.0, "ここは避ける\n（KEY の押し棒）", color=RED, fontsize=10.5, ha="center", va="bottom")
    note(ax, ((lo[0] + hi[0]) / 2, hi[2]), "留めクリップ（例：中央の少し右）", (40.0, 41.0))
    ax.text(-99, 18.5, "蓋", color="white", fontsize=12, va="center")
    ax.text(-99, 4.0, "トレイ", color=INK, fontsize=11, va="center")
    ax.set_xlim(-106, 106)
    ax.set_ylim(-8, 47)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("閉じた状態を手前から見たところ", fontsize=12.5, color=INK, loc="left")


def section_view(ax, lid, tray, clip):
    xs = B.CLIP_X
    for p in cut_yz(tray, xs):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut_yz(lid, xs):
        add_polygon(ax, p, LID_C, LID_E)
    for p in cut_yz(clip, xs):
        add_polygon(ax, p, CLIP_C, CLIP_E, lw=1.2, z=5)
    lo, hi = clip.bounds
    y_ridge = hi[1] - 2.0
    label = f"出っ張り（2 か所）\n{B.CLIP_BUMP:g} mm 押しつけてずれを防ぐ"
    note(ax, (y_ridge + 0.2, 29.8), label, (-41.5, 14.5))
    note(ax, (y_ridge + 0.2, 0.2), "", (-41.5, 14.5))
    note(ax, (lo[1] + 0.8, 8.0), f"留めクリップ\n（厚さ {B.CLIP_T:g} mm・幅 {B.CLIP_W:g} mm）", (-66.0, -5.0))
    ax.text(-41.5, 23.0, "蓋", color=LID_E, fontsize=12, va="center")
    ax.text(-41.5, 5.6, "トレイ", color="#6f6852", fontsize=11, va="center")
    ax.text(-16.5, -6.8, "奥（ヒンジ側）→", fontsize=9.5, color="#666", ha="right")
    ax.set_xlim(-67, -16)
    ax.set_ylim(-9.5, 43)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("断面（クリップの位置）", fontsize=12.5, color=INK, loc="left")


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    tray = trimesh.load(os.path.join(CAD, "out", "keyboard_tray.stl"))
    clip = trimesh.load(os.path.join(CAD, "out", "front_clip.stl"))
    fig = plt.figure(figsize=(13.0, 4.8))
    ax_f = fig.add_axes([0.01, 0.02, 0.62, 0.90])
    ax_s = fig.add_axes([0.65, 0.02, 0.34, 0.90])
    front_view(ax_f, clip)
    section_view(ax_s, lid, tray, clip)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "front_clip.png"))
