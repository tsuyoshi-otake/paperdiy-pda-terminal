"""Photoreal studio renders of the clamshell in matte black PLA (Blender Cycles, run as a Python module).

    pip install bpy==5.3.0            # Blender 5.3 as a Python 3.13 module (about 430 MB)
    python3 docs/render/photoreal.py --view open      # -> docs/images/photoreal_open.jpg (about 10 min on 2 cores)
    python3 docs/render/photoreal.py --view closed    # -> docs/images/photoreal_closed.jpg
    options: --res 1600x1100 --samples 160 --out FILE (.png or .jpg)

Builds the scene from cad/out/*.stl and cad/out/assembly.json (the same parts and positions as index.html), gives
every printed part a matte black PLA finish (faint 0.2 mm layer lines, fine grain, rounded edges at render time), and
lights it like a product shot: soft boxes, a rim light from behind, a light grey floor. The keyboard is the same
stand-in for the CACOE as in index.html; the screen shows a made-up terminal session.
"""
import argparse, json, math, os, sys
import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont
import bpy, bmesh
from mathutils import Vector, Matrix

ap = argparse.ArgumentParser()
HERE = os.path.dirname(os.path.abspath(__file__))
ap.add_argument("--repo", default=os.path.join(HERE, "..", ".."))
ap.add_argument("--view", default="open", choices=["open", "closed"])
ap.add_argument("--out", default=None)
ap.add_argument("--res", default="1600x1100")
ap.add_argument("--samples", type=int, default=160)
ap.add_argument("--tmp", default="/tmp/photoreal")
args = ap.parse_args()
REPO = os.path.abspath(args.repo)
OUT_DIR = os.path.join(REPO, "cad", "out")
A = json.load(open(os.path.join(OUT_DIR, "assembly.json")))
K = A["KIT"]
TAB5 = os.path.exists(os.path.join(OUT_DIR, "tab5_envelope.stl"))
os.makedirs(args.tmp, exist_ok=True)
RX, RY = map(int, args.res.split("x"))
OUT = os.path.abspath(args.out or os.path.join(REPO, "docs", "images", f"photoreal_{args.view}.jpg"))

MONO = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 44, index=5)
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def srgb(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c) + (a,)


# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
cy = scene.cycles
cy.device = "CPU"
cy.samples = args.samples
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.01
cy.use_denoising = True
cy.denoiser = "OPENIMAGEDENOISE"
cy.max_bounces = 10
cy.glossy_bounces = 6
cy.transparent_max_bounces = 8
cy.caustics_reflective = False
cy.caustics_refractive = False
cy.sample_clamp_indirect = 8.0
scene.render.resolution_x, scene.render.resolution_y = RX, RY
scene.render.resolution_percentage = 100
scene.render.film_transparent = False
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = 0.2
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_depth = "8"
scene.render.threads_mode = "AUTO"

world = bpy.data.worlds.new("studio")
scene.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = srgb("#c9c7c3")
bg.inputs["Strength"].default_value = 0.22

root = bpy.data.objects.new("root_mm", None)        # the model in millimetres, the studio in metres
root.scale = (0.001, 0.001, 0.001)
scene.collection.objects.link(root)


def link(obj, parent):
    scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


# ---------------------------------------------------------------- materials
def principled(name, base, rough, **kw):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = base
    b.inputs["Roughness"].default_value = rough
    for k, v in kw.items():
        b.inputs[k].default_value = v
    return m, nt, b


def edge_bevel(nt, b, radius=0.00035, bump=None):
    """Rounded edges at render time (prints never have knife edges) + an optional height into a bump."""
    bev = nt.nodes.new("ShaderNodeBevel")
    bev.samples = 8
    bev.inputs["Radius"].default_value = radius
    if bump is None:
        nt.links.new(bev.outputs["Normal"], b.inputs["Normal"])
        return
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 1.0
    bp.inputs["Distance"].default_value = bump[1]
    nt.links.new(bump[0], bp.inputs["Height"])
    nt.links.new(bev.outputs["Normal"], bp.inputs["Normal"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])


