"""Draw docs/images/latch.png: the snap tab that keeps the closed lid shut (front view and a section through it,
closed). Cut from the built STLs; numbers from cad/src/params.py.

Usage: python3 docs/latch_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
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
from matplotlib.patches import FancyArrowPatch, PathPatch, Rectangle  # noqa: E402
from matplotlib.path import Path                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                # noqa: E402

LID_C, LID_E = "#33508f", "#1d2f57"
TRAY_C, TRAY_E = "#ece6d6", "#8f8770"
RED = "#c0392b"
INK = "#222222"
XZ = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)
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


def cut(mesh, origin, normal, to2d):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return []
    p2, _ = s.to_planar(to_2D=to2d, check=False)
    return p2.polygons_full


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z))


def note(ax, xy, txt, xytext, ha="left", fs=10, color=INK):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=fs, ha=ha, va="center", color=color,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def finish(ax, xlim, ylim, title):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12, color=INK, loc="left")


def front_view(ax, lid, tray):
    """The front face just behind its surface, looking at it from the front (x to the right, z up)."""
    y = -B.BACK_OLD_Y + 0.3
    for p in cut(tray, [0, y, 0], [0, 1, 0], XZ):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut(lid, [0, y, 0], [0, 1, 0], XZ):
        add_polygon(ax, p, LID_C, LID_E)
    l = B.LATCH
    zf = B.under_z(-B.BACK_OLD_Y)
    g = l["flex"]
    zr = B.top_z(-B.BACK_OLD_Y + B.SHELL_WALL) - B.SHELL_CEIL - g["top"]
    ax.add_patch(Rectangle((g["x0"], zf), g["x1"] - g["x0"], zr - zf, fill=False, ec="white", lw=1.2, ls=(0, (4, 3)),
                           zorder=6))
    note(ax, (l["x"] + l["w"] / 2 - 2.0, zf - l["below"] + 1.0), f"ツメ（幅 {l['w']:g} mm、壁と一体、切れ目なし）", (16.0, 1.0))
    note(ax, (g["x1"] - 0.5, zr - 2.0), f"点線の帯：壁を内側から {g['t']:g} mm に薄くしてあり、\nここが板としてたわむ（外からは見えない）",
         (22.0, 17.5))
    ax.text(-27.0, zf + 5.0, "蓋", color="white", fontsize=11, va="center")
    ax.text(-27.0, zf - 4.0, "トレイ", color=INK, fontsize=10.5, va="center")
    finish(ax, (-28, 40), (-1, 23), "① 閉じた状態を手前から見たところ")


def section_view(ax, lid, tray):
    for p in cut(tray, [B.LATCH["x"], 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut(lid, [B.LATCH["x"], 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, LID_C, LID_E)
    l = B.LATCH
    zf = B.under_z(-B.BACK_OLD_Y)
    zb = zf - l["bump_at"]
    yt = -B.BACK_OLD_Y + l["t"]
    note(ax, (yt + 0.1, zb - 0.2), f"出っ張り {l['bump']:g} mm が\nトレイの溝に入る", (-64.5, zb - 3.0))
    g = l["flex"]
    note(ax, (-B.BACK_OLD_Y + g["t"] / 2, zf + 7.0), f"壁（ここだけ {g['t']:g} mm）が\n外へたわむ", (-50.0, zf + 11.0), ha="right")
    ax.add_patch(FancyArrowPatch((-49.5, zf - 1.0), (-49.5, zf + 4.0), arrowstyle="-|>", mutation_scale=11,
                                 color=RED, lw=1.4, zorder=8))
    ax.text(-50.0, zf + 4.8, "蓋の手前を持ち上げると外れる", color=RED, fontsize=9.5, ha="right", va="bottom")
    ax.text(-42.0, 1.2, "トレイ", color="#6f6852", fontsize=10.5)
    ax.text(-40.0, zf + 13.0, "蓋", color="white", fontsize=11)
    ax.text(-37.5, 0.0, "奥 →", fontsize=9.5, color="#666", ha="right")
    finish(ax, (-66, -36), (-1, 23), "② 断面（ツメの真ん中）")


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    tray = trimesh.load(os.path.join(CAD, "out", "keyboard_tray.stl"))
    fig = plt.figure(figsize=(13.0, 4.6))
    front_view(fig.add_axes([0.0, 0.03, 0.55, 0.88]), lid, tray)
    section_view(fig.add_axes([0.57, 0.03, 0.43, 0.88]), lid, tray)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "latch.png"))
