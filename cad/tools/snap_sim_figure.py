"""Pictures for tools/snap_sim.py: docs/images/snap_sim.png (three positions of the lid at the moment the bump is on the
tray's edge, and the hold and closing force against where the lid sits) and, on request, an animation of the closing.

Called by snap_sim.py (--figure, --gif). Needs matplotlib and a Japanese font such as Noto Sans CJK JP."""
import io
import os
import sys

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                       # noqa: E402
from matplotlib import font_manager                   # noqa: E402
from matplotlib.patches import FancyArrowPatch, PathPatch  # noqa: E402
from matplotlib.path import Path                      # noqa: E402
from shapely.affinity import translate                # noqa: E402
from shapely.geometry import box as sbox              # noqa: E402
from shapely.ops import transform                     # noqa: E402

LID_C, LID_E = "#33508f", "#1d2f57"
TRAY_C, TRAY_E = "#ece6d6", "#8f8770"
RED, INK, MUTED, GRID = "#c0392b", "#222222", "#6b6b66", "#e4e2dc"
OLD = "#8a8478"                                       # the version without stops: a grey, dashed reference line


def use_japanese_font():
    for f in font_manager.findSystemFonts():
        base = os.path.basename(f)
        if "NotoSansCJK-Regular" in base or "NotoSansJP" in base:
            font_manager.fontManager.addfont(f)
            plt.rcParams["font.family"] = "Noto Sans CJK JP" if f.endswith(".ttc") else \
                font_manager.FontProperties(fname=f).get_name()
            return
    sys.exit("no Japanese font found (install fonts-noto-cjk)")


def add(ax, geom, fc, ec, z, alpha=1.0, lw=0.9, ls="-"):
    for p in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        if p.is_empty or p.geom_type != "Polygon":
            continue
        verts, codes = [], []
        for ring in [p.exterior] + list(p.interiors):
            c = np.asarray(ring.coords)
            verts += c.tolist()
            codes += [Path.MOVETO] + [Path.LINETO] * (len(c) - 2) + [Path.CLOSEPOLY]
        ax.add_patch(PathPatch(Path(verts, codes), fc=fc, ec=ec, lw=lw, ls=ls, zorder=z, alpha=alpha))


TON_C = "#8fa3d1"                                     # the stop tongue: the lid's colour, lighter (another section plane)


def scene(ax, S, geo, stops, deg, u, bend):
    """The section through the lip at this angle: lid shifted by u, lip bent out by `bend`. With stops it is a stepped
    section: inside the tray's wall it runs through a stop tongue (26 mm to the side), drawn lighter."""
    B = S.B
    zt = B.top_z(S.Y_FRONT + B.SHELL_WALL) - B.SHELL_CEIL
    zb = S.Z_EDGE - B.LATCH["bump_at"]
    yi = S.Y_FRONT + B.WALL                           # the walls' inner face
    far = 20.0

    def lean(y, z):                                   # the wall leans out from the ceiling, most at the lip
        y, z = np.asarray(y, float), np.asarray(z, float)
        return y - bend * np.clip((zt - z) / (zt - zb), 0.0, 1.2) ** 2, z
    tray = geo.tray_lip
    if stops:
        ys = yi - 0.6                                 # inside the wall, where both sections are solid
        tray = geo.tray_lip.intersection(sbox(-far - 60, -far, ys, far)).union(
            geo.tray_ton.intersection(sbox(ys, -far, far, far)))
        ton = geo.ton_draw.intersection(sbox(yi - 0.02, -far, far, far))
        add(ax, translate(S.at_angle(ton, deg), u, 0), TON_C, LID_E, 5)
    add(ax, tray, TRAY_C, TRAY_E, 2)
    add(ax, translate(S.at_angle(transform(lean, geo.lip_draw), deg), u, 0), LID_C, LID_E, 4)
    ax.set_xlim(S.Y_FRONT - 3.1, S.Y_FRONT + 7.4)
    ax.set_ylim(S.Z_EDGE - 4.2, S.Z_EDGE + 3.0)
    ax.set_aspect("equal")
    ax.axis("off")