def pla(name, hexcol, rough=0.6):
    """Matte PLA: faint layer lines along the part's z (every part is printed flat), a fine grain, slightly varying
    roughness, rounded edges."""
    m, nt, b = principled(name, srgb(hexcol), rough, **{"Specular IOR Level": 0.42})
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wave = nt.nodes.new("ShaderNodeTexWave")
    wave.wave_type = "BANDS"; wave.bands_direction = "Z"; wave.wave_profile = "SIN"
    wave.inputs["Scale"].default_value = 2 * math.pi / 20 / 0.2      # bands every 0.2 mm (object units: mm)
    wave.inputs["Distortion"].default_value = 0.6
    wave.inputs["Detail"].default_value = 1.0
    nt.links.new(tc.outputs["Object"], wave.inputs["Vector"])
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 2.5
    noise.inputs["Detail"].default_value = 8.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mix = nt.nodes.new("ShaderNodeMath"); mix.operation = "MULTIPLY_ADD"
    nt.links.new(wave.outputs["Color"], mix.inputs[0]); mix.inputs[1].default_value = 0.6
    nt.links.new(noise.outputs["Fac"], mix.inputs[2])
    # roughness: +- 0.015 (a big flat top shows anything more as clouds)
    rn = nt.nodes.new("ShaderNodeTexNoise"); rn.inputs["Scale"].default_value = 0.5; rn.inputs["Detail"].default_value = 2
    nt.links.new(tc.outputs["Object"], rn.inputs["Vector"])
    mr = nt.nodes.new("ShaderNodeMapRange")
    mr.inputs["To Min"].default_value = rough - 0.015; mr.inputs["To Max"].default_value = rough + 0.015
    nt.links.new(rn.outputs["Fac"], mr.inputs["Value"]); nt.links.new(mr.outputs["Result"], b.inputs["Roughness"])
    edge_bevel(nt, b, 0.00035, (mix.outputs["Value"], 0.000012))
    return m


