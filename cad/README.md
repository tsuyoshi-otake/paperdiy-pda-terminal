# PaperDIY PDA clamshell — printable CAD (derivative of unkyulee/phone-enclosure)

A Boox-Palma-free version of Un Kyu Lee's "PDA Terminal". The screen is an **M5Stack PaperDIY Complete Kit** (4.7"
e-paper, ESP32-S3) **left in its own printed case**: it lies in a thin hollow lid (1.6 mm walls, 1.2 mm ceiling) and a
printed **bezel panel** with the screen window holds it from the front, screwed to six bosses in the lid. The buttons are
pressed directly through finger slots in the panel; a straight USB-C cable goes in through an opening in the left end,
and lid A (the small left piece) also comes in versions for a panel-mount female USB-C, so the end can be swapped later
by reprinting that piece only. It runs on the kit's own 140 mAh LiPo (a power bank on the USB-C when that is not
enough). A snap tab moulded into the lid's front clicks into a recess in the tray, so the closed lid stays shut without
magnets or extra parts. The original knob-and-pin hinge is replaced by **two free-stop torque hinges (Sugatsune HG-MF08)
recessed into the back face, under printed cover plates that sit flush in it and are held by the hinge screws
themselves**, so only the barrels and the screw heads show; the whole back face is at the hinge plane, so the seam between
screen and keyboard stays ~1 mm when open. Lid, tray and panel are split for a
**Bambu Lab A1 mini (180 mm bed)** and joined with glued dovetail keys; with a bed of 220 mm or more they print in one
piece each (`3mf/large/`). Nothing needs supports. Fasteners: 14 × M2×8
countersunk tapping screws (8 hinges, 6 panel). A **test-coupon plate** checks the hinge, dovetail and snap-tab fits in
~20 min. Bill of materials, print settings and assembly order (Japanese): [ASSEMBLY_ja.md](ASSEMBLY_ja.md); parts list
as CSV: [bom.csv](bom.csv).

`KIT_LID = "solid"` builds the previous kit lid (a solid deck with the kit in a pocket, one M2×4 screw from the top, no
panel). `PD_MOUNT = "bare"` in `src/params.py` (or `PD_MOUNT=bare` in the environment) still builds the earlier design:
the bare Assembly Kit on a printed bezel panel with a strap, snap-in push-rods, a 2000 mAh cell and a panel-mount USB-C.
It is described in [README_bare.md](README_bare.md).

