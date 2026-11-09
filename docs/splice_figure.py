"""Draw docs/images/splice_plates.png: where the splice plates go on the A1 mini split pieces (tray, lid, panel), seen
from the hidden side, and a section through the tray's seam.

The views are cut from the built STLs (cad/out/split); positions come from cad/src/params.py (SPLICE, SPLIT_X_*).
Usage: python3 docs/splice_figure.py [out.png]   (needs matplotlib and a Japanese font such as Noto Sans CJK JP)
"""
import glob
import json
import os
import sys

import numpy as np
import trimesh
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                                     # noqa: E402
from matplotlib import font_manager                                 # noqa: E402
from matplotlib.patches import PathPatch                            # noqa: E402
from matplotlib.path import Path                                    # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.path.join(HERE, "..", "cad")
OUT = os.path.join(CAD, "out")
sys.path.insert(0, os.path.join(CAD, "src"))
from params import SPLICE, SPLIT_X_LID, SPLIT_X_PANEL, SPLIT_X_TRAY, TRAY_FLOOR  # noqa: E402

A_C, A_E = "#9fb3d9", "#33508f"
B_C, B_E = "#d9d9d9", "#777777"
P_C, P_E = "#e0603f", "#8f2a12"
INK = "#222222"
XY = np.eye(4)


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        if "NotoSansCJK-Regular" in os.path.basename(f) or "NotoSansJP" in os.path.basename(f):
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = font_manager.FontProperties(fname=f).get_name()
            if f.endswith(".ttc"):
                plt.rcParams["font.family"] = "Noto Sans CJK JP"
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def add_polygon(ax, poly, fc, ec, lw=0.8, z=1):
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
    ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, zorder=z))


def section(mesh, origin, normal, to2d):
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return []
    p2, _ = s.to_planar(to_2D=to2d, check=False)
    return p2.polygons_full


def load(name):
    return trimesh.load(os.path.join(OUT, "split", name))


def plan_view(ax, kind, X, a, b, rot=None):
    plates = [trimesh.load(f) for f in sorted(glob.glob(os.path.join(OUT, "split", "splice", f"{kind}_splice_*.stl")))]
    meshes = [a, b] + plates
    if rot is not None:                          # lid: turn the sloping ceiling level, then cut parallel to it
        for m in meshes:
            m.apply_transform(rot)
    zc = float(np.mean([p.bounds[:, 2].mean() for p in plates]))
    for mesh, fc, ec, z in ((a, A_C, A_E, 1), (b, B_C, B_E, 1)):
        for poly in section(mesh, [0, 0, zc], [0, 0, 1], XY):
            add_polygon(ax, poly, fc, ec, z=z)
    for p in plates:
        for poly in section(p, [0, 0, zc], [0, 0, 1], XY):
            add_polygon(ax, poly, P_C, P_E, lw=1.0, z=3)
    ax.axvline(X, color=INK, lw=0.8, ls=(0, (4, 3)), zorder=4)
    g = SPLICE[kind]
    ax.text(X + g["x0"] - 1.0, -56.0, "A", fontsize=12, color=A_E, ha="right", weight="bold")
    ax.text(X + g["x1"] + 1.0, -56.0, "B", fontsize=12, color="#555", ha="left", weight="bold")
    ax.set_xlim(-103.0, -55.0)
    ax.set_ylim(-60.0, 58.0)
    ax.set_aspect("equal")
    ax.axis("off")


def seam_section(ax):
    y = 12.5                                     # a section across the tray's seam
    xz = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
    a, b = load("tray_A_left.stl"), load("tray_B_main.stl")
    plate = trimesh.load(os.path.join(OUT, "split", "splice", "tray_splice_1.stl"))
    for mesh, fc, ec, z in ((a, A_C, A_E, 1), (b, B_C, B_E, 1), (plate, P_C, P_E, 3)):
        for poly in section(mesh, [0, y, 0], [0, 1, 0], xz):
            add_polygon(ax, poly, fc, ec, lw=1.0, z=z)
    X, g = SPLIT_X_TRAY, SPLICE["tray"]
    t = g["t"]

    def note(xy, txt, xytext):
        ax.annotate(txt, xy=xy, xytext=xytext, fontsize=10.5, ha="left", va="center", color=INK,
                    arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkA=2, shrinkB=1))
    note((X + g["x1"] - 3.0, TRAY_FLOOR - t / 2), f"継ぎ板（厚さ {t:g} mm）。床の上面と面一", (X + g["x1"] + 2.0, TRAY_FLOOR + 1.6))
    note((X - 0.05, TRAY_FLOOR - t - 0.3), "A と B の継ぎ目（まっすぐ突き合わせ）", (X + 3.0, -1.1))
    ax.text(X + g["x0"] - 9.0, TRAY_FLOOR + 1.6, "↑ キーボードの側（隠れる面）", fontsize=9.5, color="#666", va="center")
    ax.text(X + g["x0"] - 9.0, -1.1, "↓ 机に付く面", fontsize=9.5, color="#666", va="center")
    ax.set_xlim(X + g["x0"] - 10.0, X + g["x1"] + 22.0)
    ax.set_ylim(-1.8, TRAY_FLOOR + 2.4)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"断面（トレイの床、y = {y:g} で切ったところ。縦横同じ縮尺）", fontsize=12, color=INK, pad=6)


def main(out):
    use_japanese_font()
    lid_top = json.load(open(os.path.join(OUT, "assembly.json")))["LID_TOP"]
    th = float(np.arctan(lid_top[1]))
    rot = trimesh.transformations.rotation_matrix(-th, [1, 0, 0])
    fig = plt.figure(figsize=(13.0, 8.6))
    gs = fig.add_gridspec(2, 3, height_ratios=[2.6, 1.0])
    views = (("tray", SPLIT_X_TRAY, "トレイ（床の上面。キーボードの下に隠れる）", None),
             ("lid", SPLIT_X_LID, "蓋（天板の内側。PaperDIY の裏に隠れる）", rot),
             ("panel", SPLIT_X_PANEL, "化粧パネル（裏。蓋の中に隠れる）", None))
    for i, (kind, X, title, r) in enumerate(views):
        ax = fig.add_subplot(gs[0, i])
        plan_view(ax, kind, X, load(f"{kind}_A_left.stl"), load(f"{kind}_B_main.stl"), r)
        n = len(SPLICE[kind]["y"])
        ax.set_title(f"{title}\n継ぎ板 {n} 枚", fontsize=11.5, color=INK, pad=6)
    seam_section(fig.add_subplot(gs[1, :]))
    fig.suptitle("分割版（A1 mini）の継ぎ板（赤）の位置：どれも左端の継ぎ目のまわりを、閉じた状態の向きで上から見て、継ぎ板の深さで切った形",
                 fontsize=12.5, color=INK)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out, dpi=150, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "splice_plates.png"))
