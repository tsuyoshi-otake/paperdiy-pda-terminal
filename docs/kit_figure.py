"""Draw docs/images/kit_mount.png: how the PaperDIY Complete Kit sits in the lid. Left: the lid's inner face as you
see it with the lid open (front edge up), cut through the pocket, with the finger notches and the USB-C channel.
Right: a section through the kit's screw, closed on the tray. Cut from the built STLs.

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
from matplotlib.patches import Circle, PathPatch, Polygon as MPoly, Rectangle  # noqa: E402
from matplotlib.path import Path                      # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
with contextlib.redirect_stdout(io.StringIO()):
    import build as B                                # noqa: E402

LID_C, LID_E = "#33508f", "#1d2f57"
TRAY_C, TRAY_E = "#ece6d6", "#8f8770"
KIT_C, KIT_E = "#c9ccd1", "#5f646b"
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


def inner_view(ax, lid, kit):
    z = B.KIT_Z0 + 0.6                                   # just inside the pocket, notches and channel
    for p in cut(lid, [0, 0, z], [0, 0, 1], XY_OPEN):
        add_polygon(ax, p, LID_C, LID_E)
    for p in cut(kit, [0, 0, z + 2.0], [0, 0, 1], XY_OPEN):
        add_polygon(ax, p, KIT_C, KIT_E, lw=0.9, z=2)
    w, h = B.KIT_WIN
    wx = B.KIT_CX + B.KIT_WIN_OFF
    ax.add_patch(Rectangle((wx - w / 2, -h / 2), w, h, fc="#eef0f2", ec=KIT_E, lw=0.6, zorder=3))
    ax.text(wx, 0, "画面", fontsize=12, color="#777", ha="center", va="center", zorder=4)
    sx = B.kit_x(B.KIT_SCREW_D)
    ax.add_patch(Circle((sx, 0.0), 1.2, fc="none", ec=RED, lw=1.0, ls=(0, (2, 1.5)), zorder=5))
    note(ax, (sx + 1.0, -1.0), "ねじ 1 本（裏から M2×4）", (-30.0, -22.0), color=RED)
    xs = [B.kit_x(d) for cap in B.KIT_KEY_CAPS for d in cap]
    note(ax, ((min(xs) + max(xs)) / 2, -B.KIT_Y0 + 3.5), "KEY1・KEY2 の切り欠き", (-26.0, 57.0))
    note(ax, (B.KIT_X0 - 3.5, -sum(B.KIT_PWR_CAP_Y) / 2), "電源ボタンの切り欠き", (-104.0, -61.0))
    note(ax, (-92.0, -B.KIT_USB_Y), "USB-C ケーブルの溝（左端から挿す）", (-104.0, 57.0))
    note(ax, (B.LATCH["x"] + 2.0, B.BACK_OLD_Y - 1.0), "留めツメ（閉じるとパチンと留まる）", (24.0, 57.0))
    ax.text(60.0, -63.0, "↓ ヒンジ側", fontsize=9.5, color="#666")
    finish(ax, (-106, 104), (-67, 62), "① 蓋の内側（開いて画面側から見たところ）")


def section_view(ax, lid, tray, kit):
    x = B.kit_x(B.KIT_SCREW_D)
    for p in cut(tray, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut(lid, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, LID_C, LID_E)
    for p in cut(kit, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, KIT_C, KIT_E, lw=0.9, z=2)
    z1 = B.KIT_Z1
    seat = min(z1 + B.KIT_SCREW_SEAT, B.top_z(0.0))
    tip = seat + 1.2 - B.STRAP_SCREW_LEN
    ax.add_patch(MPoly([(-1.9, seat), (1.9, seat), (1.0, seat - 1.2), (-1.0, seat - 1.2)], closed=True,
                       fc=SCR_C, ec="#2b2e33", lw=0.8, zorder=6))
    ax.add_patch(Rectangle((-1.0, tip), 2.0, seat - 1.2 - tip, fc=SCR_C, ec="#2b2e33", lw=0.8, zorder=6))
    kb = B.KB_TOP_Z
    ax.add_patch(Rectangle((-40.0, 3.0), 80.0, kb - 3.0, fc="none", ec="#999", lw=0.8, ls=(0, (4, 3)), zorder=1))
    ax.text(0.0, (3.0 + kb) / 2, f"キーボード（高さ {kb - 3.0:g} mm と仮定）", fontsize=9.5, color="#777", ha="center", va="center")
    note(ax, (1.9, seat - 0.4), f"M2×4 皿小ねじ（キットに {B.STRAP_SCREW_LEN - (seat - z1) - B.KIT_GAP:.1f} mm 入る）", (-30.0, 31.0))
    ax.text(14.0, B.KIT_Z0 + B.KIT_T / 2, "PaperDIY（ケースごと）", fontsize=9.5, color=INK, ha="center", va="center", zorder=7)
    note(ax, (-45.0, B.top_z(-45.0) - 2.0), "蓋", (-62.0, 27.0))
    note(ax, (-45.5, 4.0), "トレイ", (-62.0, -2.0))
    ax.text(-48.0, -6.0, "← 手前", fontsize=9.5, color="#666")
    ax.text(48.0, -6.0, "ヒンジ側 →", fontsize=9.5, color="#666", ha="right")
    finish(ax, (-66, 62), (-8, 33), "② 閉じたときの断面（ねじの位置）")


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    tray = trimesh.load(os.path.join(CAD, "out", "keyboard_tray.stl"))
    kit = trimesh.load(os.path.join(CAD, "out", "paperdiy_kit_envelope.stl"))
    fig = plt.figure(figsize=(14.0, 5.4))
    inner_view(fig.add_axes([0.0, 0.02, 0.52, 0.9]), lid, kit)
    section_view(fig.add_axes([0.53, 0.02, 0.47, 0.9]), lid, tray, kit)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "kit_mount.png"))
