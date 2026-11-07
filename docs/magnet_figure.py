"""Draw docs/images/magnet_catch.png: the retrofit magnetic catch (jig on the tray's front-left corner, drilling section,
closed section with the magnets). Cut from the built STLs; magnets and drill drawn from cad/src/params.py.

Usage: python3 docs/magnet_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
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
JIG_C, JIG_E = "#7fb3a0", "#2f6b55"
MAG_C, MAG_E = "#5a5f66", "#2b2e33"
GLUE = "#e8c26a"
INK = "#222222"
XY = np.eye(4)
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


def add_polygon(ax, poly, fc, ec, lw=1.0, z=1, alpha=1.0):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))


def note(ax, xy, txt, xytext, ha="left", fs=10):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=fs, ha=ha, va="center", color=INK,
                arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def finish(ax, xlim, ylim, title):
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title, fontsize=12, color=INK, loc="left")


def top_view(ax, tray, jig):
    for p in cut(tray, [0, 0, 6.0], [0, 0, 1], XY):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for z in (12.0, 6.0):                                          # roof, then fingers and fence
        for p in cut(jig, [0, 0, z], [0, 0, 1], XY):
            add_polygon(ax, p, JIG_C, JIG_E, lw=1.0, z=3, alpha=0.85)
    m = B.MAGNETS
    xe = -(B.LID_INNER_X + 3.0)
    for d in m["from_end"]:
        ax.add_patch(Circle((xe + d, m["y"]), B.MAG_JIG["guide_d"] / 2, fc="white", ec=INK, lw=0.8, zorder=5))
        ax.annotate("", xy=(xe, -51.5 + (0 if d < 30 else -2.6)), xytext=(xe + d, -51.5 + (0 if d < 30 else -2.6)),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
        ax.text(xe + d / 2, -51.0 + (0 if d < 30 else -2.6), f"{d:.0f} mm", fontsize=8.5, ha="center", va="bottom")
    note(ax, (xe - 1.0, -34.0), "端の面に当てる", (-104.0, -22.0))
    note(ax, (-60.0, -45.0), "前の壁をまたいで載せる", (-80.0, -22.0))
    note(ax, (xe + 57 + 1.0, m["y"] + 0.8), "ガイド穴 Ø2", (-48.0, -22.0))
    finish(ax, (-107, -32), (-58, -18), "① トレイの角にジグを当てる（上から見たところ）")


def drill_view(ax, tray, jig):
    x = -(B.LID_INNER_X + 3.0) + B.MAGNETS["from_end"][1]
    for p in cut(tray, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut(jig, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, JIG_C, JIG_E, lw=1.0, z=3)
    m = B.MAGNETS
    zl = m["land_z"]
    tip = zl - m["depth"]
    ax.add_patch(Rectangle((m["y"] - m["d"] / 2, tip), m["d"], 24.0 - tip, fc="#b9c0c8", ec="#5b636c", lw=0.9, zorder=4))
    flag = tip + B.MAG_JIG["h"] + m["depth"]
    ax.add_patch(Rectangle((m["y"] - 2.6, flag), 5.2, 1.4, fc="#f2d36b", ec="#9a7d12", lw=0.8, zorder=5))
    note(ax, (m["y"] + 2.6, flag + 0.7), f"テープ：刃先から {B.MAG_JIG['h'] + m['depth']:.0f} mm\n（ここで止める）", (-38.5, flag + 0.7))
    note(ax, (m["y"] + 1.0, tip + 0.5), f"穴 Ø{m['d']:g}・深さ {m['depth']:g} mm", (-38.5, 2.0))
    note(ax, (m["y"] - 1.6, 15.0), "ジグ", (-53.0, 19.0), ha="left")
    ax.text(-41.0, 5.0, "トレイ", fontsize=9.5, color="#6f6852")
    finish(ax, (-54, -27), (-1, 26), "② ガイドに沿って穴をあける")


def closed_view(ax, lid, tray):
    x = -(B.LID_INNER_X + 3.0) + B.MAGNETS["from_end"][1]
    for p in cut(tray, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, TRAY_C, TRAY_E)
    for p in cut(lid, [x, 0, 0], [1, 0, 0], YZ):
        add_polygon(ax, p, LID_C, LID_E)
    m = B.MAGNETS
    zl = m["land_z"]
    y0 = m["y"] - m["d"] / 2
    for z0, z1, mz0, mz1 in ((zl - m["depth"], zl, zl - m["l"], zl), (zl - 0.05, zl - 0.05 + m["depth"], zl - 0.05, zl - 0.05 + m["l"])):
        ax.add_patch(Rectangle((y0, z0), m["d"], z1 - z0, fc=GLUE, ec="none", zorder=4))
        ax.add_patch(Rectangle((y0, mz0), m["d"], mz1 - mz0, fc=MAG_C, ec=MAG_E, lw=0.9, zorder=5))
    note(ax, (y0 + m["d"], zl + 1.8), f"磁石 Ø{m['d']:g}×{m['l']:g} mm（蓋側）", (-40.0, 15.5))
    note(ax, (y0 + m["d"], zl - 1.8), "磁石（トレイ側）：面一に", (-40.0, 1.0))
    note(ax, (y0 + m["d"] / 2, zl + m["depth"] - 0.4), "奥はエポキシ", (-40.0, 20.5))
    ax.text(-38.0, 24.0, "蓋", fontsize=10, color=LID_E)
    ax.text(-38.0, 5.0, "トレイ", fontsize=9.5, color="#6f6852")
    finish(ax, (-50, -20), (-1, 29), "③ 閉じると磁石が吸い付く")


def main(out):
    use_japanese_font()
    tray = trimesh.load(os.path.join(CAD, "out", "keyboard_tray.stl"))
    lid = trimesh.load(os.path.join(CAD, "out", "display_lid_usbc.stl"))
    jig = trimesh.load(os.path.join(CAD, "out", "magnet_jig_L.stl"))
    fig = plt.figure(figsize=(14.0, 5.2))
    top_view(fig.add_axes([0.0, 0.03, 0.43, 0.90]), tray, jig)
    drill_view(fig.add_axes([0.45, 0.03, 0.27, 0.90]), tray, jig)
    closed_view(fig.add_axes([0.73, 0.03, 0.27, 0.90]), lid, tray)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "magnet_catch.png"))