def pick(frames, phase, key):
    fr = [f for f in frames if f[0] == phase]
    return max(fr, key=key) if fr else None


def cases(S, geo, C, eps_n):
    """The three cases of the figure: (title, run keywords)."""
    return [("① 蓋が図面どおりの位置にある", dict(at=0.0)),
            ("② 蓋が 0.2 mm 手前にある", dict(at=-0.2)),
            ("③ 蓋が 0.4 mm 手前にある", dict(at=-0.4))]


def note(ax, xy, txt, xytext, color=INK):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=9.5, ha="left", va="center", color=color,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def arrow(ax, a, b, color=RED):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, color=color, lw=1.4, zorder=9))


def on_edge(geo, fr):
    """The frame in which the bump stands on the tray's edge."""
    return min((f for f in fr if f[0] == "close"), key=lambda f: abs(f[1] - geo.deg[geo.crest]))


def figure(S, geo, C, eps_n, out):
    use_japanese_font()
    fig = plt.figure(figsize=(15.0, 9.4))
    yf, ze = S.Y_FRONT, S.Z_EDGE
    for n, (title, kw) in enumerate(cases(S, geo, C, eps_n)):
        fr = []
        r = S.run(geo, C, eps_n, frames=fr, **kw)
        ax = fig.add_axes([0.012 + n * 0.33, 0.515, 0.31, 0.375])
        _, deg, u, bend, _ = on_edge(geo, fr)
        scene(ax, S, geo, geo.stops, deg, u, bend)
        ax.set_title(title, fontsize=11.5, loc="left", color=INK)
        ax.text(yf - 0.55, ze + 2.2, "蓋", color=LID_E, fontsize=10.5, ha="right")
        ax.text(yf + 2.2, ze - 3.9, "トレイ", color="#6f6852", fontsize=10.5)
        ax.text(yf - 3.0, ze - 3.95, "← 手前", color=MUTED, fontsize=9.5)
        if bend > 0.02:
            arrow(ax, (yf - 0.45, ze - 1.4), (yf - 1.45, ze - 1.4))
            ax.text(yf - 3.0, ze - 2.3, f"ツメが {bend:.2f} mm\nたわむ", color=INK, fontsize=10, va="center")
            note(ax, (yf + 1.15, ze - 1.15), "ツメの出っ張りが、トレイの\n縁に乗り上げたところ", (yf + 3.2, ze + 1.7))
            res = f"結果：閉じる力 {r['close_n']:.0f} N、留める力 {r['hold_n']:.0f} N" + \
                  ("（留まる）" if r["hold_n"] >= S.HOLD_OK else "（弱い。持つと開く）")
        else:
            note(ax, (yf + 1.1, ze - 1.2), "出っ張りがトレイの縁に\n届かず、素通りする", (yf + 3.2, ze + 1.7), color=RED)
            res = "結果：カチッと言わない。留める力 0 N"
        ax.text(0.0, -0.02, res, transform=ax.transAxes, fontsize=10.5, color=INK, va="top", linespacing=1.5)

    xs = np.round(np.arange(-0.5, 0.3001, 0.02), 2)
    data = [S.run(geo, C, eps_n, at=x) for x in xs]
    specs = [("留める力（N）", "hold_n", [0.065, 0.075, 0.41, 0.31], 36.0),
             ("閉じるのに要る力（N）", "close_n", [0.565, 0.075, 0.41, 0.31], 36.0)]
    for title, key, rect, top in specs:
        ax = fig.add_axes(rect)
        ax.plot(xs, [r[key] for r in data], color=LID_C, lw=2.0, zorder=4)
        ax.set_xlim(-0.5, 0.42)
        ax.set_ylim(0, top)
        ax.set_title(title, fontsize=11.5, loc="left", color=INK)
        ax.set_xlabel("蓋の位置（図面どおり = 0、マイナスは手前に出ている。mm）", fontsize=10, color=MUTED)
        ax.grid(True, color=GRID, lw=0.8)
        ax.set_axisbelow(True)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color("#b9b6ad")
        ax.tick_params(colors=MUTED, labelsize=9.5)
        ax.set_xticks(np.arange(-0.5, 0.31, 0.1))
        ax.axvline(0.0, color="#b9b6ad", lw=0.8, zorder=1)
        if key == "hold_n":
            ax.axhline(S.HOLD_OK, color=RED, lw=1.0, ls=(0, (2, 2)), zorder=2)
            ax.text(0.415, S.HOLD_OK + 0.6, f"{S.HOLD_OK:g} N：これより下は持つと開く", color=INK, fontsize=9, ha="right", va="bottom")
            ax.annotate("0.3 mm 手前に出ると、ほとんど留まらない。\n0.4 mm では出っ張りが届かない", xy=(-0.3, data[10][key]),
                        xytext=(-0.49, 12.0), fontsize=9.5, color=INK, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
        else:
            ax.axhline(20.0, color=RED, lw=1.0, ls=(0, (2, 2)), zorder=2)
            ax.text(-0.49, 20.8, "20 N（約 2 kg）：これより上は閉めにくい", color=INK, fontsize=9, ha="left", va="bottom")
            ax.annotate("蓋が奥に寄っていると、ツメが\n大きくたわんで固くなる", xy=(0.2, data[35][key]),
                        xytext=(0.0, 30.0), fontsize=9.5, color=INK, ha="center", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
    fig.text(0.012, 0.965, "留めツメのシミュレーション：蓋を閉じるとき、何が起きるか", fontsize=14, color=INK)
    fig.text(0.012, 0.935, "実際の蓋とトレイの断面を、ヒンジの軸まわりの軌道で動かしたもの。ツメはばね、斜面には摩擦（0.3）。"
             "上の 3 枚は、ツメの出っ張りがトレイの縁を越える瞬間。蓋が前後にどこにあるかで結果が変わる。", fontsize=10, color=MUTED)
    fig.savefig(out, dpi=150, facecolor="white", metadata={"Software": None})
    plt.close(fig)
    print("wrote", out)


def gif(S, geo, C, eps_n, out):
    from PIL import Image
    use_japanese_font()
    todo = [cases(S, geo, C, eps_n)[i] for i in (0, 2)]
    runs = []
    for title, kw in todo:
        fr = []
        r = S.run(geo, C, eps_n, frames=fr, **kw)
        close = [f for f in fr if f[0] == "close" and f[1] <= 1.6][::4]
        lift = [f for f in fr if f[0] == "lift"][::2] or [fr[-1]]
        runs.append((title, r, close + lift))
    n = max(len(seq) for _, _, seq in runs)
    images = []
    for i in range(n + 12):
        fig = plt.figure(figsize=(9.6, 4.5))
        for j, (title, r, seq) in enumerate(runs):
            ph, deg, u, bend, f = seq[min(i, len(seq) - 1)]
            ax = fig.add_axes([0.01 + j * 0.5, 0.2, 0.48, 0.72])
            scene(ax, S, geo, geo.stops, deg, u, bend)
            ax.set_title(title, fontsize=10.5, loc="left", color=INK)
            done = i >= len(seq) - 1
            state = "手を離したあと（ヒンジの戻りで浮く）" if ph == "lift" else "閉じている途中"
            ax.text(0.0, -0.03, f"{state}　浮き {S.LEVER * np.radians(deg):.2f} mm\nツメのたわみ {max(bend, 0):.2f} mm"
                    + (f"\n→ 留める力 {r['hold_n']:.1f} N" if done else "\n"),
                    transform=ax.transAxes, fontsize=10, color=INK, va="top")
        buf = io.BytesIO()
        fig.savefig(buf, dpi=80, facecolor="white", format="png")
        plt.close(fig)
        images.append(Image.open(io.BytesIO(buf.getvalue())).convert("P", palette=Image.ADAPTIVE, colors=64))
    images[0].save(out, save_all=True, append_images=images[1:], duration=90, loop=0, optimize=True)
    print("wrote", out)


def make(S, geo, C, eps_n, fig_out, gif_out):
    if fig_out:
        figure(S, geo, C, eps_n, fig_out)
    if gif_out:
        gif(S, geo, C, eps_n, gif_out)
