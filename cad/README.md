# PaperDIY PDA clamshell — printable CAD (derivative of unkyulee/phone-enclosure)

A Boox-Palma-free version of Un Kyu Lee's "PDA Terminal": the lid holds an **M5Stack PaperDIY** (4.7" e-paper, ESP32-S3)
behind a new bezel panel, plus a 1S LiPo, and gets a panel-mount USB-C. The original knob-and-pin hinge is replaced by
**two free-stop torque hinges (Sugatsune HG-MF08) recessed flush into the back face, under printed cover plates**, so only
the hinge barrels show. The keyboard tray (CACOE mini BT keyboard) keeps the
original openings; a bay in the thickened back wall keeps the charge port as reachable as in the original. Every part is
also split for a **Bambu Lab A1 mini (180 mm bed)** and joined with glued dovetail keys; nothing needs supports. All case
fasteners are **M2×8 countersunk tapping screws into printed pilot holes** (14), plus one M2×4 machine screw into the
PaperDIY standoff: no heat-set inserts, dowels or socket screws. Only the small lid piece A depends on the USB-C cable you
buy, and it comes pre-built for eight hole spacings. A **test-coupon plate** checks the fits on your printer in ~30 min
before the long prints. Bill of materials, print settings and assembly order (Japanese): [ASSEMBLY_ja.md](ASSEMBLY_ja.md);
parts list as CSV: [bom.csv](bom.csv).

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
  fixed timestamps. Another machine can round the last digit differently: on the GitHub Actions runner 32 of the 44
  files were byte-identical and the other 12 matched in geometry only.
* **Recorded:** `out/MANIFEST.json` holds the SHA-256, volume, bounding box and triangle count of every output.
  `tools/manifest.py --check` accepts byte differences only when the geometry matches to 0.01 mm / 0.01 %.
* **CI:** `.github/workflows/build.yml` runs `make verify`, the slicer report, the firmware build (compared byte for byte
  with `firmware/prebuilt/`) and the host tests.

## Outputs (bounding boxes in the original assembly frame, mm)

| File | Bbox | Notes |
|---|---|---|
| `out/display_panel_paperdiy.stl` | 195.2 × 86.2 × 11.5 | bezel, unsplit (too big for A1 mini: use the split pieces) |
| `out/display_lid_usbc.stl` | 202.0 × 99.5 × 22.0 | lid, unsplit |
| `out/keyboard_tray.stl` | 202.0 × 99.5 × 12.8 | tray, unsplit |
| `out/paperdiy_strap.stl` | 8.0 × 78.4 × 2.5 | clamps the PaperDIY via its M2 standoff |
| `out/key_pushrod_x2.stl` | 5.5 × 15.9 × 3.7 | print **2** (KEY1/KEY2) |
| `out/power_pushrod.stl` | 41.5 × 5.5 × 3.6 | power button |
| `out/top_plate_blank.stl` | 56.0 × 10.9 × 1.5 | optional plate for the lid-top recess (accent colour) |
| `out/hinge_cover_lid_x2.stl` / `hinge_cover_tray_x2.stl` | 23.5 × 1.0 × 10.3 / 23.5 × 1.0 × 8.9 | print 2 each (lid / tray colour) |
| `out/split/lid_A_left.stl` / `lid_B_main.stl` | 35.0 × 99.5 × 22.0 / 173.0 × 99.5 × 22.0 | |
| `out/split/tray_A_left.stl` / `tray_B_main.stl` | 35.0 × 99.5 × 12.8 / 173.0 × 99.5 × 12.8 | |
| `out/split/panel_A_left.stl` / `panel_B_main.stl` | 31.6 × 86.2 × 7.1 / 169.6 × 86.2 × 11.5 | the panel (195.2 mm) does not fit 180 mm in any orientation either |
| `out/split/usb_variants/lid_A_left_usb{16,18,20,22,25,28,30}mm.stl`, `…_usb_noscrew.stl` | 35.0 × 99.5 × 22.0 | lid A for other USB-C hole spacings (28 mm = the default `lid_A_left`) |
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
* **Buttons:** two D-section push-rods pass through the restored front wall at the real KEY positions
  (x −17.1 / −29.1, z 20.95). A 41.5 mm rod passes through the left end wall to the power button (y +23.4, z 21.27).
  Each rod has a collar inside the wall that stops it falling out, an open-top U-cradle on the panel, and a 0.3 mm rest gap
  to the actuator. These are **side-actuated** switches on the board edges, so rods (not front holes) are the only way to reach them.
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
  removed (`BACK_ZONE_X` = ±62 is cut back and rebuilt from the plain back-wall profile): the case is 99.5 mm deep
  instead of 108.
