"""Draw docs/images/panel_snap.png: where the bezel panel snaps into the lid (plan view + section through one snap).

Both views are cut from the built STLs (cad/out); positions come from cad/src/params.py (PANEL_SNAP).
Usage: python3 docs/snap_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
"""
import os
import sys

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib import font_manager                                 # noqa: E402
from matplotlib.patches import PathPatch, Rectangle                 # noqa: E402
from matplotlib.path import Path                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
sys.path.insert(0, os.path.join(CAD, "src"))
from params import KB_CLR, KB_TOP_Z, PANEL_CLR, PANEL_SNAP, PANEL_T, SHELL_WALL, Z_PART  # noqa: E402

PANEL_Z0 = max(KB_TOP_Z + KB_CLR, Z_PART + 0.3)          # as in build.py: the panel's visible face
PANEL_Z1 = PANEL_Z0 + PANEL_T

LID_C, LID_E = "#33508f", "#1d2f57"
PANEL_C, PANEL_E = "#e1d7b9", "#8f8770"
HI = "#d2462f"
INK = "#222222"


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in os.path.basename(f) or "NotoSansJP" in os.path.basename(f):
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
            if f.endswith(".ttc"):
                plt.rcParams["font.family"] = "Noto Sans CJK JP"
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def polygons(mesh, origin, normal, to2d):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    p2, _ = s.to_planar(to_2D=to2d, check=False)
    return p2.polygons_full


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z))


def plan_view(ax, lid, panel):
    xy = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], float)
    zc = (PANEL_Z0 + PANEL_Z1) / 2
    for poly in polygons(lid, [0, 0, zc], [0, 0, 1], xy):
        add_polygon(ax, poly, LID_C, LID_E)
    for poly in polygons(panel, [0, 0, zc], [0, 0, 1], xy):
        add_polygon(ax, poly, PANEL_C, PANEL_E, z=2)
    yb = [float(panel.bounds[0][1]), float(panel.bounds[1][1])]
    for xs, y in ((PANEL_SNAP["x_front"], yb[0]), (PANEL_SNAP["x_back"], yb[1])):
        for x in xs:
            ax.add_patch(Rectangle((x - PANEL_SNAP["len"] / 2 - 1.5, y - 2.5), PANEL_SNAP["len"] + 3, 5.0, fc="none", ec=HI,
                                   lw=2.0, zorder=4))
    ax.annotate(f"突起と溝（手前に {len(PANEL_SNAP['x_front'])} か所）", xy=(PANEL_SNAP["x_front"][-1] + 6, yb[0] - 1),
                xytext=(40, -62), fontsize=11, color=HI, ha="left", arrowprops=dict(arrowstyle="-", color=HI, lw=1.0))
    ax.annotate(f"突起と溝（奥に {len(PANEL_SNAP['x_back'])} か所）", xy=(PANEL_SNAP["x_back"][-1] + 6, yb[1] + 1),
                xytext=(40, 62), fontsize=11, color=HI, ha="left", arrowprops=dict(arrowstyle="-", color=HI, lw=1.0))
    ax.text(-100, -70, "手前（留めツメの側）", fontsize=10, color=INK)
    ax.text(-100, 66, "奥（ヒンジの側）", fontsize=10, color=INK)
    ax.set_xlim(-108, 108)
    ax.set_ylim(-75, 75)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("化粧パネルを裏から見たところ（蓋は紺、パネルの厚さの中ほどで切った形）", fontsize=12, color=INK, pad=8)


def section_view(ax, lid, panel):
    x = PANEL_SNAP["x_front"][-1]
    yz = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
    for poly in polygons(lid, [x, 0, 0], [1, 0, 0], yz):
        add_polygon(ax, poly, LID_C, LID_E)
    for poly in polygons(panel, [x, 0, 0], [1, 0, 0], yz):
        add_polygon(ax, poly, PANEL_C, PANEL_E, z=2)
    y_wall = float(panel.bounds[0][1]) + PANEL_SNAP["bump"] - PANEL_CLR          # the wall's inner face
    g = PANEL_SNAP

    def note(xy, txt, xytext):
        ax.annotate(txt, xy=xy, xytext=xytext, fontsize=10.5, ha="left", va="center", color=INK,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=1))
    peak = PANEL_T / 2
    note((y_wall - 0.1, PANEL_Z0 + peak), f"突起（パネルの縁から {g['bump']:g} mm の山）", (y_wall + 1.5, PANEL_Z0 - 1.1))
    note((y_wall - 0.25, PANEL_Z0 + peak + 0.3), f"溝（深さ {g['h'] - PANEL_CLR + g['clr']:.2f} mm）", (y_wall + 2.5, PANEL_Z1 + 2.3))
    note((y_wall - 0.8, PANEL_Z1 + 3.0), f"蓋の壁（{SHELL_WALL:g} mm）。押し込むと外へたわむ", (y_wall + 1.0, PANEL_Z1 + 3.2))
    note((y_wall + 4.0, PANEL_Z1 - 0.4), "化粧パネル", (y_wall + 5.5, 17.5))
    ax.text(y_wall + 1.5, PANEL_Z0 - 2.0, "↓ 画面側（キーボードの側）", fontsize=9.5, color="#666", va="center")
    ax.set_xlim(y_wall - 2.5, y_wall + 9.5)
    ax.set_ylim(PANEL_Z0 - 2.5, PANEL_Z1 + 3.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"断面（手前の突起の位置 x = {x:g} で切ったところ）", fontsize=12, color=INK, pad=8)


def main(out):
    use_japanese_font()
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    panel = trimesh.load(os.path.join(CAD, "out", "display_panel_kit.stl"))
    fig, (ax_plan, ax_sec) = plt.subplots(1, 2, figsize=(14.0, 5.6), gridspec_kw=dict(width_ratios=[1.6, 1]))
    plan_view(ax_plan, lid, panel)
    section_view(ax_sec, lid, panel)
    fig.tight_layout(w_pad=2.0)
    fig.savefig(out, dpi=160, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "panel_snap.png"))