def image_mat(name, img_path, rough, emission=0.0, to_base=True, coat=0.0, coat_rough=0.1):
    m, nt, b = principled(name, (0, 0, 0, 1), rough)
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(img_path)
    tex.interpolation = "Cubic"
    if to_base:
        nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
    if emission:
        nt.links.new(tex.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emission
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_rough
    return m, nt, tex


BLACK = "#1c1c1e"
M = dict(
    lid=pla("pla_lid", BLACK, 0.62),
    tray=pla("pla_tray", BLACK, 0.62),
    panel=pla("pla_panel", "#19191b", 0.64),
)
pom, nt, b = principled("pom", srgb("#161618"), 0.38, **{"Specular IOR Level": 0.5}); edge_bevel(nt, b, 0.0003)
steel, nt, b = principled("steel", srgb("#9aa0a8"), 0.32, Metallic=1.0); edge_bevel(nt, b, 0.0002)
kb_body, nt, b = principled("kb_body", srgb("#202023"), 0.5, **{"Specular IOR Level": 0.45}); edge_bevel(nt, b, 0.0008)
key_side, nt, b = principled("key_side", srgb("#18181a"), 0.42, **{"Specular IOR Level": 0.45})
body_mat, nt, b = principled("module_body", srgb("#d9d9db" if not TAB5 else "#d6d6d4"), 0.5)
edge_bevel(nt, b, 0.0004)


# ---------------------------------------------------------------- meshes
def mesh_obj(name, verts, faces, mats, parent, sharp_deg=32.0, mat_idx=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update(calc_edges=True)
    bm = bmesh.new(); bm.from_mesh(me)
    thr = math.radians(sharp_deg)
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = not (len(e.link_faces) != 2 or e.calc_face_angle(math.pi) > thr)
    if mat_idx is not None:
        for f in bm.faces:
            f.material_index = mat_idx(f)
    bm.to_mesh(me); bm.free()
    for mt in mats:
        me.materials.append(mt)
    ob = bpy.data.objects.new(name, me)
    return link(ob, parent)


def stl_obj(fname, mat, parent):
    t = trimesh.load(os.path.join(OUT_DIR, fname + ".stl"), process=True)
    t.merge_vertices()
    return mesh_obj(fname, t.vertices, t.faces, [mat], parent)


def box_tm(sx, sy, sz, c):
    t = trimesh.creation.box(extents=(sx, sy, sz))
    t.apply_translation(c)
    return t


def rbox_tm(sx, sy, sz, r, c, n=8):
    """Box rounded in plan (radius r), straight sides."""
    import shapely.geometry as sg
    p = sg.box(-sx / 2 + r, -sy / 2 + r, sx / 2 - r, sy / 2 - r).buffer(r, quad_segs=n)
    t = trimesh.creation.extrude_polygon(p, sz)
    t.apply_translation((c[0], c[1], c[2] - sz / 2))
    return t


# ---------------------------------------------------------------- textures
def terminal_png(path, paper):
    """The terminal session of docs/render/index.html, at 2x (1920 x 1080)."""
    W, H = 1920, 1080
    bgc, fg = ("#d9d7d1", "#1f1f1f") if paper else ("#0f1317", "#d6dde4")
    im = Image.new("RGB", (W, H), bgc)
    g = ImageDraw.Draw(im)
    CW, CH, X0 = 24, 48, 24
    lines = ["pi@raspberrypi:~ $ uptime",
             " 21:14:03 up 12 days,  3:41,  1 user,  load average: 0.08, 0.05, 0.01",
             "pi@raspberrypi:~ $ ls notes",
             ("2026-11-03.md  ideas.md  paperdiy-pda.md  todo.md" if paper else "2026-11-12.md  ideas.md  tab5-pda.md  todo.md"),
             "pi@raspberrypi:~ $ cat notes/todo.md",
             "# TODO",
             ("- [x] PaperDIY にファームを書き込む" if paper else "- [x] Tab5 を蓋に組み込む"),
             ("- [x] CACOE キーボードを BLE でつなぐ" if paper else "- [x] CACOE キーボードをつなぐ"),
             "- [ ] 筐体を A1 mini で印刷する",
             "- [ ] トルクヒンジ HG-MF08 を 2 個買う",
             "pi@raspberrypi:~ $ df -h /",
             "Filesystem      Size  Used Avail Use% Mounted on",
             "/dev/mmcblk0p2   29G  6.1G   22G  23% /",
             "pi@raspberrypi:~ $ "]
    wide = lambda ch: ord(ch) > 0x2e7f
    for row, ln in enumerate(lines):
        col = 0
        for ch in ln:
            g.text((X0 + col * CW, row * CH + CH // 2 + 2 + 12), ch, font=MONO, fill=fg, anchor="lm")
            col += 2 if wide(ch) else 1
    g.rectangle([X0 + col * CW, row * CH + 4 + 12, X0 + col * CW + CW, row * CH + CH - 4 + 12], fill=fg)
    sy = 21 * CH
    bar = "#1f1f1f" if paper else "#2b6cb0"
    g.rectangle([0, sy, W, H], fill=bar)
    tc = "#e9e7e1" if paper else "#f2f5f8"
    ty = sy + (H - sy) // 2 + 2
    g.text((CW, ty), "KB:CACOE  Wi-Fi:home 192.168.1.23  SSH:pi@raspberrypi", font=MONO, fill=tc, anchor="lm")
    g.text((W - CW, ty), "電池 87%" if paper else "USB 給電", font=MONO, fill=tc, anchor="rm")
    im.save(path)
    return im


def glass_png(path, gw, gh, aa_w, aa_h, aa_dx, aa_dy, cam, mics, term):
    """The Tab5's black glass (gw x gh mm) with the lit area, camera and microphone holes; image up = lid -y."""
    s = 20
    im = Image.new("RGB", (round(gw * s), round(gh * s)), "#040506")
    g = ImageDraw.Draw(im)
    px = lambda x, y: ((x + gw / 2) * s, (y + gh / 2) * s)    # (x right, y lid -> image down = lid +y)
    x0, y0 = px(aa_dx - aa_w / 2, aa_dy - aa_h / 2)
    x1, y1 = px(aa_dx + aa_w / 2, aa_dy + aa_h / 2)
    im.paste(term.resize((round(x1 - x0), round(y1 - y0)), Image.LANCZOS), (round(x0), round(y0)))
    cx, cy_ = px(cam[0], cam[1]); r = 2.0 * s
    g.ellipse([cx - r, cy_ - r, cx + r, cy_ + r], fill="#0b0d10")
    g.ellipse([cx - r * 0.45, cy_ - r * 0.45, cx + r * 0.45, cy_ + r * 0.45], fill="#141a22")
    for mx, my in mics:
        mx_, my_ = px(mx, my); r = 0.5 * s
        g.ellipse([mx_ - r, my_ - r, mx_ + r, my_ + r], fill="#0a0b0c")
    im.save(path)


def legends_png(path, keys, x0, x1, y0, y1, keycol="#1b1b1d"):
    s = 24
    W, H = round((x1 - x0) * s), round((y1 - y0) * s)
    im = Image.new("RGB", (W, H), keycol)
    g = ImageDraw.Draw(im)
    for (lab, kx0, kx1, ky0, ky1) in keys:
        if not lab:
            continue
        big = not (len(lab) > 1 and not any(c in lab for c in "←↑↓→"))
        f = ImageFont.truetype(SANS, round((5.0 if big else 3.3) * s))
        X = (kx0 - x0 + 1.8) * s
        Y = (y1 - ky1 + 1.5) * s          # image row 0 = +y (the far side of the key)
        g.text((X, Y), lab, font=f, fill="#bdbdbd", anchor="lt")
    im.save(path)


def plane_obj(name, w, h, cx, cy_, z, mat, parent, flip=True):
    """A w x h rectangle facing -z (the viewer of the open lid); its image's top edge at -y."""
    v = [(cx - w / 2, cy_ - h / 2, z), (cx + w / 2, cy_ - h / 2, z), (cx + w / 2, cy_ + h / 2, z), (cx - w / 2, cy_ + h / 2, z)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(v, [], [(0, 3, 2, 1)])        # wound to face -z
    me.update()
    uv = me.uv_layers.new()
    # u along +x, v = 1 at y = cy - h/2
    for loop in me.loops:
        x, y, _ = v[loop.vertex_index]
        uv.data[loop.index].uv = ((x - (cx - w / 2)) / w, 1 - (y - (cy_ - h / 2)) / h)
    me.materials.append(mat)
    return link(bpy.data.objects.new(name, me), parent)


# ---------------------------------------------------------------- assemble (as docs/render/index.html)
tray = stl_obj("keyboard_tray", M["tray"], root)

# keyboard (illustration: a CACOE-like low-profile board)
F, KH = A.get("TRAY_FLOOR", 3.0), 2.2
HB = 11.5 - KH
KW, KD = A.get("KB_SIZE", [195, 86])
kb = bpy.data.objects.new("keyboard", None); link(kb, root)
mesh_obj("kb_body", *(lambda t: (t.vertices, t.faces))(rbox_tm(KW, KD, HB, 3.0, (0, 0, F + HB / 2))), [kb_body], kb)
rows = [
    [['`', 1], ['1', 1], ['2', 1], ['3', 1], ['4', 1], ['5', 1], ['6', 1], ['7', 1], ['8', 1], ['9', 1], ['0', 1], ['-', 1], ['=', 1], ['Bksp', 1.5]],
    [['Tab', 1.5], ['Q', 1], ['W', 1], ['E', 1], ['R', 1], ['T', 1], ['Y', 1], ['U', 1], ['I', 1], ['O', 1], ['P', 1], ['[', 1], [']', 1], ['\\', 1]],
    [['Caps', 1.75], ['A', 1], ['S', 1], ['D', 1], ['F', 1], ['G', 1], ['H', 1], ['J', 1], ['K', 1], ['L', 1], [';', 1], ["'", 1], ['Enter', 1.75]],
    [['Shift', 2.25], ['Z', 1], ['X', 1], ['C', 1], ['V', 1], ['B', 1], ['N', 1], ['M', 1], [',', 1], ['.', 1], ['/', 1], ['Shift', 1.25], ['↑', 1]],
    [['Fn', 1], ['Ctrl', 1], ['Alt', 1], ['Cmd', 1.25], ['', 5.25], ['Alt', 1], ['Ctrl', 1], ['←', 1], ['↓', 1], ['→', 1]],
]
U, GAP = 13.0, 1.4
totalW = 14.5 * U
ky0 = 2.5 * U - U / 2 + 1
caps, keys = [], []
for r, row in enumerate(rows):
    x = -totalW / 2
    y = ky0 - r * U
    for lab, w in row:
        kw, kd = w * U - GAP, U - GAP
        c = (x + w * U / 2, y, F + HB + KH / 2)
        t = trimesh.creation.box(extents=(kw, kd, KH))
        t.apply_translation(c)
        caps.append(t)
        keys.append((lab, c[0] - kw / 2, c[0] + kw / 2, y - kd / 2, y + kd / 2))
        x += w * U
capm = trimesh.util.concatenate(caps)
LX0, LX1, LY0, LY1 = -KW / 2, KW / 2, -KD / 2, KD / 2
legends_png(os.path.join(args.tmp, "legends.png"), keys, LX0, LX1, LY0, LY1)
keytop, nt, b = principled("keytop", (0, 0, 0, 1), 0.42, **{"Specular IOR Level": 0.45})
tc = nt.nodes.new("ShaderNodeTexCoord"); mp = nt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1 / (LX1 - LX0), 1 / (LY1 - LY0), 1)
mp.inputs["Location"].default_value = (0.5, 0.5, 0)
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = bpy.data.images.load(os.path.join(args.tmp, "legends.png"))
tex.extension = "EXTEND"
nt.links.new(tc.outputs["Object"], mp.inputs["Vector"]); nt.links.new(mp.outputs["Vector"], tex.inputs["Vector"])
nt.links.new(tex.outputs["Color"], b.inputs["Base Color"])
capobj = mesh_obj("keycaps", capm.vertices, capm.faces, [key_side, keytop], kb, sharp_deg=181,
                  mat_idx=lambda f: 1 if f.normal.z > 0.9 else 0)
bev = capobj.modifiers.new("bevel", "BEVEL"); bev.width = 0.55; bev.segments = 3; bev.limit_method = "ANGLE"
bev.harden_normals = True
for p in capobj.data.polygons:
    p.use_smooth = True

# moving half
AXIS_Y = A.get("HINGE_AXIS_Y", A["Y_BACK"]); HZ = A["Z_PART"]
pivot = bpy.data.objects.new("pivot", None); link(pivot, root); pivot.location = (0, AXIS_Y, HZ)
lid = bpy.data.objects.new("lid", None); link(lid, pivot); lid.location = (0, -AXIS_Y, -HZ)
stl_obj("display_lid_usbc", M["lid"], lid)
if A.get("PANEL"):
    stl_obj("display_panel_kit", M["panel"], lid)
if A.get("PORT_COVER"):
    stl_obj("port_cover", M["panel"], lid)
env = stl_obj("tab5_envelope" if TAB5 else "paperdiy_kit_envelope", body_mat, lid)
term = terminal_png(os.path.join(args.tmp, "term.png"), paper=not TAB5)
if TAB5:
    rim = 1.2
    gw, gh = K["L"] - 2 * rim, K["W"] - 2 * rim
    glass_png(os.path.join(args.tmp, "glass.png"), gw, gh, K["win"][0], K["win"][1], K["win_off"], K.get("win_off_y", 0.0),
              (59.55, 0.0), [(-40.8, -36.7), (-6.5, -36.7)], term)
    gm, nt, tex = image_mat("tab5_glass", os.path.join(args.tmp, "glass.png"), 0.035, emission=2.6, to_base=False)
    b = nt.nodes["Principled BSDF"]
    b.inputs["Specular IOR Level"].default_value = 0.5
    plane_obj("glass", gw, gh, K["cx"], 0.0, K["z0"] - 0.02, gm, lid)
else:
    em, nt, tex = image_mat("epaper", os.path.join(args.tmp, "term.png"), 0.85, coat=0.25, coat_rough=0.35)
    plane_obj("epaper", K["win"][0], K["win"][1], K["cx"] + K["win_off"], 0.0, K["z0"] - 0.05, em, lid)

# hinges: barrels, leaves, M2 flat heads
HY, HX, HL, HW, BD = A["Y_BACK"], A["HINGE_X"], A["HINGE_LEN"], A["HINGE_WIDTH"], A["HINGE_BARREL_D"]
LT = A["HINGE_LEAF_T"]
for cx in (-HX, HX):
    t = trimesh.creation.cylinder(radius=BD / 2, height=HL, sections=48)
    t.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (0, 1, 0)))
    t.apply_translation((cx, AXIS_Y, HZ))
    mesh_obj("barrel", t.vertices, t.faces, [pom], root)
    for s in (1, -1):
        lw = HW / 2 - BD / 2
        cz = HZ + s * (BD / 2 + lw / 2)
        t = box_tm(HL, LT, lw, (cx, HY - A.get("HINGE_SINK", 0) - LT / 2 - 0.05, cz))
        mesh_obj("leaf", t.vertices, t.faces, [pom], lid if s > 0 else root)
        for hx in (-A["HINGE_HOLE_PITCH_X"] / 2, A["HINGE_HOLE_PITCH_X"] / 2):
            t = trimesh.creation.cylinder(radius=1.85, height=0.3, sections=32)
            t.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, (1, 0, 0)))
            t.apply_translation((cx + hx, HY - 0.1, HZ + s * A["HINGE_HOLE_OFF"]))
            mesh_obj("screw", t.vertices, t.faces, [steel], lid if s > 0 else root)