* **Back walls thickened outward** 3.0 → 9.5 mm (outer half of the wall, the top / bottom chamfers and the rounded back
  corners move 6.5 mm back; the keyboard pocket and the lid interior are unchanged), so M2×8 screws fit on both sides.
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
  0 to 180°; on a table the lid's top-back edge reaches the table at about **154°**, which is the opening limit.
  Hinge envelopes (flat back on the mortise floor, barrel around the real axis) and covers vs lid / tray: 0 mm³.
* `HINGE_MOUNT = "parting"` is an alternative: the leaves lie folded in the parting plane inside 14.5 mm back walls
  (case 8 mm deeper). Closed, only the barrels show, but open, the leaves and screw heads are visible under the screen.

### Keyboard charge port: bay in the back wall
The original tray has an opening in its 3 mm back wall at x 72.9–89.1, open from the lip at z ≈ 6.0 up to the lid
(z 12.78), probably for the CACOE charge port. Thickening the back wall to 9.5 mm turned it into a 9.5 mm tunnel that a
plug overmold would have to fit through. A **bay** (x 70.5–91.5, z 4.0–15.5, r 1.5) is now cut from the outside back to
the original wall face (y = 46.5), in the tray and 2.65 mm up into the lid wall, so the plug meets the same 3 mm wall as in
the original: any straight plug whose overmold fits the original opening (≈ 16 × 6.8 mm) fits. `build.py` checks a
12 × 6.5 mm overmold (0 mm³ against tray and closed lid) and sweeps the lid: **with that plug in, the lid opens to 95°**;
beyond that the lid's back face swings down behind the tray into the plug. Charge with the lid closed or up to 95°.
Both bay faces print without overhang (open at the top in each part's print orientation).

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

## Changes vs. the original (for the licence "indicate changes")
1. **Display Panel:** Palma window, Palma button slots and both vent grilles filled. New PaperDIY window, locating lip, strap
   posts, push-rod cradles, battery bay, USB-plug relief. Outline and the 4 corner screw holes are untouched (original mesh kept).
2. **Display (lid):** front-wall Palma side-button slot (incl. ceiling-edge notch) and right-wall Palma USB opening **closed**,
   rebuilt by extruding the adjacent original wall profile. A ray scan found **0 deviations** from the original outer surface
   (flat wall at y = −46.5 / x = +101, same top chamfer). Added: panel-mount USB-C opening + 2 screw holes (inner fillet
   squared behind them) and the power-rod bore (left wall), 2 key-rod bores (front wall), battery ceiling relief, the upper
   2.65 mm of the keyboard charge-port bay. **Hinge knuckle removed**, back wall rebuilt and
   thickened to 9.5 mm, two hinge mortises with barrel slot and pilot holes (see "Hinge"). **Camera window filled**
   (flat top). The 4 corner insert holes are refilled and re-drilled as Ø1.8 pilots for M2×8 tapping screws.
   Label recess, vents and corner bosses otherwise unchanged.
3. **Keyboard (tray):** **hinge ears and trough removed**, back wall rebuilt and thickened to 9.5 mm, two hinge mortises
   with barrel slot and pilot holes, bottom chamfer squared under the leaves, charge-port bay back to the original wall
   face. Keyboard cut-outs otherwise unchanged by default
   (`KB_CUTS_ENABLED = False`). The original right-wall (y 26.3–36.7) and
   rear-wall (x 72.9–89.1) openings are kept; they are probably the CACOE port/switch cut-outs of the original design (not
   verified). If the real keyboard's port/switch are elsewhere, set `KB_CUTS_ENABLED = True`, measure `KB_*` and rebuild.
4. New parts: strap, 3 push-rods, 4 hinge covers, optional top plate, test coupons. Split versions of lid / tray / panel,
   lid-A variants for other USB-C cables. The original knobs and label are not used.

## Splitting for the A1 mini
* **Lid** at x = −72: clear of the hinges (|x| 42–62). Joined like the tray and panel: **3 glued dovetail keys** through
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
2 tray hinge covers) and `plate3_panel_parts.3mf` (panel A+B, strap, 3 push-rods, optional top plate): every part already
in print orientation and laid out on a 180 x 180 mm plate, grouped by colour. `3mf/usb_variants/` holds lid A alone for
the other USB-C hole spacings. No supports are needed. Regenerate with `python3 src/export_3mf.py` after `src/build.py`.