Contents: [Run](#run) · [Kit design](#kit-design-pd_mount--kit-the-default) · [Hinge](#hinge) ·
[Printing](#printing) · [Hardware](#hardware) · [Measure on the real parts](#measure-on-the-real-parts) ·
[Verification](#verification-performed) · [Changes vs. the original](#changes-vs-the-original-for-the-licence-indicate-changes) ·
[Sources](#sources-of-measured-dimensions) · [Parameters](#parameters-srcparamspy-all-of-them)

## Run

From the repository root (or the same commands by hand from this folder):
```
make setup     # pip install -r cad/requirements.txt (pinned versions) + the host-test packages
make verify    # fetch the pinned original, build every STL + 3MF, compare with out/MANIFEST.json
make report    # optional, needs prusa-slicer: print time / filament / stability warnings -> out/print_report.md
```
By hand:
```
pip install -r requirements.txt
tools/fetch_original.sh                  # clones unkyulee/phone-enclosure at the pinned commit to ~/phone-enclosure, checks hashes
python3 src/build.py                     # ~10 s; writes out/, out/split/, out/coupons/, renders/
python3 src/export_3mf.py                # 3mf/ print plates
python3 tools/manifest.py --check        # same outputs as committed?
python3 tools/print_report.py            # optional (prusa-slicer)
```
Set `PHONE_ENCLOSURE_STL=/path/to/phone-enclosure/STL` if the original repo is cloned elsewhere.
`src/params.py` holds every parameter; `src/build.py` does the mesh booleans (manifold3d) on the original STLs,
checks each export by re-loading the written STL (watertight, one body), runs assembly interference and motion checks,
writes the test coupons and the lid-A variants, and renders PNGs with `src/render.py` (software z-buffer, no GPU). The full
log is written to `out/build_log.txt`.

### Reproducibility
* **Input pinned:** `ORIG_COMMIT` and `ORIG_SHA256` in `src/params.py`; `load()` refuses STLs with other hashes
  (override: `PHONE_ENCLOSURE_ANY_VERSION=1`). `tools/fetch_original.sh` checks out that commit.
* **Tools pinned:** `requirements.txt` (Python 3.13). The README images use `docs/render/package-lock.json`.
* **Deterministic:** on one machine, two builds give byte-identical STL / 3MF files (also with one CPU); the 3MF zips carry
  fixed timestamps. Another machine can round the last digit differently: on the GitHub Actions runner some files
  are byte-identical and the rest match in geometry only.
* **Recorded:** `out/MANIFEST.json` holds the SHA-256, volume, bounding box and triangle count of every output.
  `tools/manifest.py --check` accepts byte differences only when the geometry matches to 0.01 mm / 0.01 %.
* **CI:** `.github/workflows/build.yml` runs `make verify`, the slicer report, the firmware build (compared byte for byte
  with `firmware/prebuilt/`) and the host tests.

## Kit design (`PD_MOUNT = "kit"`, the default)

### Outputs
| File | Notes |
|---|---|
| `out/display_lid_usbc.stl` | lid, unsplit (hollow shell; 202.0 × 99.5 × 22.8) |
| `out/display_panel_kit.stl` | bezel panel, unsplit (198.4 × 95.9, 1.6 thick + 2.0 rim) |
| `out/keyboard_tray.stl` | tray, unsplit (the original tray with the hinge rework and the snap-tab recess) |
| `out/paperdiy_kit_envelope.stl` | the kit as placed (case 120.0 × 67.0 × 6.3, r 3, KEY and power caps): checks and renders |
| `out/hinge_cover_lid_x2.stl`, `out/hinge_cover_tray_x2.stl` | print 2 of each |
| `out/split/lid_A_left.stl`, `lid_B_main.stl`, `panel_A_left.stl`, `panel_B_main.stl`, `tray_A_left.stl`, `tray_B_main.stl` | A1 mini pieces (≤ 175 mm) |
| `out/split/usb_variants/lid_A_left_usb*.stl` | lid A for a panel-mount female USB-C: M3 ears 16 / 18 / 20 / 22 / 25 / 28 / 30 mm apart, or none (glue) |
| `out/whole/lid.stl`, `tray.stl`, `panel.stl`, `out/whole/usb_variants/lid_usb*.stl` | one-piece parts for a bed of 220 mm or more: no split, no keys, and the lid without the ceiling blocks that only carry the keys (each asserted to be the checked part minus material; the panel-mount lids are also checked against the connector) |
| `out/coupons/*.stl` | hinge seat (lid, tray), dovetail key (A, B), snap tab (lid) + recess (tray) |
| `3mf/plate0_test_coupons.3mf` | coupons + one cover of each kind, ~23 min, 9 g |
| `3mf/plate1_lid.3mf` | lid A + B + 2 lid covers, ~1 h 18 min, 52 g |
| `3mf/plate2_tray.3mf` | tray A + B + 2 tray covers, ~1 h 38 min, 64 g |
| `3mf/plate3_panel.3mf` | panel A + B, ~34 min, 23 g |
| `3mf/usb_variants/lid_A_left_usb*.3mf` | the lid-A variants, one per file |
| `3mf/large/plate1_lid.3mf`, `plate2_tray.3mf`, `plate3_panel.3mf` | one-piece lid / tray / panel (+ covers) on a 220 x 220 mm plate: ~1 h 11 min 51 g, ~1 h 34 min 63 g, ~33 min 23 g (137 g, 3 h 17 min, nothing to glue) |
| `3mf/large/usb_variants/lid_usb*.3mf` | the panel-mount lids in one piece |

Plates 1–3: about 139 g and 3 h 30 min (the solid kit lid took 87 g and 2 h 45 min for plate 1 alone).

### The kit
Measured from M5Stack's model of the Complete Kit (`m5stack/M5_Hardware`, `Products/K159-B_PaperDIY_Complete_Kit/Structures/PaperDlY_Complete_Kit.stl`,
sha256 `9258e3e2…3e58`): case 120.0 × 67.0 × 6.3 mm with r 3 mm corners; window 105.0 × 59.7 at the front, 4.0 mm off
centre away from the USB end; KEY1/KEY2 caps on one long edge (9.6–20.4 and 21.6–32.4 mm from the centre toward the USB
end, 1.2 proud, 2.1–4.95 mm behind the front face); power cap on the USB end (+17.9…+28.8 mm across, 1.27 proud);
USB-C at −24.0 across, 2.44–5.6 mm behind the front; a 4.2 mm hole in the back plate over the M2 standoff, 20.0 mm from
the centre toward the USB end (not used by the shell lid). M5Stack: 43.1 g.

### Layout and lid shape
* The kit lies front face down (window toward the keyboard), window centred on the lid (`KIT_CX = −4.0`), USB end at −x,
  KEY edge toward the front (−y), as the bare board was.
* **Panel face** at `PANEL_Z0 = KB_TOP_Z + KB_CLR` = 15.0: the CACOE stands above the tray rim (the original lid's panel
  face was at z = 15), and nobody has measured it yet. Measure the keyboard over the keycaps and set
  `KB_TOP_Z = 3.0 + thickness`: every millimetre comes off the lid. The panel is 1.6 thick, so the kit's front face is at
  16.6 and its back (+ 0.2 gap) at 23.1.
* **Underside**: the original parting plane z = 10.4417 + 0.05376 y (fitted to the original lid, residual < 0.001 mm),
  flat at `Z_PART` behind y = 44.7 (the hinge strip).
* **Top**: a plane through the lowest point that the hinge allows at the back face (leaf 12.75 mm above the axis + cover
  rim 0.8 + chamfer 0.8 → z 27.2 at y = 53) and the most demanding of: the kit + ceiling, the USB-C plug path + 0.8
  (`USB_CEIL`), the snap tab's root. The USB-C path sets it: z = 25.804 + 0.02635 y. The lid is 16.6 mm thick at the front
  face and 14.2 at the back; the closed case is 24.6 mm tall at the front and 27.2 at the back (was 30 / 30). The hinge
  (25 mm wide, face mounted) sets a floor of ~26 mm at the back whatever the keyboard.
* **Shell** (`KIT_LID = "shell"`): the tray's outline (r 6 corners) as a prism between the two planes with 0.8 mm
  chamfers, hollowed to `SHELL_WALL` = 1.6 walls and a `SHELL_CEIL` = 1.2 ceiling. Inside: the two hinge housings
  (9.5 mm deep, 27 mm wide), six screw bosses (Ø6) for the panel with Ø1.8 pilots, three ribs from the
  ceiling to 0.1 mm above the kit's back (x −50 / 0 / 40, clear of the ESP32 window), two guide ribs either side of the
  plug path, thicker ceiling blocks (3.4 mm) around the dovetail keys, and a relief that leaves 0.8 mm of ceiling over the
  plug. Plate 1 went from 87 g / 2 h 45 min (solid) to 52 g / 1 h 18 min.
* **Bezel panel** (`PANEL_*`): 1.6 mm, inside the lid's walls (0.2 mm clear of them and the housings). Screen
  window = the kit's window + 0.3 per side with a 1.0 mm chamfer on the visible face; a locating rim (2.0 high, 1.2 wide,
  0.2 clear, below the caps at 2.1) around the kit on its back; six countersunk M2×8 holes (6.4 mm into the bosses); a gap in
  the rim for the USB-C plug. The kit is clamped between the panel and the ribs.
* **Buttons**: finger slots through the panel, 6.5 mm out from the kit, at the KEY caps (one slot for both, on the front
  edge) and the power cap (on the USB end). No push-rods.
* **USB-C, direct** (default): a 13 × 7.6 mm opening in the left end face; the guide ribs lead a straight plug (overmold
  ≤ 12 × 6.5) to the port, and the plug stays in with the lid closed. The panel is open over the plug path
  (`PANEL_USB_SLOT`: 13.2 mm wide, from a 2.2 mm frame at its left edge to the kit), like the button slots, so the plug
  can be watched and pushed home by hand; with a panel-mount female the extension's inner plug goes in and out the same
  way, without taking the panel off. The front panel key moved to y −37.6 to clear it.
* **USB-C, panel-mount female** (lid-A variants): the same lid with the opening moved to y = 20 (`USB_PM_Y_KIT`, clear of
  the split blocks and the power slot), 13 × 7 mm (narrower for close ears) and two Ø3.4 holes. The connector's ears and
  body can be up to 7.8 mm tall between the panel and the ceiling. Only lid A changes (the build asserts that lid B is
  identical); a short extension's male end goes into the kit and its cable lies beside the kit, behind the panel.
* **Back**: `BACK_STYLE = "solid"` for lid and tray in the kit design: the whole back face is at the hinge plane
  (y = 53). With housings only behind the hinges, the lid's back edge between them was 7.65 mm in front of the hinge axis
  and swung 11–15 mm off the tray when opened, a slot between screen and keyboard; now the edge is 0.15 mm from the axis
  (1.15 mm before the covers went flush) and the seam stays 0.8–0.9 mm (90–150°; it was 2.3–2.6). Same hinges. The cost:
  with the keyboard's charge plug in, the lid opens to 91°.
* **Split**: at x = −72 like before, three dovetail keys in the lid's ceiling blocks at y −37, 5, 36 and in the panel at
  y −36, 0, 40 (clear of the plug path and the slots).
* **Print**: lid pieces top face down (the 3MF export first tilts the top plane level, `LAY_TOP`, from `assembly.json`);
  panel pieces visible face down.

### Snap tab (`LATCH`)
An 18 × 1.0 mm tab is freed from the middle of the lid's front wall by two 0.8 mm slots and runs 3.6 mm below the
parting into a recess in the tray's front face (0.15 mm behind it, 0.3 mm each side). A 0.45 mm bump on its inside
(45° closing ramp, 35° opening ramp) presses on the recess face, bending the tab 0.30 mm outward into free air, and drops
into a groove 2 mm below the parting. Free length 11 mm → k = 3EI/L³ ≈ 11.8 N/mm (E = 3.5 GPa); ~4.5 N to open at the tab
(μ = 0.3) plus the hinges' friction, ~6.3 N to close; strain 1.5 t δ / L² = 0.37 % (the tab bends across the print
layers, so keep it under ~0.5 %). The build also rotates the rigid tab along the real opening arc: it bends at most
0.29 mm. The tray keeps 1.85 mm of front wall behind the recess, 1.50 behind the groove.

### Checks run by `src/build.py` (kit)
Kit envelope vs lid and vs panel, a straight USB-C plug in the port vs lid and vs panel, panel vs lid and vs tray, lid vs
tray, the keyboard's room (tray floor to `KB_TOP_Z`) vs lid and vs panel, dovetail halves (lid, panel, tray), hinge leaves
/ barrels / covers vs both halves, and for every lid-A variant a female-connector envelope (ears + body) vs lid, panel and
kit: all 0 mm³ (plug vs lid 0.012, lid vs tray 0.001). Lid + kit + panel + covers rotated 0–180° about the real hinge
axis: no contact with the tray; the lid reaches the table at 157.3°. With the axis 0.15 mm further in (exactly at the back
face) still none; 0.3 mm further in, the lid meets the tray at 168°. With the keyboard's charge plug in, the lid opens to
91°.

### Tipping
Lid side 125 g (printed parts as sliced + kit 43.1 g + half the hinges), centre of mass 47.6 mm in front of the hinge
axis; the device rests on the tray covers' bottom edge (y = 53): a keyboard of **60 g** keeps it on its feet up to the
table contact at 157.3° (`out/print_report.md`).

### Colour mock-ups
`make render` also draws the closed and open views in three palettes: all black, all khaki, and a mix (khaki lid, black
tray and panel): `docs/images/render_{open,closed}_{black,khaki,mix}.png`.

### Hinge
* **Parts:** 2 × Sugatsune **HG-MF08** (free-stop, 0.0784 N·m ±25 % each, POM, 20 × 25 × 2.0 mm, holes Ø2.4 with Ø4.2
  countersink, pitch 10 along / 16 across the axis, from Sugatsune's spec table). The lid side (125 g with the kit and the
  panel, centre of mass 47.6 mm from the axis) needs about 0.06 N·m held horizontal, so the pair (0.157 N·m) holds it at
  any angle and still opens easily. HG-MF15 (0.147 N·m) is 30 mm long with M3 holes: `HINGE_LEN = 30`,
  `HINGE_HOLE_PITCH_X = 20`.
* **Axis** at the outer back edge, on the parting (z = 12.85). Sugatsune's 3D model shows a flat back and a barrel (≈ Ø5.5)
  on the front only, its axis ≈ 3.2 mm above the flat back (`HINGE_AXIS_ABOVE_BACK`). Seated flat side down 1 mm below
  the back face (under the flush covers), the axis is at y ≈ 53.15, 0.15 mm outside the back face (y = 53.0); the motion
  check, the tipping estimate and the renders rotate about that axis. The original knuckle, ears, knob-pins and trough are removed.
* **Mounting:** each leaf sits in a 3.05 mm mortise (2 mm leaf + 1 mm cover, 0.25 mm clearance) with a slot for the barrel
  (up to ~Ø6.2); 4 × M2×8 countersunk tapping screws per hinge go through the cover and the leaf, 5 mm into the back
  (Ø1.8 pilots), tip 1.5 mm before the wall's inner face. Hinge centres at x = ±52
  (`HINGE_X`), clear of the split at x = −72 and the tray's rear opening (x ≥ 72.9).
* **Back face:** `BACK_STYLE = "solid"`: the whole back face of lid and tray is at the hinge plane, so the lid's lower back
  edge is 0.15 mm from the axis and the seam between screen and keyboard stays 0.8–0.9 mm from 90 to 150°
  (with housings only behind the hinges it was 11–15 mm). The lid has a 9.5 mm deep, 27 mm wide housing behind each hinge
  for the screws.
* **Covers** (`out/hinge_cover_lid_x2.stl`, `out/hinge_cover_tray_x2.stl`, 1.0 mm, case colour): flush in a pocket in the
  back face (0.15 mm clearance), overlapping the case by 1.5 mm and starting 3.6 mm from the axis; the tray's runs out
  through the bottom, where the tray's 3 mm back-bottom chamfer is squared under the cover plus a 1.5 mm frame each side. Each has two Ø4.0 × 90° countersinks over the leaf holes and under each a cone (Ø4.1, 0.7 mm) that
  fills the leaf's countersink, so the hinge screw clamps cover and leaf through a conical PLA washer: no glue. Two crush
  ribs on each side edge (`COVER_RIBS`: 0.15 → 0.3 mm proud from the inner to the outer face, so up to 0.15 mm into the
  pocket wall) hold a cover in its pocket when pressed in, before or without the screws; tune them by reprinting the
  covers only. Flush
  covers sink the leaves by their thickness, which moves the axis in by as much: at 2 mm the axis would sit inside the back
  face and the back edges of lid and tray would collide when opening, so they stay 1 mm (too thin for print services'
  2 mm minimum; print them yourself).
* **Checks:** lid + kit + panel + covers rotated 0–180° about the axis do not touch the tray + covers; on a table the lid
  reaches the table at 157.3° (opening limit). The axis height is read off Sugatsune's 3D viewer: moved 0.3 mm further in,
  the lid would meet the tray at 168° (past the table limit). Hinge envelopes and covers vs lid / tray: 0 mm³.
* The hinge's 25 mm leaf span sets a floor of about 26 mm for the closed height at the back, whatever the keyboard.

### Keyboard charge port
The original tray has an opening in its back wall at x 72.9–89.1 (z ≈ 6.0 to the lid), probably for the CACOE's charge
port, kept as it is. `build.py` checks a straight plug with a 12 × 6.5 mm overmold: 0 mm³ against tray and closed lid;
**with the plug in, the lid opens to 91°** (the full-width back face meets the plug beyond that). Any plug whose overmold
fits the original opening (≈ 16 × 6.8 mm) fits.

### Printing
* **Plates** (`3mf/`, A1 mini, 180 × 180 mm): `plate0_test_coupons` (23 min, 9 g, print first), `plate1_lid` (lid A + B,
  2 lid covers, 1 h 18 min, 52 g), `plate2_tray` (tray A + B, 2 tray covers, 1 h 38 min, 64 g), `plate3_panel` (panel A + B,
  34 min, 23 g): 139 g and 3 h 30 min for plates 1–3. `3mf/usb_variants/` holds lid A for a panel-mount female.
* **One piece** (`3mf/large/`, 220 × 220 mm plates): lid (1 h 11 min, 51 g), tray (1 h 34 min, 63 g), panel (33 min,
  23 g): 137 g and 3 h 17 min, nothing to glue; `3mf/large/usb_variants/` holds the panel-mount lids in one piece.
* **Orientation:** lid top face down (the export tilts the sloped top plane level first, `LAY_TOP` from `assembly.json`),
  panel visible face down, tray floor down, covers visible face down (the cones face up). No supports.
* **Settings** (Bambu Studio): 0.20 mm Standard, PLA, textured PEI, **3 wall loops** (material around the screw pilots),
  15 % gyroid, brim Auto. Times and masses above are PrusaSlicer estimates with an approximation of that profile
  (`tools/a1mini_pla_020.ini`, `out/print_report.md`); Bambu Studio's own numbers differ somewhat.
* **Slicer warnings:** plate 0 flags the snap-tab coupons for low bed adhesion (keep brim on Auto); plate 1 flags "floating
  bridge anchors" in lid B, which is the 1.2 mm ceiling bridged over the infill of the hinge housings (checked in the sliced
  layers; the one-piece lid has none).