# ---------------------------------------------------------------- studio: floor, lights, camera
floor_m, nt, b = principled("floor", srgb("#d8d5cf"), 0.85)
fn = nt.nodes.new("ShaderNodeTexNoise"); fn.inputs["Scale"].default_value = 900; fn.inputs["Detail"].default_value = 4
bp = nt.nodes.new("ShaderNodeBump"); bp.inputs["Strength"].default_value = 0.05
nt.links.new(fn.outputs["Fac"], bp.inputs["Height"]); nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
bpy.ops.mesh.primitive_plane_add(size=8.0, location=(0, 0, -0.00005))
floor = bpy.context.active_object; floor.data.materials.append(floor_m)


def area(name, loc, target, size, power, color="#ffffff", spread=180):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "RECTANGLE"; ld.size, ld.size_y = size
    ld.energy = power; ld.color = srgb(color)[:3]
    ld.spread = math.radians(spread)
    ob = bpy.data.objects.new(name, ld); scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


V = args.view
OPEN = V == "open"
pivot.rotation_euler = (math.radians(-112 if OPEN else 0), 0, 0)
VIEWS_CAM = {"open": (-215, -330, 235)}
L = 1 / 22    # light scale (the powers below were set up at 22x)
area("key", (-0.60, -0.22, 0.52), (0, 0.0, 0.03), (0.6, 0.6), 95 * L, "#fff6ec")
area("fill", (0.50, -0.50, 0.20), (0, 0, 0.04), (0.6, 0.4), 26 * L, "#eef3ff")
area("top", (0.05, 0.10, 0.75), (0, 0.02, 0), (0.9, 0.5), 50 * L)
area("rim", (0.30, 0.55, 0.42), (0, 0.02, 0.06), (0.7, 0.18), 80 * L, "#ffffff")
area("rim_l", (-0.55, 0.35, 0.30), (0, 0.02, 0.06), (0.18, 0.5), 35 * L, "#ffffff")
bg.inputs["Strength"].default_value = 0.22 * L * 1.5
if OPEN:   # a soft card whose reflection crosses the upper part of the glass (sells the glass)
    rot = Matrix.Rotation(math.radians(-112), 4, "X")
    ax = Vector((0, AXIS_Y, HZ))
    sc = (rot @ (Vector((K["cx"], -12.0, K["z0"])) - ax) + ax) * 0.001
    n = (rot.to_3x3() @ Vector((0, 0, -1))).normalized()
    cpos = Vector(VIEWS_CAM[V]) * 0.001
    d = (sc - cpos).normalized()
    r = d - 2 * d.dot(n) * n
    area("glass_card", sc + r * 0.55 + Vector((-0.20, 0, 0.07)), sc, (0.16, 0.42), 0.35, "#ffffff", spread=40)

cam_d = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_d); scene.collection.objects.link(cam)
scene.camera = cam
cam_d.sensor_fit = "VERTICAL"
VIEWS = {   # camera (mm), target (mm), vertical fov (deg)
    "open":   ((-215, -330, 235), (-4, 20, 40), 26.5),
    "closed": ((-300, -250, 230), (13, 4, 8), 27.0),
}
cp, tg, fov = VIEWS[V]
cam.location = Vector(cp) * 0.001
cam.rotation_euler = (Vector(tg) * 0.001 - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_d.angle_y = math.radians(fov)
cam_d.clip_start = 0.01; cam_d.clip_end = 20
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = (Vector(tg) * 0.001 - cam.location).length
cam_d.dof.aperture_fstop = 28.0

png = OUT if OUT.endswith(".png") else os.path.join(args.tmp, "render.png")
scene.render.filepath = png
bpy.ops.render.render(write_still=True)
if png != OUT:
    Image.open(png).convert("RGB").save(OUT, quality=92, optimize=True)
print("wrote", OUT)
