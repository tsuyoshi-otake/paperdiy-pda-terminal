"""Draw docs/images/plate0_coupons.png: a labelled top view of the test-print plate (cad/3mf/plate0_test_coupons.3mf),
seen as in Bambu Studio (x to the right, back of the plate up), with what each piece checks.

Usage: python3 docs/coupons_figure.py [out.png]   (needs matplotlib, shapely and a Japanese font such as Noto Sans CJK JP)
"""
import os
import sys
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib import font_manager                   # noqa: E402
from matplotlib.patches import Circle, PathPatch      # noqa: E402
from matplotlib.path import Path                      # noqa: E402
from shapely.geometry import Polygon                  # noqa: E402
from shapely.ops import unary_union                   # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
PLATE = os.path.join(HERE, "..", "cad", "3mf", "plate0_test_coupons.3mf")
NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"
INK = "#222222"

# object name -> (number, short name); pairs are checked together
PIECES = {
    "coupon_hinge_tray": (1, "ヒンジの座（トレイ側）"),
    "coupon_hinge_lid": (2, "ヒンジの座（蓋側）"),
    "coupon_dovetail_A": (3, "蟻ほぞ（A 側）"),
    "coupon_dovetail_B": (4, "蟻ほぞ（B 側）"),
    "coupon_latch_lid": (5, "留めツメ（蓋側）"),
    "coupon_latch_tray": (6, "ツメの受け（トレイ側）"),
    "hinge_cover_lid": (7, "ヒンジカバー（蓋側）"),
    "hinge_cover_tray": (8, "ヒンジカバー（トレイ側）"),
}
CHECKS = [
    ((1, 2), "本物のヒンジで 1 と 2 をつなぐ。板が溝に面一で入る、筒がこすらず回る、M2×8 が割れずに効く、150° 以上開いても壁同士が当たらない"),
    ((3, 4), "3 と 4 を手で押し合わせる。入って、がたつかない"),
    ((5, 6), "6 の手前の面に沿って 5 を押し下げる。パチンと留まり、引き上げると外れる"),
    ((7, 8), "ヒンジの板の上に 7・8 を乗せる。平らに乗る"),
]


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        base = os.path.basename(f)
        if "NotoSansCJK-Regular" in base or "NotoSansJP" in base:
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = "Noto Sans CJK JP" if f.endswith(".ttc") else \
                font_manager.FontProperties(fname=f).get_name()
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def load_plate(path):
    """{name: (vertices placed on the plate, triangles)} from the 3MF (plain objects + item translations)."""
    root = ET.fromstring(zipfile.ZipFile(path).read("3D/3dmodel.model"))
    objs = {}
    for o in root.iter(NS + "object"):
        v = np.array([[float(p.get(k)) for k in "xyz"] for p in o.iter(NS + "vertex")])
        t = np.array([[int(p.get(k)) for k in ("v1", "v2", "v3")] for p in o.iter(NS + "triangle")])
        objs[o.get("id")] = (o.get("name"), v, t)
    out = {}
    for it in root.iter(NS + "item"):
        name, v, t = objs[it.get("objectid")]
        m = [float(x) for x in it.get("transform", "1 0 0 0 1 0 0 0 1 0 0 0").split()]
        R, T = np.array(m[:9]).reshape(3, 3), np.array(m[9:])
        out[name] = (v @ R + T, t)
    return out


def silhouette(v, t):
    tris = [Polygon(v[f, :2]) for f in t]
    return unary_union([p.buffer(1e-4) for p in tris if p.area > 1e-6])


def add_poly(ax, geom, fc, ec):
    polys = getattr(geom, "geoms", [geom])
    for g in polys:
        verts, codes = [], []
        for ring in [g.exterior] + list(g.interiors):
            c = np.asarray(ring.coords)
            verts += c.tolist()
            codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=1.0))


def main(out):
    use_japanese_font()
    plate = load_plate(PLATE)
    fig = plt.figure(figsize=(13.0, 6.4))
    ax = fig.add_axes([0.02, 0.06, 0.46, 0.86])
    zmax = max(v[:, 2].max() for v, _ in plate.values())
    for name, (v, t) in plate.items():
        h = v[:, 2].max()
        shade = 0.93 - 0.33 * h / zmax                     # taller pieces darker
        add_poly(ax, silhouette(v, t), (shade, shade, shade * 1.02), "#555")
        num, _ = PIECES[name]
        c = v[:, :2].mean(axis=0)
        ax.add_patch(Circle(c, 3.0, fc="#c0392b", ec="white", lw=1.2, zorder=5))
        ax.text(c[0], c[1], str(num), color="white", fontsize=10.5, ha="center", va="center", zorder=6,
                fontweight="bold")
        ax.text(c[0], v[:, 1].min() - 1.2, f"高さ {h:.0f} mm" if h >= 2 else f"厚さ {h:.0f} mm",
                fontsize=7.5, color="#666", ha="center", va="top")
    xs = np.concatenate([v[:, 0] for v, _ in plate.values()])
    ys = np.concatenate([v[:, 1] for v, _ in plate.values()])
    ax.set_xlim(xs.min() - 6, xs.max() + 6)
    ax.set_ylim(ys.min() - 8, ys.max() + 6)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title("plate 0（試し刷り）を上から見たところ　↑奥", fontsize=12.5, color=INK, loc="left")

    tx = fig.add_axes([0.51, 0.04, 0.48, 0.90])
    tx.axis("off")
    y = 0.97
    tx.text(0.0, y, "1〜6 は本番の部品から同じ向きのまま切り出した小片で、完成品には使いません。\n"
            "7・8 は本番と同じ部品なので、合えば予備になります。",
            fontsize=10.5, color=INK, va="top", transform=tx.transAxes, linespacing=1.5)
    y -= 0.11
    names = {n: s for n, s in PIECES.values()}
    for pair, check in CHECKS:
        tx.text(0.0, y, "・".join(f"{n} {names[n]}" for n in pair), fontsize=11, color="#c0392b",
                fontweight="bold", va="top", transform=tx.transAxes)
        y -= 0.058
        tx.text(0.03, y, check, fontsize=10, color=INK, va="top", transform=tx.transAxes, wrap=True)
        y -= 0.108
    tx.text(0.0, y + 0.02, "合わないときは cad/src/params.py を直して作り直すか、やすりやドリルで合わせる"
            "（組み立てガイド 2-1）", fontsize=9.5, color="#555", va="top", transform=tx.transAxes)
    fig.savefig(out, dpi=170, facecolor="white", metadata={"Software": None})
    print("wrote", out)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "images", "plate0_coupons.png"))
