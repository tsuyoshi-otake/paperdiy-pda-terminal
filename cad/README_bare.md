# Earlier design: the bare PaperDIY Assembly Kit (`PD_MOUNT = "bare"`)

This is the design before the Complete Kit version: the bare Assembly Kit board on a printed bezel panel with a strap,
snap-in push-rods for the buttons, a 2000 mAh cell in a bay on the panel and a panel-mount USB-C. It still builds with
`PD_MOUNT=bare make verify` (or `PD_MOUNT = "bare"` in `src/params.py`), but the outputs committed to this repository
are the current design, described in [README.md](README.md). Its assembly guide in Japanese is the version of
`ASSEMBLY_ja.md` at commit `7b0e57d`. The changes to the original enclosure are listed in
[README.md](README.md#changes-vs-the-original-for-the-licence-indicate-changes); the parameters are in the table there.

Numbers below (sizes, masses, print times) were measured when this design was current.

## Outputs (bounding boxes in the original assembly frame, mm)

| File | Bbox | Notes |
|---|---|---|
| `out/display_panel_paperdiy.stl` | 195.2 × 86.2 × 11.5 | bezel, unsplit (too big for A1 mini: use the split pieces) |
| `out/display_lid_usbc.stl` | 202.0 × 99.5 × 22.0 | lid, unsplit |
| `out/keyboard_tray.stl` | 202.0 × 99.5 × 12.8 | tray, unsplit |
| `out/paperdiy_strap.stl` | 78.9 × 78.4 × 6.5 | clamps the PaperDIY via its M2 standoff; legs stop the PCB turning, rails hold the display's far end |
| `out/key_pushrod_x2.stl` | 5.5 × 16.9 × 3.6 | print **2** (KEY1/KEY2); snap tip clicks into the front wall |
| `out/power_pushrod.stl` | 42.5 × 5.5 × 3.6 | power button; snap tip clicks into the left wall |
| `out/top_plate_blank.stl` | 56.0 × 10.9 × 1.5 | optional plate for the lid-top recess (accent colour) |
| `out/front_clip.stl` | 20.0 × 13.7 × 33.4 | optional push-on clip for the front edge: keeps the closed lid shut |
| `out/magnet_jig_L.stl` / `_R.stl` | 67.2 × 18.3 × 12.0 | optional drilling jigs for the retrofit magnetic catch |
| `out/hinge_cover_lid_x2.stl` / `hinge_cover_tray_x2.stl` | 23.5 × 1.0 × 10.3 / 23.5 × 1.0 × 8.9 | print 2 each (lid / tray colour) |
| `out/split/lid_A_left.stl` / `lid_B_main.stl` | 35.0 × 93.0 × 22.0 / 173.0 × 99.5 × 22.0 | |
| `out/split/tray_A_left.stl` / `tray_B_main.stl` | 35.0 × 93.0 × 12.8 / 173.0 × 99.5 × 12.8 | |
| `out/split/panel_A_left.stl` / `panel_B_main.stl` | 31.6 × 86.2 × 7.1 / 169.6 × 86.2 × 11.5 | the panel (195.2 mm) does not fit 180 mm in any orientation either |
| `out/split/usb_variants/lid_A_left_usb{16,18,20,22,25,28,30}mm.stl`, `…_usb_noscrew.stl` | 35.0 × 93.0 × 22.0 | lid A for other USB-C hole spacings (28 mm = the default `lid_A_left`) |
| `out/coupons/coupon_*.stl` | ≤ 27 × 21 × 18 | test prints cut from the real parts (see "Test coupons") |
| `out/assembly.json` | | positions for the README renderer |
| `out/print_report.md` | | slicer estimates, wall thickness, tipping check (`tools/print_report.py`) |
| `out/MANIFEST.json` | | fingerprints of all of the above (`tools/manifest.py`) |

All printed parts ≤ 173 mm (limit 175). Every STL above was re-loaded after writing: watertight, consistent winding, a single body.

## Layout (lid frame: x = long axis, y − = front/free edge, y + = hinge, screen faces −z)

* **PaperDIY** sits with its glass on the panel back (z = 18), USB end at **−x** (x −59.5 … 55.8), its key edge facing the
  **front wall**. Reason: the key edge must face a wall without the hinge block, so the antenna edge (opposite the keys)
  faces the hinge side and the USB-C faces the left end wall.
* **Window** 105.0 × 59.72 at the back face (M5's own kit window), 1.5 mm/side bevel to the front like the original.
  It sits 1.39 mm from the non-USB end and 8.90 mm from the USB end of the glass, which hides the FPC/bond area.
  The window centre is at x = +1.9.
* **Retention:** a 1.6 × 1.0 mm locating lip around the glass (0.3 mm clearance). A printed **strap** is screwed to two
  posts on the panel (M2×8 tapping screws into Ø1.8 pilots; `FASTENING = "inserts"` restores M2 heat-set inserts) and clamps the board through its **single M2 standoff** (the drawing shows only one
  M2, centred, 77.9 mm from the non-USB end). The strap is 2.5 mm thick under the countersunk head, so **ISO 7046 M2×4 gives
  1.5 mm of thread in the standoff, and M2×5 gives 2.5 mm. Both are under the 3 mm limit. Do not use M2×6 or longer.**
  `build.py` asserts this. Elsewhere the strap's underside clears the ESP32-S3 module (5.45 mm tall) by 0.45 mm.
  The Assembly Kit's PCB only lies on the back of the display, so one screw would let it turn about the standoff: two arms
  off the strap end in legs 0.2 mm past the PCB's inner end (x = −12.1, at y ±22…29), with their feet 0.2 mm above the
  display's back (`STRAP_LEGS`). They clear the module and leave the middle free for the battery lead. The arms carry on
  as two ribbed rails (6 mm wide, 1.6 mm rib) to x = 52.3, 3.5 mm short of the end of the glass, with feet at x = 18 and
  49 on the display's back (`STRAP_RAILS`), so its far end cannot lift either; the battery lead runs between the rails.
  The strap is now nearly square, so plate 3 is laid out by hand (`placed_layout` in `export_3mf.py`).
* **Buttons:** two D-section push-rods pass through the restored front wall at the real KEY positions
  (x −17.1 / −29.1, z 20.95). A 41.5 mm rod passes through the left end wall to the power button (y +23.4, z 21.27).
  Each rod has a collar inside the wall, an open-top U-cradle on the panel, and a 0.3 mm rest gap to the actuator. The
  outer end is split by a 1.0 mm vertical slot (7.5 mm long) and each half carries a barb (`ROD_SNAP`): pushed in from
  inside the lid, the halves close up, pass the Ø3.4 bore and spring out 0.9 mm past the outer face, so the wall is held
  between collar and barbs and the rod no longer drops out while the panel is fitted (plain rods did). The barbs are
  circles of the bore's radius set 0.35 mm off the axis, so squeezed together they exactly fill the bore; prong strain is
  about 1.2 % with the bore printed 0.1 mm small, and the split part is flattened on top like underneath, so each half
  slices as one 1 mm perimeter loop. The 0.9 mm between barbs and wall is the press travel (rest gap 0.3 + switch
  travel; the plain rods had 0.7 to the cradle), and the collar is 0.8 mm thick so that, pushed fully in, the KEY collars
  still clear the panel cradles by 0.2 mm (checked). To take a rod out, pinch the split tip and push it back in. These are **side-actuated** switches on the board edges, so rods (not front holes) are the only way to reach them.
* **Battery** (integrated, see below) sits at **+x**, at the far end from the antenna. The antenna is on the hinge-side long
  edge, 70–88 mm from the non-USB end, so it is about 70 mm from the cell.
* **USB-C panel mount** goes on the **left end wall** (the wall nearest the PaperDIY port). It is offset to y = +1
  (the port is at y = −24) so the extension cable can loop. A 15 × 1 mm relief in the panel back clears the plug overmold.
  The wall is in **lid piece A**, so the build also writes lid A for hole spacings 16 / 18 / 20 / 22 / 25 / 28 / 30 mm and
  without screw holes (`3mf/usb_variants/`): measure your cable and print the matching lid A, nothing else changes
  (`build.py` asserts that lid B is identical for every variant). The opening narrows for close spacings so 1.2 mm of wall
  stays between it and each hole (16 mm: 10.2 wide, 18 mm: 12.2). Behind the wall the inner wall/ceiling fillet is squared
  over the ear span, so ears up to the full 9 mm cavity height seat flat. Each variant is checked against a rough connector
  envelope (ears 4 mm past each hole, 8 mm tall, 3 mm thick, 13 × 7 × 25 body): 0 mm³ with the lid, panel and power rod.
  Published example: SparkFun CAB-15455 (18 mm, M3, flange 26.4 × 8, drawing ACCA-2517).

### Hinge: two torque hinges flush in the back face
The original hinge (a knuckle on an axis at y = 54, z = 7.5 inside a 14 mm barrel strip behind the case, two printed threaded
knob-pins, M3×40 cores, O-rings, friction set by how tight the knobs are) is replaced:
* **Hinges:** 2 × **Sugatsune HG-MF08-BL** (free-stop, 0.0784 N·m ±25 % each, POM, 20 × 25 × 2.0, holes Ø2.4 with Ø4.2
  countersink, hole pitch 10 along / 16 across the axis — Sugatsune's spec table). Estimated lid torque (lid side ≈ 200 g
  from the sliced masses plus PaperDIY, 2000 mAh cell and cable, centre of mass ≈ 50 mm from the axis) is ≈ 0.1 N·m with
  the lid horizontal and 0.02–0.07 N·m at normal viewing angles, so the pair holds the lid anywhere and still opens easily. HG-MF15 (0.147 N·m) is 30 mm long with
  M3 holes: it needs `HINGE_LEN = 30`, `HINGE_HOLE_PITCH_X = 20`.
* **Axis** at the outer back edge, on the parting line (z = 12.85). Sugatsune's 3D model shows a flat back and a barrel
  (≈ Ø5.5) standing on the front only, its axis ≈ 3.2 mm above the flat back (`HINGE_AXIS_ABOVE_BACK`). Seated flat side
  down in the 2.05 mm mortise, the axis is at y ≈ 54.15, ≈ 1.15 mm outside the back face (y = 53.0); every motion check, the
  tipping estimate and the renders rotate about that real axis. The barrel strip, knuckle, ears and trough are
  removed (`BACK_ZONE_X` = ±62 is cut back and rebuilt from the plain back-wall profile): the case is 93 mm deep (99.5 mm
  over the hinge housings) instead of 108.
* **Hinge housings** (`BACK_STYLE = "housings"`): the screws need 9.5 mm of back wall (2 mm mortise + 6 mm of M2×8 +
  1.5 mm), but only behind the hinges. Each hinge gets a 27 mm wide housing (`HOUSING_HALF`) that carries the back-wall
  profile, top / bottom chamfers included, 6.5 mm further back, and a tapered rib on each side (`HOUSING_GUSSET`, 5.5 mm
  long in plan) blends it into the original 3 mm wall. Everywhere else the back wall, the keyboard pocket and the lid
  interior are the original. Inside the lid, 14 triangular ribs (`LID_RIBS`: 1.6 mm thick, 7 mm along the ceiling, 7.5 mm
  down the wall) tie the long walls to the ceiling, placed clear of the strap, the key push-rods and the USB-C cable;
  they are part of the lid in every interference check. `BACK_STYLE = "solid"` rebuilds the v0.3 design (whole back
  wall 9.5 mm). Compared with it the solid volume of lid and tray is 13 % lower, but the sliced mass only 8 g (lid
  85 → 81 g, tray 64 → 60 g): the slicer prints the core of a thick wall with 15 % infill anyway, so the saving comes from
  the smaller outside, not from the thinner wall.
* **Mortises:** each leaf sits in a 2.0 mm pocket (0.25 mm clearance) so it is flush with the back face; a slot along the axis
  takes the barrel (up to ~Ø6.2, axis tolerated up to 0.8 mm inside the face). Under the tray leaves the bottom chamfer is
  squared off and the mortise runs out through the bottom edge (no 0.1 mm skin).
* **Screws:** 8 × **M2×8 countersunk tapping screws** (head in the leaf countersink, 6 mm into the wall). 7.5 mm of wall
  behind each leaf, so no bosses are needed; Ø1.8 pilot holes at the catalogue hole positions stop 1.5 mm short of the
  keyboard pocket / lid interior.
* **Positions:** x = ±52 (20 mm long each), clear of the split at x = −72 (and its dovetail keys) and the tray's rear
  opening (x ≥ 72.9).
* **Cover plates** (`out/hinge_cover_lid_x2.stl`, `out/hinge_cover_tray_x2.stl`, 1.0 mm, print in the case colours):
  glued over each leaf after the screws are in, overlapping the case by 1.5 mm (glue land), starting 3.6 mm from the axis so
  the barrel stays free (0.85 mm). They stand 1.0 mm proud of the back face. The axis position matters: if it sat inside
  the back face the lid's back wall would sweep into the tray (axis 0.5 mm inside: contact at 132°, 1.0 mm inside: 91°);
  with the measured axis 1.15 mm outside, nothing touches from 0 to 180°. The hinge coupon checks this with a real hinge.
* **Checks (`build.py`):** the lid + panel (+ covers) rotated about the real axis does not touch the tray (+ covers) from
  0 to 180°; on a table the lid's top-back edge reaches the table at about **150°**, which is the opening limit.
  Hinge envelopes (flat back on the mortise floor, barrel around the real axis) and covers vs lid / tray: 0 mm³.
* `HINGE_MOUNT = "parting"` is an alternative: the leaves lie folded in the parting plane inside 14.5 mm back walls
  (case 8 mm deeper). Closed, only the barrels show, but open, the leaves and screw heads are visible under the screen.

### Keyboard charge port
The original tray has an opening in its 3 mm back wall at x 72.9–89.1, open from the lip at z ≈ 6.0 up to the lid
(z 12.78), probably for the CACOE charge port. The back wall there is the original 3 mm, so any straight plug whose
overmold fits the original opening (≈ 16 × 6.8 mm) fits. `build.py` checks a 12 × 6.5 mm overmold (0 mm³ against tray and
closed lid) and sweeps the lid: **with that plug in, the lid opens to 119°**; beyond that the lid's back face swings down
behind the tray into the plug. (With `BACK_STYLE = "solid"` the 9.5 mm wall would turn the opening into a tunnel; there
`KB_PORT_BAY` cuts a bay back to the original wall face and the limit drops to 95°.)

### Battery: integrated into the panel (no separate `battery_carrier.stl`)
The bay frame (1.6 mm walls, 0.5 mm clearance, wire notch toward the PaperDIY) is printed on the panel back. It prints
face-down with no supports, needs no fasteners, and is held in place when the panel is screwed to the lid.
**Fit check, from the parameters:** the lid cavity between the panel back and the ceiling is **9.0 mm**. The default
50 × 34 × **10** mm cell needs 10.5 mm (with 0.5 mm clearance), so it does **not** fit unmodified. The build therefore cuts a
**0.75 mm pocket into the panel back** and a **0.75 mm relief into the lid ceiling** (both left at 2.25 mm, ≥ 1.6).
The cell then has 0.5 mm of top clearance. The largest cell thickness possible without going under 1.6 mm walls is
**11.3 mm**. For cells ≤ 8.5 mm both cuts vanish automatically. The ceiling relief stops 0.34 mm short of the 1.5 mm-thin
label recess (the bay is shifted to y = −4.5 for that reason). The original lid vents over the bay are kept, so they open
onto the cell. Add a 0.5 mm foam pad on the cell.
One original Palma corner rib in the lid flares to y = −30.2 near the ceiling, so the frame wall is notched there.

### Front clip (optional accessory)
The torque hinges hold any angle but do not latch, so a closed case can open in a bag. `out/front_clip.stl` is a U that is
pushed onto the front edge of the closed case; nothing else changes. Its profile is the outline of the closed lid + tray at
x = `CLIP_X` (front face and both 3 mm chamfers) with `CLIP_CLR` all round, the lips reach `CLIP_LIP` = 12 mm back over the
lid top and the tray bottom, and a ridge 2 mm from each lip tip presses `CLIP_BUMP` = 0.2 mm into the case, so the clip stays
on by its own spring. `build.py` checks it without the ridges at x = −75, −50, 20, 50 and 80 (0 mm³ against lid, tray and
the key push-rods) and logs the ridges' intended overlap. Keep it off the two key push-rods (x −29 and −17), which stand
1 mm proud of the front face. It prints standing on its U profile (layers across the width), so the bends flex along the
extrusion lines rather than across layers.

### Magnetic catch (optional retrofit)
Inside the closed case there is no room for a catch (the panel fills the lid, the keyboard fills the tray), but the front
walls of lid and tray meet on a ~1 mm flat land at z = 8.0 (y −45.5 … −44.5, chamfered either side). Four pairs of
2 × 3 mm magnets go into 4 mm deep, Ø2 holes in that land at x = ±44 and ±84 (17 and 57 mm from each end face), centred
at y = −44.8, which leaves 0.7 mm to the front face and 0.3 mm to the hidden inner face; the rim just touches the seam's
chamfer. The holes are drilled with printed jigs (`magnet_jig_L/R`) that straddle the front wall with two fingers and
stop against the end face, so lid and tray holes are coaxial; on the upside-down lid the other hand fits the same corner.
`build.py` checks both jigs on both parts (0 mm³) and logs how much of each hole lies in material. Magnets are set flush
with epoxy by letting them jump to a steel ruler laid on the land. Estimated holding force about 2 N per pair in contact,
≈ 8 N at the front edge for four pairs (about 0.8 N·m with the 99 mm lever, five times the hinges' 0.16 N·m).
`MAGNET_HOLES = True` prints the holes into lid and tray instead.

## Splitting for the A1 mini
* **Lid** at x = −72: clear of the hinges and their housings (|x| 33–71). Joined like the tray and panel: **3 glued dovetail keys** through
  the 3 mm ceiling (y = −25 / 0 / +25; the camera window that used to sit there is filled) plus butt-glued front / back
  walls. The hinges are in piece B, so the seam carries no hinge load. (The earlier seam pads with dowels, inserts and
  socket screws are gone.)
* **Tray** at x = −72: clear of the hinges and the rear opening. The tray interior is fully occupied by the
  keyboard and the floor is only 3 mm, so dowels or inserts would break the ≥ 1.6 mm wall rule or the outer silhouette.
  The joint is **3 glued dovetail keys** through the floor (neck 6, head 10, depth 6, 0.2 mm/side clearance) plus butt-glued
  walls. Use CA or epoxy.
* **Panel** at x = −72: same dovetail keys. Each piece keeps two of the original corner screws.

## Print-ready 3MF (A1 mini)
`3mf/plate0_test_coupons.3mf` (print first), `plate1_lid.3mf` (lid A+B, 2 lid hinge covers), `plate2_tray.3mf` (tray A+B,
2 tray hinge covers), `plate3_panel_parts.3mf` (panel A+B, strap, 3 push-rods, optional top plate) and the optional
`plate4_front_clip.3mf` (two front clips, one is a spare) and `plate5_magnet_jigs.3mf` (drilling jigs L and R for the
magnetic catch): every part already
in print orientation and laid out on a 180 x 180 mm plate, grouped by colour. `3mf/usb_variants/` holds lid A alone for
the other USB-C hole spacings. No supports are needed. Regenerate with `python3 src/export_3mf.py` after `src/build.py`.

Estimates from `tools/print_report.py` (PrusaSlicer 2.7 CLI with an approximation of Bambu Studio's A1 mini 0.20 mm
Standard + PLA profile, 3 walls, 15 % gyroid; Bambu Studio's own numbers will differ somewhat):

| Plate | Time | PLA |
|---|---|---|
| 0 test coupons | 0 h 28 min | 12 g |
| 1 lid | 2 h 10 min | 81 g |
| 2 tray | 1 h 31 min | 60 g |
| 3 panel, strap, rods, top plate | 1 h 08 min | 37 g |
| 1–3 together | 4 h 48 min | 179 g |
| 4 front clips (optional) | 0 h 10 min | 4 g |
| 5 magnet drilling jigs (optional) | 0 h 17 min | 8 g |

With 2 wall loops (Bambu Studio's default) instead of 3, plates 1–3 come to ≈ 163 g and 4 h 32 min: the 3 mm walls then
get a sparse core, and the screw pilots get 2 loops as well.

The slicer's own stability check reports nothing for plates 1 and 2. On plate 3 it flags the thin push-rods for low bed
adhesion (keep Bambu Studio's brim type on Auto, its default, or give them a brim), and on plate 4 the clips, which stand
20 mm tall on a 1.6 mm U (same remedy); on plate 0 also the panel-corner coupon,
whose 5 mm counterbore is bridged 1.5 mm above the bed, as in the real panel.

### Test coupons (`plate0_test_coupons.3mf`, ~30 min)
Cut from the real parts and printed in the same orientation, so they show how your printer handles each fit:
* `coupon_hinge_tray` + `coupon_hinge_lid`: a hinge seat from tray and lid (mortise, barrel slot, 4 pilot holes). Put a real
  HG-MF08 in: the leaves must sit flush, the barrel must turn freely, M2×8 screws must bite without splitting.
* `coupon_dovetail_A` + `_B`: one dovetail key (0.2 mm per side). It should slide in by hand without play.
* `coupon_corner_lid` + `coupon_corner_panel`: a panel corner screw (counterbore, Ø1.8 pilot in the lid boss).
* `coupon_keywall_lid` + a key push-rod: pushed in from the inner side, the rod must click in and then slide freely in the
  bore printed upside down in the lid wall.
* One lid cover and one tray cover: they must lie flat on the leaves.
If something is tight or loose, change `DOVETAIL["clr"]`, `HINGE_CLR`, `HINGE_BARREL_D`, `HINGE_PILOT_D`, `SCREW_PILOT_D` or
`ROD_HOLE` (and `ROD_SNAP["catch"]` if the rod will not click in, or falls out again) and rebuild.

## Print orientation (suggested)
* Lid pieces: **top face down** (the ceiling is flat at z = 30). No supports (the knuckle that needed them is gone).
* Panel pieces: **screen face down** (z = 15 on the bed). Lip, posts, cradles and bay frame grow upward with no supports.
* Tray pieces: **floor down** (as modelled).
* Strap: **top face down** (countersinks open toward the bed, pad up). Push-rods: **flat (D) side down**; the flat sits
  0.9 mm below the axis (2.4 mm wide on the bed) and the panel cradles are raised to match. The snap slot then runs
  vertically, so the two halves flex in the bed plane along their perimeters.
* Hinge covers and top plate: **visible face down**, like the lid, so they match its texture.
* Suggested process (Bambu Studio): 0.20 mm Standard, PLA, textured PEI, **3 wall loops** (material around the screw
  pilots), 15 % gyroid, no supports, brim type Auto (default).

## Hardware
* **14× M2×8 countersunk tapping screws** (plastic type): 4 panel corners, 2 strap ends, 8 hinges.
* **1× M2×4 countersunk machine screw** (ISO 7046) into the PaperDIY standoff — **max M2×5** (3 mm thread limit).
* **2× Sugatsune HG-MF08** (-WT or -BL; hidden under the covers).
* CA gel or epoxy (dovetail seams, hinge covers, top plate); thin double-sided tape and 0.5 mm foam (battery, keyboard).
* Panel-mount USB-C extension (male–female, screw ears, **data and CC lines passed through**), with its own screws / nuts.
* 1S LiPo with protection PCB, ≤ 50 × 34 × 11.3 mm, JST **SH1.0-2P** lead (PaperDIY battery input per M5 docs) —
  **check the polarity** before plugging it in.
* `FASTENING = "inserts"` switches the panel corners and strap posts back to M2 heat-set inserts (Ø3.2 L3) with M2 machine
  screws, for a panel that will be opened often.

## Assumptions / placeholders — **measure on the real part**
* **Hinge barrel / axis:** read off Sugatsune's 3D viewer, not a drawing (Ø ≈ 5.5, axis ≈ 3.2 mm above the flat back).
  The slot takes a barrel up to ~Ø6.2. The opening range depends on the axis staying outside the back face (it is ≈ 1.15 mm
  outside); join the hinge coupons with a real hinge and open them past 150° before printing lid and tray.
* **TODO keyboard:** first fit the CACOE in the tray and check that the original openings reach its charge port
  and switch. Only if they don't: `KB_CUTS_ENABLED = True` and measure `KB_PORT_*` / `KB_SW_*` (placeholders: 10 × 5 opening
  at y = +10, z = 6.5 and an 8 mm notch down to z = 5.5 at y = −15, left short wall). Its weight decides the tipping angle.
* **USB-C panel mount:** 13 × 7 opening, 2 × Ø3.4 holes at y = +1, z = 22.5; **28 mm spacing in plate 1**, other spacings
  as lid-A variants. Measure your cable (M2 ears → set `USB_PM_SCREW_D = 2.4` and rebuild). The plug overmold at the
  PaperDIY end must be ≤ ~6.4 mm thick (or use a right-angle plug).
* **Power button identity** is inferred: it is the lone switch on the USB short edge. The two long-edge switches are KEY1/KEY2,
  but which is which is not determined.
* Actuator heights (depth 2.95 / 3.27) come from the drawing's side view (± ~0.3). Rod gaps of 0.3 mm absorb this.
  The power actuator protrusion (0.7) comes from an extension line and the kit cap position.
* The ED047TC1 active area is **not** taken from a datasheet. The window is M5's kit window, which shows some inactive border.
* Battery default 50 × 34 × 10 is the requested default, not a specific cell. Check charge current vs. cell size (not verified).
* Fits: 0.3 mm lip, 0.4 mm on rod bores, 0.2 mm/side on dovetails, 0.25 mm/side on the hinge mortises, Ø1.8 screw pilots.
  Tune for your printer.

## Does it tip over when open?
`tools/print_report.py` adds the sliced part masses, the PaperDIY (26.4 g, M5Stack spec), a 38 g cell and a 10 g cable
(both assumed) and finds the lid side at **≈ 198 g** with its centre of mass 53 mm in front of the hinge axis when closed;
the printed base is ≈ 64 g. The device rests on the back edge of the tray (y = 51.0). Opened past 90° the lid's centre of
mass moves behind that edge, so the keyboard has to supply the counterweight:

| Opening | 100° | 110° | 120° | 130° | 140° | 150° (lid touches the table) |
|---|---|---|---|---|---|---|
| Keyboard needed | 30 g | 63 g | 93 g | 119 g | 140 g | 156 g |

**Weigh the CACOE keyboard.** At 156 g or more it never tips; lighter keyboards are fine up to the angle in the table.

## Verification actually performed
STL re-load watertight / single body / bbox ≤ 175 mm for every part. Zero-volume interference (closed assembly) between
lid, panel, strap, rods, a PaperDIY envelope built from the drawing (glass, PCB + USB-end ears, module, standoff, USB-C,
actuators) and the battery box; hinge envelopes vs lid / tray; lid + panel (+ covers) rotated 0–180° about the hinge axis vs
the tray (+ covers); a 12 × 6.5 mm charge plug vs tray and lid, closed and opening; a USB-C connector envelope vs lid,
panel and power rod for every lid-A variant. Ray scan of the restored lid walls against the original. **PrusaSlicer**
slice of every plate (time, filament, its stability check), wall thickness by ray casting, tipping estimate. Two builds
byte-identical. Renders inspected visually.
**Not done:** no physical print or test fit, no FEA of the strap or seams; the slicer profile only approximates the A1 mini.