* **Test coupons** (`plate0_test_coupons.3mf`, cut from the real parts in print orientation): hinge seats from tray and lid
  (put a real HG-MF08 and a cover in: cover flush, barrel free, M2×8 bites, opens past 160°), a dovetail key (slides in by hand
  without play; skip it for the one-piece parts), the snap tab and its recess (clicks shut, lifts off; tune
  `LATCH["bump"]` in 0.05 mm steps), and one cover of each kind. Other fits: `HINGE_CLR`, `HINGE_BARREL_D`,
  `HINGE_PILOT_D`, `HINGE_AXIS_ABOVE_BACK`, `COVER_POCKET_CLR`, `COVER_RIBS`, `COVER_CSK`, `DOVETAIL["clr"]`.

### Hardware
* 14 × **M2×8 countersunk tapping screws** for plastic: 8 hinges (through the covers), 6 panel.
* 2 × **Sugatsune HG-MF08** (-WT or -BL; hidden under the covers).
* M5Stack **PaperDIY Complete Kit** (K159-B), used in its own case.
* A straight USB-C cable whose overmold is ≤ 12 × 6.5 mm, or (optional) a short panel-mount USB-C extension with M3 ears
  16–30 mm apart and ears + body ≤ 7.8 mm tall, with the matching lid A.