Estimates from `tools/print_report.py` (PrusaSlicer 2.7 CLI with an approximation of Bambu Studio's A1 mini 0.20 mm
Standard + PLA profile, 3 walls, 15 % gyroid; Bambu Studio's own numbers will differ somewhat):

| Plate | Time | PLA |
|---|---|---|
| 0 test coupons | 0 h 29 min | 13 g |
| 1 lid | 2 h 15 min | 85 g |
| 2 tray | 1 h 37 min | 64 g |
| 3 panel, strap, rods, top plate | 1 h 00 min | 34 g |
| 1–3 together | 4 h 50 min | 183 g |

The slicer's own stability check reports nothing for plates 1 and 2. On plate 3 it flags the thin push-rods for low bed
adhesion (keep Bambu Studio's brim type on Auto, its default, or give them a brim); on plate 0 also the panel-corner coupon,
whose 5 mm counterbore is bridged 1.5 mm above the bed, as in the real panel.

### Test coupons (`plate0_test_coupons.3mf`, ~30 min)
Cut from the real parts and printed in the same orientation, so they show how your printer handles each fit:
* `coupon_hinge_tray` + `coupon_hinge_lid`: a hinge seat from tray and lid (mortise, barrel slot, 4 pilot holes). Put a real
  HG-MF08 in: the leaves must sit flush, the barrel must turn freely, M2×8 screws must bite without splitting.
* `coupon_dovetail_A` + `_B`: one dovetail key (0.2 mm per side). It should slide in by hand without play.
* `coupon_corner_lid` + `coupon_corner_panel`: a panel corner screw (counterbore, Ø1.8 pilot in the lid boss).
* `coupon_keywall_lid` + a key push-rod: the rod must slide freely in the bore printed upside down in the lid wall.
* One lid cover and one tray cover: they must lie flat on the leaves.
If something is tight or loose, change `DOVETAIL["clr"]`, `HINGE_CLR`, `HINGE_BARREL_D`, `SCREW_PILOT_D` or `ROD_HOLE` and rebuild.

## Print orientation (suggested)
* Lid pieces: **top face down** (the ceiling is flat at z = 30). No supports (the knuckle that needed them is gone).
* Panel pieces: **screen face down** (z = 15 on the bed). Lip, posts, cradles and bay frame grow upward with no supports.
* Tray pieces: **floor down** (as modelled).
* Strap: **top face down** (countersinks open toward the bed, pad up). Push-rods: **flat (D) side down**; the flat sits
  0.9 mm below the axis (2.4 mm wide on the bed) and the panel cradles are raised to match.
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
(both assumed) and finds the lid side at **≈ 199 g** with its centre of mass 50 mm in front of the hinge axis when closed;
the printed base is ≈ 68 g. The device rests on the back edge of the tray (y = 51.0). Opened past 90° the lid's centre of
mass moves behind that edge, so the keyboard has to supply the counterweight:

| Opening | 100° | 110° | 120° | 130° | 140° | 154° (lid touches the table) |
|---|---|---|---|---|---|---|
| Keyboard needed | 31 g | 62 g | 91 g | 115 g | 134 g | 153 g |

**Weigh the CACOE keyboard.** At 153 g or more it never tips; lighter keyboards are fine up to the angle in the table.

## Verification actually performed
STL re-load watertight / single body / bbox ≤ 175 mm for every part. Zero-volume interference (closed assembly) between
lid, panel, strap, rods, a PaperDIY envelope built from the drawing (glass, PCB + USB-end ears, module, standoff, USB-C,
actuators) and the battery box; hinge envelopes vs lid / tray; lid + panel (+ covers) rotated 0–180° about the hinge axis vs
the tray (+ covers); a 12 × 6.5 mm charge plug vs tray and lid, closed and opening; a USB-C connector envelope vs lid,
panel and power rod for every lid-A variant. Ray scan of the restored lid walls against the original. **PrusaSlicer**
slice of every plate (time, filament, its stability check), wall thickness by ray casting, tipping estimate. Two builds
byte-identical. Renders inspected visually.
**Not done:** no physical print or test fit, no FEA of the strap or seams; the slicer profile only approximates the A1 mini.

## Licence & attribution
Derived from **"The PDA Terminal" / phone-enclosure by Un Kyu Lee** — https://github.com/unkyulee/phone-enclosure —
licensed **CC BY-NC 4.0** (https://creativecommons.org/licenses/by-nc/4.0/). This derivative is under the same licence,
non-commercial use only. Changes are listed above. The PaperDIY is a product of M5Stack; its dimensions come from M5Stack's
published drawing and structure files.

## Parameters (`src/params.py`, all of them)
| Parameter | Value | Status | Note / source |
|---|---|---|---|
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
| `ROD_COLLAR_T` | `1.2` | design choice |  |
| `ROD_PROUD` | `1.0` | design choice | rod end proud of the outer wall |
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
| `KB_PORT_BAY` / `_X` / `_Z` / `_R` | `True` / `(70.5, 91.5)` / `(4.0, 15.5)` / `1.5` | design choice | charge-port bay back to the original wall face |
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
| `BACK_EXTRA` | `6.5` | design choice | back walls 3.0 -> 9.5 mm; new back face / axis plane y = 53.0 |
| `Z_PART` | `12.85` | measured | [M] parting line at the back |
| `BACK_ZONE_X` | `62.0` | design choice | old hinge removed and back wall rebuilt for /x/ <= 62 |
| `CORNER_C` | `(95.0, 40.5)` | measured | [M] centre of the r 6 back-corner arcs |
| `LID_HINGE_BOSS` | `w 18, depth 4, z 18.5..27` | design choice | screw boss inside the lid per hinge |
| `HINGE_MOUNT` | `"face"` | design choice | leaves flush in the back face ("parting": folded in the parting plane) |
| `HINGE_COVER` / `COVER_T` / `COVER_RIM` / `COVER_R0` | `True` / `1.0` / `1.5` / `3.6` | design choice | printed covers over the leaves |
| `FASTENING` | `"tapping"` | design choice | M2x8 tapping screws into printed pilots ("inserts": M2 heat-set inserts) |
| `SCREW_PILOT_D` / `TAP_SCREW_LEN` | `1.8` / `8.0` | design choice | one tapping-screw size everywhere |
| `LID_CORNER_HOLES` | `(+-92.8, +-38.78)` | measured | [M] panel screw bosses in the lid |
| `LID_FILL_CAMERA` / `CAMERA_FILL` | `True` / `(-69.5, -22.5, -34.8, -17.8)` | design choice | Palma camera window filled |
| `LID_SEAM` | `"dovetail"` | design choice | lid halves joined by 3 glued dovetail keys in the ceiling |
| `TOP_PLATE` | `True` | design choice | blank plate for the lid-top recess |
