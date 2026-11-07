"""Draw docs/images/pushrod_snap.png: the snap-in push-rods (one rod seen from above as it prints, and a horizontal
section through the lid's front wall at the KEY rods). Cut from the built STLs.

Usage: python3 docs/pushrod_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
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
from matplotlib.patches import FancyArrowPatch, PathPatch  # noqa: E402
from matplotlib.path import Path                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                # noqa: E402

LID_C, LID_E = "#33508f", "#1d2f57"
PANEL_C, PANEL_E = "#ece6d6", "#8f8770"
ROD_C, ROD_E = "#d24a3c", "#7d2219"
KEY_C, KEY_E = "#3c8a5a", "#1f4f31"
INK = "#222222"
XY = np.eye(4)


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        base = os.path.basename(f)
        if "NotoSansCJK-Regular" in base or "NotoSansJP" in base:
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = "Noto Sans CJK JP" if f.endswith(".ttc") else \
                font_manager.FontProperties(fname=f).get_name()
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def cut_z(mesh, z):
    s = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if s is None:
        return []
    p2, _ = s.to_planar(to_2D=XY, check=False)
    return p2.polygons_full


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z))


def note(ax, xy, txt, xytext, ha="left", fs=10):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=fs, ha=ha, va="center", color=INK,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def finish(ax, xlim, ylim, title):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12, color=INK, loc="left")


def rod_view(ax):
    """One KEY rod in its own frame (x = 0 at the wall's outer face, inward to the right), cut at its axis."""
    s = B.ROD_SNAP
    length = B.KEY_TIP_Y - B.ROD_GAP + (B.LID_INNER_Y + B.ROD_WALL)
    rod = B.to_t(B.rod_local(length))
    for p in cut_z(rod, 0.0):
        add_polygon(ax, p, ROD_C, ROD_E, lw=1.0, z=3)
    for x in (0.0, B.ROD_WALL):                                       # where the wall will be
        ax.plot([x, x], [-4.2, 4.2], color=LID_E, lw=0.8, ls=(0, (3, 2)), zorder=1)
    ax.text(B.ROD_WALL / 2, -4.7, f"壁（{B.ROD_WALL:g} mm）", fontsize=9, ha="center", va="top", color=LID_E)
    x_c = -s["play"]
    x_root = x_c - s["land"] / 2 + s["slot_len"]
    note(ax, (x_c - s["land"] / 2, B.ROD_HOLE / 2 + s["catch"] - 0.1), "爪（左右 2 か所）", (-6.0, 5.6))
    note(ax, (x_root - 2.0, 0.0), f"切れ目（{s['slot_len']:g} mm）\n爪がすぼまって穴を通る", (2.0, 7.2))
    note(ax, (B.ROD_WALL + B.ROD_COLLAR_T / 2, B.ROD_COLLAR_D / 2 - 0.2), "つば", (8.5, 5.0))
    note(ax, (length - 0.5, -0.8), "KEY ボタンを押す先", (11.0, -6.5))
    ax.text(-2.4, -6.4, "← 外", fontsize=9.5, color="#666", ha="left")
    ax.text(-7.0, -8.0, "平らな面（下）をパネル側に向けて差し込む。外から見ると切れ目が縦になる",
            fontsize=9.5, color=INK, va="top")
    finish(ax, (-7.5, 17.5), (-10.0, 9.5), "① 押し棒（上から見たところ）")


def wall_view(ax, lid, panel, rods, pd):
    """Horizontal section through the lid's front wall at the KEY height, looking down (outside at the bottom)."""
    z = B.KEY_Z
    for p in cut_z(lid, z):
        add_polygon(ax, p, LID_C, LID_E)
    for p in cut_z(panel, z):
        add_polygon(ax, p, PANEL_C, PANEL_E, z=2)
    for p in cut_z(pd, z):
        add_polygon(ax, p, KEY_C, KEY_E, z=2)
    for r in rods:
        for p in cut_z(r, z):
            add_polygon(ax, p, ROD_C, ROD_E, z=3)
    s = B.ROD_SNAP
    y_out, y_in = -(B.LID_INNER_Y + B.ROD_WALL), -B.LID_INNER_Y
    ax.plot([-40, -6], [B.Y_KEYEDGE, B.Y_KEYEDGE], color=KEY_E, lw=0.8, ls=(0, (4, 3)), zorder=1)
    ax.text(-6.3, B.Y_KEYEDGE + 0.5, "PaperDIY の縁", fontsize=9, color=KEY_E, ha="right", va="bottom")
    x0, x1 = B.KEY_X
    note(ax, (x0 + 1.9, y_out - s["play"] - 0.15), "爪が壁の外に掛かる", (-6.0, -50.6), ha="right")
    note(ax, (x0 + 2.4, y_in + B.ROD_COLLAR_T / 2), "つばが壁の内側に当たる", (-6.0, -45.0), ha="right")
    note(ax, (x0 + 2.7, -40.6), "パネルの受け", (-6.0, -40.0), ha="right")
    note(ax, (x0 + 0.5, B.KEY_TIP_Y + 0.6), "KEY ボタン", (-6.0, -33.8), ha="right")
    xd = x1 - 2.9
    ax.annotate("", xy=(xd, y_out), xytext=(xd, y_out - s["play"]),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8, shrinkA=0, shrinkB=0))
    note(ax, (xd, y_out - s["play"] / 2), f"押せる量 {s['play']:g} mm", (-37.0, -49.4), ha="left", fs=9)
    ax.add_patch(FancyArrowPatch((-35.0, -36.2), (-35.0, -43.9), arrowstyle="-|>", mutation_scale=12,
                                 color="#c0392b", lw=1.6, zorder=8))
    ax.text(-40.2, -32.2, "内側から差し込むと\nパチンと留まる", fontsize=9.5, color="#c0392b", va="top")
    ax.text(-39.8, -45.0, "蓋の手前の壁", fontsize=9.5, color="white", va="center")
    ax.text(-39.5, -51.3, "外（手前）", fontsize=9.5, color="#666", va="center")
    finish(ax, (-40.5, -5.5), (-52.5, -30.0), "② 蓋の手前の壁（KEY の高さの断面、上から）")


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    panel = trimesh.load(os.path.join(CAD, "out", "display_panel_paperdiy.stl"))
    rods = [B.to_t(B.build_key_rod(x)) for x in B.KEY_X]
    pd = B.to_t(B.paperdiy_envelope())
    fig = plt.figure(figsize=(13.0, 5.6))
    rod_view(fig.add_axes([0.0, 0.03, 0.46, 0.88]))
    wall_view(fig.add_axes([0.48, 0.03, 0.52, 0.88]), lid, panel, rods, pd)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "pushrod_snap.png"))
