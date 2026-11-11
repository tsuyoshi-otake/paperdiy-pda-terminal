"""Pictures for tools/snap_sim.py: docs/images/snap_sim.png (three cases at the moment that decides them, and the hold
and closing force against where the lid sits) and, on request, an animation of the lid closing with and without stops.

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
    """The three cases of the figure: (title, stops, run keywords)."""
    free = dict(play=0.3)
    return [("① ストッパーなし・蓋が前後に動く（これまでの版）", False, free),
            ("② ストッパーあり・蓋が前後に動く", True, free),
            ("③ ストッパーあり・蓋が 0.4 mm 手前にずれて固定", True, dict(at=-0.4))]


def note(ax, xy, txt, xytext, color=INK):
    ax.annotate(txt, xy=xy, xytext=xytext, fontsize=9.5, ha="left", va="center", color=color,
                arrowprops=dict(arrowstyle="-", color=color, lw=0.8, shrinkA=2, shrinkB=1), zorder=12)


def arrow(ax, a, b, color=RED):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=11, color=color, lw=1.4, zorder=9))


def figure(S, geo, C, eps_n, out):
    use_japanese_font()
    fig = plt.figure(figsize=(15.0, 9.4))
    yf, ze = S.Y_FRONT, S.Z_EDGE
    for n, (title, stops, kw) in enumerate(cases(S, geo, C, eps_n)):
        fr = []
        r = S.run(geo, C, eps_n, stops=stops, frames=fr, **kw)
        ax = fig.add_axes([0.012 + n * 0.33, 0.515, 0.31, 0.375])
        if n < 2:                                     # the moment the bump is on the tray's edge
            f = pick(fr, "close", lambda f: (f[3], -f[1])) if stops else \
                min((f for f in fr if f[0] == "close"), key=lambda f: abs(f[1] - geo.deg[geo.crest]))
        else:                                         # the moment the tongue is hardest to push in
            f = pick(fr, "close", lambda f: f[4])
        _, deg, u, bend, _ = f
        scene(ax, S, geo, stops, deg, u, bend)
        ax.set_title(title, fontsize=11.5, loc="left", color=INK)
        ax.text(yf - 0.55, ze + 2.2, "蓋", color=LID_E, fontsize=10.5, ha="right")
        ax.text(yf + 2.2, ze - 3.9, "トレイ", color="#6f6852", fontsize=10.5)
        ax.text(yf - 3.0, ze - 3.95, "← 手前", color=MUTED, fontsize=9.5)
        if n == 0:
            arrow(ax, (yf - 0.5, ze + 1.3), (yf - 1.6, ze + 1.3))
            ax.text(yf - 3.0, ze + 0.55, f"蓋ごと手前へ\n{-u:.2f} mm 逃げる", color=RED, fontsize=10, va="center")
            note(ax, (yf + 1.25, ze - 1.35), f"ツメは {bend:.2f} mm しか\nたわまない", (yf + 3.3, ze + 1.6))
            res = f"結果：留める力 {r['hold_n']:.1f} N（弱い。持つと開く）\n蓋は手前に {-r['lid_at']:.2f} mm 出たままになる"
        elif n == 1:
            note(ax, (yf + 2.75, ze - 1.6), "ストッパー（蓋の舌。26 mm 横に\nあるので薄い色）がトレイの壁の\n内側に当たり、蓋を止める",
                 (yf + 3.25, ze + 1.9), color=RED)
            arrow(ax, (yf - 0.45, ze - 1.4), (yf - 1.45, ze - 1.4))
            ax.text(yf - 3.0, ze - 2.3, f"ツメが {bend:.2f} mm\nたわむ", color=INK, fontsize=10, va="center")
            res = f"結果：閉じる力 {r['close_n']:.0f} N、留める力 {r['hold_n']:.0f} N（留まる）"
        else:
            note(ax, (yf + 2.35, S.Z_EDGE + 0.2), f"舌がトレイの壁の角に乗る。\n押し込むには、舌を {-u - 0.13:.2f} mm\n奥へ押しのける力が要る",
                 (yf + 3.25, ze + 2.2), color=RED)
            res = f"結果：閉じるのに {r['close_n']:.0f} N（約 {r['close_n'] / 9.81:.1f} kg）要る。手では閉まらない"
        ax.text(0.0, -0.02, res, transform=ax.transAxes, fontsize=10.5, color=INK, va="top", linespacing=1.5)

    # hold and closing force against where the lid sits (rigid)
    xs = np.round(np.arange(-0.5, 0.3001, 0.02), 2)
    data = {st: [S.run(geo, C, eps_n, stops=st, at=x) for x in xs] for st in (False, True)}
    specs = [("留める力（N）　蓋が前後に動かない場合", "hold_n", [0.065, 0.075, 0.41, 0.31]),
             ("閉じるのに要る力（N）　蓋が前後に動かない場合", "close_n", [0.565, 0.075, 0.41, 0.31])]
    for title, key, rect in specs:
        ax = fig.add_axes(rect)
        top = 62.0 if key == "close_n" else 36.0
        ax.plot(xs, [min(r[key], top * 2) for r in data[False]], color=OLD, lw=2.0, ls=(0, (5, 3)), zorder=3)
        ax.plot(xs, [min(r[key], top * 2) for r in data[True]], color=LID_C, lw=2.0, zorder=4)
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
        y_no, y_st = data[False][-1][key], data[True][-1][key]
        if key == "hold_n":
            ax.axhline(S.HOLD_OK, color=RED, lw=1.0, ls=(0, (2, 2)), zorder=2)
            ax.text(0.415, S.HOLD_OK + 0.6, f"{S.HOLD_OK:g} N：これより下は持つと開く", color=INK, fontsize=9, ha="right", va="bottom")
            ax.annotate("ストッパーなし：手前に 0.3 mm\n出ると、ほとんど留まらない", xy=(-0.3, data[False][10][key]),
                        xytext=(-0.49, 8.3), fontsize=9.5, color=INK, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
            ax.annotate("ストッパーあり：舌が壁をはさむ摩擦で留まるが、\n右の図のとおり閉めるのに大きな力が要る", xy=(-0.42, data[True][4][key]),
                        xytext=(-0.49, 19.5), fontsize=9.5, color=INK, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
            ax.text(0.31, y_st, "どちらも同じ", color=INK, fontsize=9.5, va="center")
        else:
            ax.axhline(20.0, color=RED, lw=1.0, ls=(0, (2, 2)), zorder=2)
            ax.text(-0.02, 20.8, "20 N（約 2 kg）：これより上は閉めにくい", color=INK, fontsize=9, ha="center", va="bottom")
            ax.annotate("ストッパーあり：蓋が 0.3 mm より手前にあると、\n舌がトレイの壁に乗り上げる", xy=(-0.4, data[True][5][key]),
                        xytext=(-0.33, 53.0), fontsize=9.5, color=INK, ha="left", va="center",
                        arrowprops=dict(arrowstyle="-", color=INK, lw=0.8, shrinkB=2))
            ax.text(-0.49, 2.2, "ストッパーなし", color=INK, fontsize=9.5, va="bottom")
            ax.text(0.31, y_st, "どちらも同じ", color=INK, fontsize=9.5, va="center")
        ax.plot([], [], color=LID_C, lw=2.0, label="ストッパーあり（いまの版）")
        ax.plot([], [], color=OLD, lw=2.0, ls=(0, (5, 3)), label="ストッパーなし（これまでの版）")
        ax.legend(loc="upper left" if key == "hold_n" else "upper right", fontsize=9.5, frameon=False,
                  bbox_to_anchor=(0.0, 1.0) if key == "hold_n" else (1.0, 0.82))
    fig.text(0.012, 0.965, "留めツメのシミュレーション：蓋を閉じるとき、何が起きるか", fontsize=14, color=INK)
    fig.text(0.012, 0.935, "実際の蓋とトレイの断面を、ヒンジの軸まわりの軌道で動かしたもの。ツメと壁はばね、斜面には摩擦（0.3）。"
             "上の 3 枚は、それぞれの場合で結果が決まる瞬間。", fontsize=10, color=MUTED)
    fig.savefig(out, dpi=150, facecolor="white", metadata={"Software": None})
    plt.close(fig)
    print("wrote", out)


def gif(S, geo, C, eps_n, out):
    from PIL import Image
    use_japanese_font()
    todo = cases(S, geo, C, eps_n)[:2]
    runs = []
    for title, stops, kw in todo:
        fr = []
        r = S.run(geo, C, eps_n, stops=stops, frames=fr, **kw)
        close = [f for f in fr if f[0] == "close" and f[1] <= 1.6][::4]
        lift = [f for f in fr if f[0] == "lift"][::2] or [fr[-1]]
        runs.append((title, stops, r, close + lift))
    n = max(len(seq) for _, _, _, seq in runs)
    images = []
    for i in range(n + 12):
        fig = plt.figure(figsize=(9.6, 4.5))
        for j, (title, stops, r, seq) in enumerate(runs):
            ph, deg, u, bend, f = seq[min(i, len(seq) - 1)]
            ax = fig.add_axes([0.01 + j * 0.5, 0.2, 0.48, 0.72])
            scene(ax, S, geo, stops, deg, u, bend)
            ax.set_title(title, fontsize=10.5, loc="left", color=INK)
            done = i >= len(seq) - 1
            state = "手を離したあと（ヒンジの戻りで浮く）" if ph == "lift" else "閉じている途中"
            ax.text(0.0, -0.03, f"{state}　浮き {S.LEVER * np.radians(deg):.2f} mm\nツメのたわみ {max(bend, 0):.2f} mm　"
                    f"蓋のずれ {u:+.2f} mm" + (f"\n→ 留める力 {r['hold_n']:.1f} N" if done else "\n"),
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