* CA gel or epoxy (dovetail seams of the split parts); thin double-sided tape if the keyboard is loose.
* Parts list with numbers matching the exploded view: [bom.csv](bom.csv); assembly order: [ASSEMBLY_ja.md](ASSEMBLY_ja.md).

### Measure on the real parts
* **Keyboard thickness** over the keycaps: `KB_TOP_Z = 3.0 + thickness` (assumed 11.5 mm, as the original lid allowed).
  Every millimetre less comes off the lid.
* **Keyboard width and depth**: `KB_SIZE = (w, d)` adds pads on the tray's inner walls to take up the play (`KB_PAD`).
* **Keyboard weight**: 60 g or more keeps the device on its feet up to the table contact; see "Tipping".
* **Hinge barrel and axis**: read off Sugatsune's 3D viewer, not a drawing; join the hinge coupons with a real hinge.
* **The kit's printed case**: modelled from M5Stack's 3D file (120.0 × 67.0 × 6.3, r 3); the panel's rim has 0.2 mm clearance.
* **CACOE charge port / switch** positions are inferred from the original tray's openings (`KB_CUTS_ENABLED` adds others).

### Verification performed
Every STL re-loaded: watertight, consistent winding, one body, pieces ≤ 175 mm (one-piece parts ≤ 214 mm). Zero-volume
interference in the closed assembly between lid, panel, tray, the kit envelope, a USB-C plug in the port, the keyboard's
room and every panel-mount connector envelope; dovetail halves; hinge envelopes and covers; lid + kit + panel + covers
rotated 0–180° about the hinge axis; the keyboard's charge plug while opening; the snap tab along its real opening arc.
PrusaSlicer slice of every plate, wall thickness by ray casting, tipping estimate, two builds byte-identical, renders
inspected. **Not done:** no print of this version yet (the earlier bare-kit version was printed and assembled); no FEA.

## Changes vs. the original (for the licence "indicate changes")
**Kit design (default):** the original lid (`Display.stl`) and display panel are not used: the lid is a new hollow part
that follows the original's outline, parting surface and corner radii, with hinge housings, panel bosses, ribs, a USB-C
opening and guides, the hinge mortises and a snap tab; the bezel panel is new (window, rim, finger slots, countersunk
holes). The tray is the original `Keyboard.stl` with the hinge rework below (item 3) and a recess + groove for the snap tab
in its front face. New parts: 4 hinge covers, the lid-A variants and the test coupons.

**Earlier design (`PD_MOUNT = "bare"`):**
1. **Display Panel:** Palma window, Palma button slots and both vent grilles filled. New PaperDIY window, locating lip, strap
   posts, push-rod cradles, battery bay, USB-plug relief. Outline and the 4 corner screw holes are untouched (original mesh kept).
