"""Draw docs/images/kit_mount.png: how the PaperDIY Complete Kit sits in the lid. Left: the bezel panel as you see it
with the lid open (front edge up), with the finger slots, the screws and where the USB-C goes in. Right: a section
through the closed case (lid shell, kit, panel, tray). Cut from the built STLs.

Usage: python3 docs/kit_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
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
from matplotlib.patches import Circle, FancyArrowPatch, PathPatch, Polygon as MPoly, Rectangle  # noqa: E402
from matplotlib.path import Path                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                # noqa: E402

LID_C, LID_E = "#33508f", "#1d2f57"
TRAY_C, TRAY_E = "#ece6d6", "#8f8770"
KIT_C, KIT_E = "#c9ccd1", "#5f646b"
PANEL_C, PANEL_E = "#ece6d6", "#8f8770"
SCR_C = "#5a5f66"
RED = "#c0392b"
INK = "#222222"
XY_OPEN = np.array([[1, 0, 0, 0], [0, -1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)   # front edge up
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


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1, ls="-"):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z, ls=ls))


def note(ax, xy, txt, xytext, ha="left", fs=10, color=INK):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=fs, ha=ha, va="center", color=color,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def finish(ax, xlim, ylim, title):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12, color=INK, loc="left")


def inner_view(ax, lid, panel, kit):
    for p in cut(lid, [0, 0, B.PANEL_Z0 + 0.8], [0, 0, 1], XY_OPEN):            # the lid's walls around the panel
        add_polygon(ax, p, LID_C, LID_E)
    for p in cut(kit, [0, 0, B.KIT_Z0 + 3.0], [0, 0, 1], XY_OPEN):             # the kit, seen through the slots
        add_polygon(ax, p, KIT_C, KIT_E, lw=0.6, z=1)
    for p in cut(panel, [0, 0, B.PANEL_Z0 + 0.8], [0, 0, 1], XY_OPEN):
        add_polygon(ax, p, PANEL_C, PANEL_E, lw=0.9, z=2)
    w, h = B.KIT_WIN
    wx = B.KIT_CX + B.KIT_WIN_OFF
    ax.add_patch(Rectangle((wx - w / 2, -h / 2), w, h, fc="#eef0f2", ec=KIT_E, lw=0.6, zorder=3))
    ax.text(wx, 0, "画面", fontsize=12, color="#777", ha="center", va="center", zorder=4)
    for x, y in B.PANEL_SCREWS:
        ax.add_patch(Circle((x, -y), 1.6, fc="white", ec=INK, lw=0.8, zorder=5))
    note(ax, (B.PANEL_SCREWS[1][0] - 1.5, -B.PANEL_SCREWS[1][1] + 1.0), "M2×8 皿タッピングねじ（6 本）", (60.0, 57.0))
    xs = [B.kit_x(d) for cap in B.KIT_KEY_CAPS for d in cap]
    note(ax, ((min(xs) + max(xs)) / 2, B.KIT_W / 2 + 3.0), "KEY1・KEY2 を押す切り欠き", (-40.0, 57.0))
    note(ax, (B.KIT_CX - B.KIT_L / 2 - 2.5, -sum(B.KIT_PWR_CAP_Y) / 2), "電源ボタンを押す切り欠き", (-40.0, -61.0))
    ax.add_patch(FancyArrowPatch((-112.0, -B.KIT_USB_Y), (-101.5, -B.KIT_USB_Y), arrowstyle="-|>", mutation_scale=12,
                                 color=RED, lw=1.4, zorder=8))
    ax.text(-113.0, 52.0, "USB-C：左端の穴から挿す\n（切り欠きから見ながら端子まで）", fontsize=10, color=RED, va="bottom")
    if B.PANEL_USB_SLOT:
        note(ax, (-82.0, -B.KIT_USB_Y - B.PANEL_USB_SLOT["half"] + 1.0), "USB-C プラグの\n切り欠き", (-96.0, 6.0), fs=9.5)
    ax.text(75.0, -63.0, "↓ ヒンジ側", fontsize=9.5, color="#666")
    finish(ax, (-114, 104), (-67, 62), "① 化粧パネル（開いて画面側から見たところ）")


def section_view(ax, lid, panel, tray, kit):
    x = 20.0
    for p in cut(tray, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut(lid, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, LID_C, LID_E)
    for p in cut(kit, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, KIT_C, KIT_E, lw=0.9, z=2)
    for p in cut(panel, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, PANEL_C, PANEL_E, lw=0.9, z=3)
    kb = B.KB_TOP_Z
    ax.add_patch(Rectangle((-40.0, 3.0), 80.0, kb - 3.0, fc="none", ec="#999", lw=0.8, ls=(0, (4, 3)), zorder=1))
    ax.text(0.0, (3.0 + kb) / 2, f"キーボード（厚さ {kb - 3.0:g} mm と仮定）", fontsize=9.5, color="#777", ha="center", va="center")
    ax.text(10.0, B.KIT_Z0 + B.KIT_T / 2, "PaperDIY（ケースごと）", fontsize=9.5, color=INK, ha="center", va="center", zorder=7)
    note(ax, (40.0, B.PANEL_Z0 + B.PANEL_T / 2), f"化粧パネル（{B.PANEL_T:g} mm）", (22.0, 31.5))
    note(ax, (-30.0, B.top_z(-30.0) - B.SHELL_CEIL / 2), f"蓋（壁 {B.SHELL_WALL:g}・天板 {B.SHELL_CEIL:g} mm の中空）", (-64.0, 31.5))
    note(ax, (-45.5, 4.0), "トレイ", (-62.0, -2.0))
    ax.text(-48.0, -6.0, "← 手前", fontsize=9.5, color="#666")
    ax.text(48.0, -6.0, "ヒンジ側 →", fontsize=9.5, color="#666", ha="right")
    finish(ax, (-66, 62), (-8, 35), "② 閉じたときの断面")


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    tray = trimesh.load(os.path.join(CAD, "out", "keyboard_tray.stl"))
    kit = trimesh.load(os.path.join(CAD, "out", "paperdiy_kit_envelope.stl"))
    panel = trimesh.load(os.path.join(CAD, "out", "display_panel_kit.stl"))
    fig = plt.figure(figsize=(14.0, 5.4))
    inner_view(fig.add_axes([0.0, 0.02, 0.52, 0.9]), lid, panel, kit)
    section_view(fig.add_axes([0.53, 0.02, 0.47, 0.9]), lid, panel, tray, kit)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "kit_mount.png"))