2. **Display (lid):** front-wall Palma side-button slot (incl. ceiling-edge notch) and right-wall Palma USB opening **closed**,
   rebuilt by extruding the adjacent original wall profile. A ray scan found **0 deviations** from the original outer surface
   (flat wall at y = −46.5 / x = +101, same top chamfer). Added: panel-mount USB-C opening + 2 screw holes (inner fillet
   squared behind them) and the power-rod bore (left wall), 2 key-rod bores (front wall), battery ceiling relief.
   **Hinge knuckle removed**, back wall rebuilt (original 3 mm) with a 9.5 mm housing and two tapered ribs behind each
   hinge, two hinge mortises with barrel slot and pilot holes, 14 triangular ribs between the long walls and the ceiling
   (see "Hinge"). **Camera window filled** (flat top). The 4 corner insert holes are refilled and re-drilled as Ø1.8 pilots for M2×8 tapping screws.
   Label recess, vents and corner bosses otherwise unchanged.
3. **Keyboard (tray):** **hinge ears and trough removed**, back wall rebuilt (original 3 mm) with a 9.5 mm housing and two
   tapered ribs behind each hinge, two hinge mortises with barrel slot and pilot holes, bottom chamfer squared under the
   leaves. Keyboard cut-outs otherwise unchanged by default
   (`KB_CUTS_ENABLED = False`). The original right-wall (y 26.3–36.7) and
   rear-wall (x 72.9–89.1) openings are kept; they are probably the CACOE port/switch cut-outs of the original design (not
   verified). If the real keyboard's port/switch are elsewhere, set `KB_CUTS_ENABLED = True`, measure `KB_*` and rebuild.
4. New parts: strap, 3 push-rods, 4 hinge covers, optional top plate, optional front clip and magnet drilling jigs, test coupons. Split versions of lid / tray / panel,
   lid-A variants for other USB-C cables. The original knobs and label are not used.

## Sources of measured dimensions
* PaperDIY Assembly Kit mechanical drawing **K159_PaperDIY_Assembly_Kit_model_size.pdf**
  (m5stack-doc.oss-cn-shenzhen.aliyuncs.com/1287/…). Text is not extractable (CJK font map missing), so the dimension values
  and positions were read from the PDF's vector geometry (scale 1:2): 115.3 × 62.5 × 5.5, PCB from 67.9, M2 at 77.9/centre
  (d2 in d4, top depth 5.4), keys at 72.9 & 84.9 (12.0 apart; actuator 1.72), short-edge switch 6.84 + 1.72, USB-C
  50.78–59.72 (8.94) protruding 1.75, module and antenna outline.
* **M5_Hardware/Products/K159-B_PaperDIY_Complete_Kit/Structures/PaperDlY_Complete_Kit.stl** (GitHub): cross-checked the
  above (kit back-cover hole at the M2 position, button caps 12.0 apart, USB-C position) and gave the **window 105.01 × 59.72**
  with its offsets (1.39 / 8.90 / 1.39).
* M5 docs (docs.m5stack.com/en/products/sku/K159): size, power button / KEY1 = G4 / KEY2 = G3, SH1.0-2P battery connector.
* Sugatsune HG-MF spec table (global.sugatsune.com/eu/en/tech/products/21651_t) and retailer listings: L / W / t / W2 / H2,
  holes, torque. The barrel is not in the table: `HINGE_BARREL_D` = 5.5 and `HINGE_AXIS_ABOVE_BACK` = 3.2 are read off
  Sugatsune's online 3D viewer (end view, scaled by the 25 mm width), so they are good to a few tenths of a mm.
* Original enclosure geometry: sections and ray probes of the phone-enclosure STLs.

## Licence & attribution
Derived from **"The PDA Terminal" / phone-enclosure by Un Kyu Lee** — https://github.com/unkyulee/phone-enclosure —
licensed **CC BY-NC 4.0** (https://creativecommons.org/licenses/by-nc/4.0/). The models and the images made from them
(`out/`, `3mf/`, `renders/`, `../docs/images/`) are under the same licence, non-commercial use only: see
[LICENSE.md](LICENSE.md). The scripts that build them (`src/`, `tools/`) and the documentation are under the
repository's [MIT License](../LICENSE). Changes are listed above. The PaperDIY is a product of M5Stack; its dimensions come from M5Stack's
published drawing and structure files.

## Parameters (`src/params.py`, all of them)
| Parameter | Value | Status | Note / source |
|---|---|---|---|
| `PD_MOUNT` | `"kit"` | design choice | `"kit"`: Complete Kit in its case in the lid; `"bare"`: the earlier design (env `PD_MOUNT` overrides) |
| `KIT_L` / `KIT_W` / `KIT_T` / `KIT_R` | `120.0` / `67.0` / `6.3` / `3.0` | measured | [M:K159-B STL] case without the caps |
| `KIT_WIN` / `KIT_WIN_OFF` | `(105.0, 59.7)` / `4.0` | measured | [M:K159-B STL] window, its offset away from the USB end |
| `KIT_KEY_CAPS` / `KIT_CAP_OUT` / `KIT_CAP_Z` | `((9.6, 20.4), (21.6, 32.4))` / `1.2` / `(2.1, 4.95)` | measured | [M:K159-B STL] KEY caps toward the USB end |
| `KIT_PWR_CAP_Y` / `KIT_PWR_CAP_OUT` | `(17.9, 28.8)` / `1.27` | measured | [M:K159-B STL] power cap on the USB end |
| `KIT_USB_Y` / `KIT_USB_Z` | `-24.0` / `(2.44, 5.6)` | measured | [M:K159-B STL] USB-C on the USB end |
| `KIT_SCREW_D` | `20.0` | measured | [M:K159-B STL] back-plate hole over the M2 standoff, toward the USB end |
| `KIT_MASS_G` | `43.1` | measured | [M: docs.m5stack.com K159-B] |
| `KIT_CX` / `KIT_FIT` / `KIT_GAP` | `-4.0` / `0.2` / `0.2` | design choice | window centred; pocket clearance per side / behind |
| `KB_TOP_Z` / `KB_CLR` | `14.5` / `0.5` | ASSUMED | keyboard's highest point (3.0 + thickness over the keycaps) -> MEASURE; clearance under the panel |
| `KB_SIZE` / `KB_PAD` | `None` / `clr 0.15, w 6, 4 front + 4 back + 2 per end` | ASSUMED | keyboard body width × depth -> MEASURE; pads on the tray's inner walls take up the play (`None` = no pads) |
| `LID_UNDER` | `(10.4417, 0.05376)` | measured | [M] parting plane of the original lid, z = a + b y |
| `LID_SKIN` / `LID_CHAMFER` / `COVER_TOP_RIM` | `1.2` / `0.8` / `0.8` | design choice | least skin; edge chamfers; lid-cover rim above the leaf (the top chamfer leaves a thin lip over the flush cover) |
| `KIT_NOTCH` | `out 7, depth 5.6, end 1.5, r 2` | design choice | finger notches at the caps (`KIT_LID = "solid"`) |
| `USB_CH` | `w 13, h 7.6` | design choice | channel for a straight USB-C plug (overmold ≤ 12 × 6.5) |
| `KIT_SCREW_SEAT` | `1.6` | design choice | lid under the M2×4 head -> 2.2 mm into the kit (`KIT_LID = "solid"`) |
| `KIT_LID` | `"shell"` | design choice | hollow lid + bezel panel; `"solid"`: the solid deck with the kit in a pocket |
| `SHELL_WALL` / `SHELL_CEIL` / `USB_CEIL` | `1.6` / `1.2` / `0.8` | design choice | lid walls (4 lines), ceiling (6 layers), ceiling left over the USB-C plug path |
| `PANEL_T` / `PANEL_CLR` / `PANEL_WIN_CLR` | `1.6` / `0.2` / `0.3` | design choice | bezel panel; clearance to the lid's walls; window = kit window + 0.3 per side |
| `PANEL_RIM` / `PANEL_SLOT` | `h 2.0, w 1.2` / `out 6.5, end 1.5, r 1.5` | design choice | locating rim around the kit; finger slots at the caps |
| `PANEL_SCREWS` | `(±91, −37.5), (±91, 46), (−62, −39.5), (−62, 40)` | design choice | six M2×8 into the lid's bosses, clear of the housings |
| `PANEL_DOVETAIL_Y` / `DOVETAIL_Y_KIT` | `(-37.6, 0, 40)` / `(-37, 5, 36)` | design choice | panel keys (the front one between the edge and the USB slot) / lid keys |
| `PANEL_USB_SLOT` | `frame 2.2, half 6.6, r 1.5` | design choice | panel open over the USB-C plug path, from a 2.2 mm frame at the left edge to the kit (`None` = closed) |
| `KIT_RIBS_X` / `USB_GUIDE_X` / `SPLIT_BLOCK` | `(-50, 0, 40)` / `(-84, None)` / `7 × 7 × 3.4` | design choice | ribs onto the kit's back; USB-C guide ribs; ceiling blocks around the lid keys |
| `USB_PM_Y_KIT` | `20.0` | design choice | panel-mount female opening in the lid-A variants (clear of the split blocks and the power slot) |
| `LATCH` | `w 18, t 1.0, slot 0.8, root 9, below 3.6, bump 0.45 @ 2.0, clr 0.15, 45° / 35°` | design choice | snap tab (see "Snap tab") |
| `PANEL_Z_FRONT` | `15.0` | measured | [M:Display Panel.stl] screen-side face |
| `PANEL_Z_BACK` | `18.0` | measured | [M:Display Panel.stl] back face, seats against lid corner bosses |
| `LID_CEILING_Z` | `27.0` | measured | [M:Display.stl] ceiling underside (ceiling 27..30, 3.0 thick) |
| `LID_CEIL_THK` | `3.0` | measured | [M:Display.stl] |
| `LID_INNER_Y` | `43.5` | measured | [M:Display.stl] inner wall faces at y=+-43.5, x=+-98 |
| `LID_INNER_X` | `98.0` | design choice |  |
| `LID_LABEL_POCKET` | `(21.7, 78.0, 21.34, 32.5)` | measured | [M:Display.stl] x0,x1,y0,y1 of top label recess (ceiling only 1.5 thick) |
| `LID_FRONT_SLOT_X` | `(-51.5, -6.5)` | measured | [M:Display.stl] Palma side-button slot in front wall, z 19..27 + ceiling edge |
| `LID_RIGHT_OPEN_Y` | `(-6.0, 6.0)` | measured | [M:Display.stl] Palma USB opening in right wall (x=+101), z 19..27 |
| `INSERT_M2_D` | `3.2` | measured | [M:Display.stl corner bosses d=3.18; readme: M2 insert OD3.2 L3] |
| `INSERT_M2_L` | `3.0` | measured | [M:readme] |
| `PD_L` | `115.3` | measured | [M:K159 PDF] display/board length |
| `PD_W` | `62.5` | measured | [M:K159 PDF] display/board width |
| `PD_T` | `5.5` | measured | [M:K159 PDF] overall thickness (front face -> tallest part) |
| `PD_PCB_TOP_FROM_TOP` | `67.9` | measured | [M:K159 PDF] PCB starts 67.9 from the non-USB end |
| `PD_PCB_OVERHANG` | `0.85` | measured | [M:K159 PDF] PCB 'ears' 64.2 wide vs display 62.5 (0.85/side) only for v>=108.9 (USB end); depth 1.4..2.4 |
| `PD_M2_FROM_TOP` | `77.9` | measured | [M:K159 PDF] single M2 standoff, centred across width (30.2 from edge line @61.45 -> 31.25) |
| `PD_M2_STANDOFF_H` | `5.4` | measured | [M:K159 PDF side view] standoff top depth from screen face (PCB back at 2.4 -> 3.0 tall) |
| `PD_M2_STANDOFF_OD` | `4.0` | measured | [M:K159 PDF] d4 circle (thread M2 d2) |
| `PD_MAX_THREAD` | `3.0` | given | [given] screws must engage < 3 mm into the PaperDIY standoff |
| `PD_KEY_FROM_TOP` | `(72.9, 84.9)` | measured | [M:K159 PDF] side keys (12.0 apart; 30.14 dim) on long edge, actuator 1.72 wide |
| `PD_KEY_DEPTH` | `2.95` | measured | [M:K159 PDF side view] actuator centre depth from screen face (2.67..3.23) |
| `PD_KEY_PROTRUDE` | `0.05` | measured | [M:K159 PDF] actuator tip beyond display edge |
| `PD_PWR_FROM_KEYEDGE` | `62.5 - 7.85` | measured | [M:K159 PDF 6.84+1.72/2 from far edge] power button on USB short edge  (=54.65) |
| `PD_PWR_DEPTH` | `3.27` | measured | [M:K159 PDF side view, 2.84..3.69] (inferred to be the power button: the lone short-edge switch) |
| `PD_PWR_PROTRUDE` | `0.7` | measured | [M:K159 PDF ext. line @116.0 vs edge 115.3; kit cap at 0.72] |
| `PD_USB_FROM_KEYEDGE` | `62.5 - 55.25` | measured | [M:K159 PDF 50.78..59.72] USB-C centre 7.25 from the key edge |
| `PD_USB_W` | `8.94` | measured | [M:K159 PDF] |
| `PD_USB_DEPTH` | `(1.64, 4.8)` | measured | [M:K159 PDF side view] |
| `PD_USB_PROTRUDE` | `1.75` | measured | [M:K159 PDF 117.05 - 115.3] |
| `PD_WIN_W` | `105.0` | measured | [M:K159-B kit STL window 105.01 x 59.72 at inner face] |
| `PD_WIN_H` | `59.72` | design choice |  |
| `PD_WIN_FROM_TOP` | `1.39` | measured | [M:K159-B kit STL] window offset from non-USB end |
| `PD_WIN_FROM_USB` | `8.90` | measured | [M:K159-B kit STL] window offset from USB end (FPC/bond area hidden) |
| `PD_ANTENNA_FROM_TOP` | `(70.0, 88.0)` | measured | [M:K159 PDF] WROOM-1 antenna zone, on the long edge opposite the keys |
| `PD_TOP_X` | `55.8` | derived | [D] x of the non-USB end; USB end = 55.8-115.3 = -59.5 |
| `PD_CY` | `0.0` | derived | [D] centred across the lid |
| `FIT` | `0.3` | ASSUMED | [A] display-to-rim clearance per side |
| `RIM_W` | `1.6` | design choice | locating lip width (>= MIN_WALL) |
| `RIM_H` | `1.0` | design choice | rim z 18..19 stays below PCB (z 19.4) and USB-C (z 19.64) |
| `WIN_CHAMFER` | `1.5` | derived | [D: same 1.5/side bevel as original panel window] |
| `PANEL_KEEP_VENTS` | `False` | design choice | original Palma "speaker" slots: filled (left ones sit over the battery pocket) |
| `STRAP_X` | `-22.6` | design choice | strap centre line (standoff at x=-22.1, posts at x=-22.6) |
| `STRAP_W` | `8.0` | design choice |  |
| `STRAP_THK` | `2.0` | design choice |  |
| `STRAP_PAD_DROP` | `0.5` | design choice | pad under the screw reaches the standoff top; elsewhere 0.5 higher (module is 5.45 tall) |
| `STRAP_POST_Y` | `36.0` | design choice |  |
| `STRAP_POST_SIZE` | `6.4` | design choice |  |
| `STRAP_SCREW_LEN` | `4.0` | design choice | ISO 7046 M2x4 countersunk -> 1.5 mm into the standoff (M2x5 -> 2.5 mm, still < 3) |
| `CSK_D` | `4.2` | design choice | countersink for M2 ISO 7046 (head 3.8) |
| `M2_CLEAR` | `2.4` | design choice |  |
| `ROD_D` | `3.0` | design choice |  |
| `ROD_HOLE` | `3.4` | design choice | +0.4 slide clearance |
| `ROD_GAP` | `0.3` | design choice | rest gap rod tip -> actuator |
| `ROD_COLLAR_D` | `5.5` | design choice |  |
| `ROD_COLLAR_T` | `0.8` | design choice | thin enough that a rod pushed fully in still clears the panel cradle |
| `ROD_PROUD` | `1.0` | design choice | rod end proud of the outer wall (plain rods, `ROD_SNAP = None`) |
| `ROD_SNAP` | `play 0.9, catch 0.35, slot 1.0 × 7.5` | design choice | split snap tip: barbs click past the outer face |
| `BATT_L` | `50.0` | ASSUMED | [A] cell length (along y)   default 50x34x10 "~2000 mAh" |
| `BATT_W` | `34.0` | ASSUMED | [A] cell width  (along x) |
| `BATT_T` | `10.0` | ASSUMED | [A] cell thickness |
| `BATT_CLR` | `0.5` | design choice | side clearance and minimum top clearance |
| `BATT_WALL` | `1.6` | design choice |  |
| `BATT_CX` | `76.9` | design choice | bay centre x (between PaperDIY end and right wall) |
| `BATT_CY` | `-4.5` | design choice | shifted -y so the ceiling relief stays clear of the 1.5 mm-thin label recess |
| `MIN_WALL` | `1.6` | design choice |  |
| `USB_PM_W` | `13.0` | ASSUMED | [A] opening width  (along y); narrowed for close screw spacings |
| `USB_PM_H` | `7.0` | ASSUMED | [A] opening height (along z) |
| `USB_PM_R` | `1.0` | design choice |  |
| `USB_PM_Y` | `1.0` | ASSUMED | [A] offset from the PaperDIY port (y=-24) so the cable can loop; 30 mm ears clear the power rod |
| `USB_PM_Z` | `22.5` | design choice |  |
| `USB_PM_SCREW_SPACING` | `28.0` | ASSUMED | [A] default in plate 1 -> MEASURE |
| `USB_PM_SCREW_D` | `3.4` | ASSUMED | [A] M3 clearance (use 2.4 for M2 ears) |
| `USB_PM_WEB` | `1.2` | design choice | minimum wall between the opening and a screw hole |
| `USB_PM_VARIANTS` | `(0, 16, 18, 20, 22, 25, 28, 30)` | design choice | lid-A variants (0 = opening only) |
| `USB_PM_EAR` / `USB_PM_BODY` | `4 past hole, 8 tall, 3 thick` / `13 × 7 × 25` | ASSUMED | connector envelope for the fit check |
| `KB_PORT_BAY` / `_X` / `_Z` / `_R` | `True` / `(70.5, 91.5)` / `(4.0, 15.5)` / `1.5` | design choice | charge-port bay back to the original wall face (`BACK_STYLE = "solid"` only) |
| `KB_PLUG` | `12 × 6.5 overmold at x 81, z 9.4` | ASSUMED | straight USB-C plug for the fit / opening check |
| `ROD_FLAT` | `0.9` | design choice | push-rod flat below the axis (2.4 mm on the bed) |
| `ORIG_REPO` / `ORIG_COMMIT` / `ORIG_SHA256` | `a21bfd6…` | pinned | original phone-enclosure version the build accepts |
| `KB_PORT_WALL` | `"left"` | ASSUMED | [A] TODO measure: left short wall (x=-101) |
| `KB_PORT_Y` | `10.0` | ASSUMED | [A] TODO |
| `KB_PORT_Z` | `6.5` | ASSUMED | [A] TODO centre height (floor top is z=3) |
| `KB_PORT_W` | `10.0` | ASSUMED | [A] TODO |
| `KB_PORT_H` | `5.0` | ASSUMED | [A] TODO |
| `KB_SW_Y` | `-15.0` | ASSUMED | [A] TODO switch notch centre (same wall) |
| `KB_SW_W` | `8.0` | ASSUMED | [A] TODO |
| `KB_SW_BOTTOM_Z` | `5.5` | ASSUMED | [A] TODO notch bottom (wall top there is ~z 9.6) |
| `SPLIT_X_LID` | `-72.0` | design choice | clear of the hinges (/x/ 42..62) and camera window (x>=-68.9) |
| `SPLIT_X_TRAY` | `-72.0` | design choice | clear of the hinges and rear opening (x 72.9..89.1) |
| `SPLIT_X_PANEL` | `-72.0` | design choice | clear of the window bevel (x>=-52.1) |
| `MAX_PIECE` | `175.0` | design choice |  |
| `DOVETAIL` | `dict(neck=6.0, head=10.0, depth=6.0, clr=0.2)` | design choice | glued dovetail keys (0.4 total clearance) |
| `DOVETAIL_Y` | `(-25.0, 0.0, 25.0)` | design choice |  |
| `DOWEL_D` | `3.3` | unused | (old lid seam pads) |
| `LID_PAD` | `dict(...)` | unused | (old lid seam pads; `LID_SEAM = "dovetail"` replaces them) |
| `HINGE_LEN` / `HINGE_WIDTH` / `HINGE_LEAF_T` | `20.0` / `25.0` / `2.0` | measured | [M:Sugatsune spec table] HG-MF08 L / W / t |
| `HINGE_HOLE_PITCH_X` / `HINGE_HOLE_OFF` | `10.0` / `8.0` | measured | [M:Sugatsune spec table] H2 = 10, W2 = 16 |
| `HINGE_BARREL_D` | `5.5` | measured | [M: Sugatsune 3D viewer, ± a few 0.1 mm] |
| `HINGE_AXIS_ABOVE_BACK` / `HINGE_AXIS_Y` | `3.2` / `≈ 54.15` | measured / derived | axis height above the hinge's flat back; real rotation axis |
| `HINGE_X` | `52.0` | design choice | hinge centres at +-52 |
| `HINGE_CLR` | `0.25` | design choice | mortise clearance per side |
| `HINGE_PILOT_HOLES` / `HINGE_PILOT_D` | `True` / `1.8` | design choice | printed pilots for M2 tapping screws |
| `BACK_EXTRA` | `6.5` | design choice | hinge housings 3.0 -> 9.5 mm deep; new back face / axis plane y = 53.0 |
| `BACK_STYLE` | `"solid"` (kit) / `"housings"` (bare) | design choice | whole back face at the hinge plane (`"housings"`: 9.5 mm only behind the hinges) |
| `HOUSING_HALF` / `HOUSING_GUSSET` | `13.5` / `5.5` | design choice | housing 27 mm wide; tapered rib 5.5 mm long each side |
| `LID_RIBS` | `t 1.6, depth 7.0, drop 7.5`, 7 + 7 x positions | design choice | ribs between the long walls and the lid ceiling |
| `STRAP_RAILS` | `x_end 52.3, width 6.0, rib 1.6 deep to z 20.4, feet x 18 / 49` | design choice | rails off the strap hold down the display's far end |
| `STRAP_LEGS` | `gap 0.2, t 2.0, legs y ±22…29, arms y ±20…29.5` | design choice | two legs just past the PCB's inner end (x = −12.1) stop the loose Assembly Kit PCB turning about its single standoff |
| `CLIP_X` / `CLIP_W` / `CLIP_T` / `CLIP_LIP` | `20.0` / `20.0` / `1.6` / `12.0` | design choice | front clip: profile taken at x = 20; 20 mm wide, 1.6 mm thick, lips 12 mm deep |
| `CLIP_CLR` / `CLIP_BUMP` / `CLIP_BUMP_R` | `0.1` / `0.2` / `0.8` | design choice | clip clearance; ridges 0.2 mm into the lid top and tray bottom (spring preload) |
| `MAGNETS` | `d 2.0, l 3.0, depth 4.0, y -44.8, from_end (17, 57)` | design choice | 4 pairs of 2 x 3 mm magnets in the front walls' land, 17 and 57 mm from each end face |
| `MAG_JIG` | `clr 0.15, guide_d 2.15, h 8.0, finger 3.0` | design choice | drilling jig: straddles the front wall, fence on the end face, 8 mm guide bores |
| `MAGNET_HOLES` | `False` | design choice | `True` prints the magnet holes into lid and tray (no jig needed) |
| `Z_PART` | `12.85` | measured | [M] parting line at the back |
| `BACK_ZONE_X` | `62.0` | design choice | old hinge removed and back wall rebuilt for /x/ <= 62 |
| `CORNER_C` | `(95.0, 40.5)` | measured | [M] centre of the r 6 back-corner arcs |
| `LID_HINGE_BOSS` | `w 18, depth 4, z 18.5..27` | design choice | screw boss inside the lid per hinge |
| `HINGE_MOUNT` | `"face"` | design choice | leaves flush in the back face ("parting": folded in the parting plane) |
| `HINGE_COVER` / `COVER_T` / `COVER_RIM` / `COVER_R0` | `True` / `1.0` / `1.5` / `3.6` | design choice | printed covers over the leaves |
| `COVER_FLUSH` / `COVER_SCREWED` / `HINGE_SINK` | `True` / `True` / `1.0` (kit) | design choice | covers flush in a pocket, leaves sunk by `COVER_T`, covers clamped by the hinge screws (bare: glued on top) |
| `COVER_POCKET_CLR` / `COVER_CSK` | `0.15` / `top_d 4.0, hole_d 2.3, cone_d 4.1, cone_h 0.7` | design choice | pocket clearance per side; countersink for the M2 head, cone into the leaf's 4.2 countersink |
| `COVER_RIBS` | `per_side 2, h 0.3, r 0.6` | design choice | tapered crush ribs on the covers' side edges: press fit in the pocket (tight: lower `h`; loose: raise it) |
| `FASTENING` | `"tapping"` | design choice | M2x8 tapping screws into printed pilots ("inserts": M2 heat-set inserts) |
| `SCREW_PILOT_D` / `TAP_SCREW_LEN` | `1.8` / `8.0` | design choice | one tapping-screw size everywhere |
| `LID_CORNER_HOLES` | `(+-92.8, +-38.78)` | measured | [M] panel screw bosses in the lid |
| `LID_FILL_CAMERA` / `CAMERA_FILL` | `True` / `(-69.5, -22.5, -34.8, -17.8)` | design choice | Palma camera window filled |
| `LID_SEAM` | `"dovetail"` | design choice | lid halves joined by 3 glued dovetail keys in the ceiling |
| `TOP_PLATE` | `True` | design choice | blank plate for the lid-top recess |
