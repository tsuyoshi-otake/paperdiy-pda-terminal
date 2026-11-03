# PaperDIY PDA clamshell — printable CAD (derivative of unkyulee/phone-enclosure)

A Boox-Palma-free version of Un Kyu Lee's "PDA Terminal": the lid holds an **M5Stack PaperDIY** (4.7" e-paper, ESP32-S3)
behind a new bezel panel, plus a 1S LiPo, and gets a panel-mount USB-C. The keyboard tray (CACOE mini BT keyboard) keeps the
original openings by default; optional charge-port / switch cut-outs can be enabled once measured. Every part is also split for a **Bambu Lab A1 mini (180 mm bed)**.

## Run

```
pip install trimesh manifold3d numpy shapely rtree pillow scipy
git clone https://github.com/unkyulee/phone-enclosure ~/phone-enclosure   # original STLs (read-only input)
python3 src/build.py     # run from this cad/ folder, ~10 s; writes out/, out/split/, renders/
```
Set `PHONE_ENCLOSURE_STL=/path/to/phone-enclosure/STL` if the original repo is cloned elsewhere.
`src/params.py` holds every parameter; `src/build.py` does the mesh booleans (manifold3d) on the original STLs,
checks each export by re-loading the written STL (watertight, one body), runs assembly interference checks and renders
PNGs with `src/render.py` (software z-buffer, no GPU). The full log is written to `out/build_log.txt`.

## Outputs (bounding boxes in the original assembly frame, mm)

| File | Bbox | Notes |
|---|---|---|
| `out/display_panel_paperdiy.stl` | 195.2 × 86.2 × 11.5 | bezel, unsplit (too big for A1 mini: use the split pieces) |
| `out/display_lid_usbc.stl` | 202.0 × 107.6 × 29.6 | lid, unsplit (no seam pads) |
| `out/keyboard_tray.stl` | 202.0 × 108.0 × 15.0 | tray, unsplit |
| `out/paperdiy_strap.stl` | 8.0 × 78.4 × 2.5 | clamps the PaperDIY via its M2 standoff |
| `out/key_pushrod_x2.stl` | 5.5 × 15.9 × 4.0 | print **2** (KEY1/KEY2) |
| `out/power_pushrod.stl` | 41.5 × 5.5 × 4.0 | power button |
| `out/split/lid_A_left.stl` / `lid_B_main.stl` | 29.0 × 93.0 × 22.0 / 173.0 × 107.6 × 29.6 | |
| `out/split/tray_A_left.stl` / `tray_B_main.stl` | 35.0 × 93.0 × 12.9 / 173.0 × 108.0 × 15.0 | |
| `out/split/panel_A_left.stl` / `panel_B_main.stl` | 31.6 × 86.2 × 7.1 / 169.6 × 86.2 × 11.5 | the panel (195.2 mm) does not fit 180 mm in any orientation either |

All printed parts ≤ 173 mm (limit 175). Every STL above was re-loaded after writing: watertight, consistent winding, a single body.

## Layout (lid frame: x = long axis, y − = front/free edge, y + = hinge, screen faces −z)

* **PaperDIY** sits with its glass on the panel back (z = 18), USB end at **−x** (x −59.5 … 55.8), its key edge facing the
  **front wall**. Reason: the key edge must face a wall without the hinge block, so the antenna edge (opposite the keys)
  faces the hinge side and the USB-C faces the left end wall.
* **Window** 105.0 × 59.72 at the back face (M5's own kit window), 1.5 mm/side bevel to the front like the original.
  It sits 1.39 mm from the non-USB end and 8.90 mm from the USB end of the glass, which hides the FPC/bond area.
  The window centre is at x = +1.9.
* **Retention:** a 1.6 × 1.0 mm locating lip around the glass (0.3 mm clearance). A printed **strap** is screwed to two
  posts on the panel (M2 heat-set inserts) and clamps the board through its **single M2 standoff** (the drawing shows only one
  M2, centred, 77.9 mm from the non-USB end). The strap is 2.5 mm thick under the countersunk head, so **ISO 7046 M2×4 gives
  1.5 mm of thread in the standoff, and M2×5 gives 2.5 mm. Both are under the 3 mm limit. Do not use M2×6 or longer.**
  `build.py` asserts this. Elsewhere the strap's underside clears the ESP32-S3 module (5.45 mm tall) by 0.45 mm.
* **Buttons:** two D-section push-rods pass through the restored front wall at the real KEY positions
  (x −17.1 / −29.1, z 20.95). A 41.5 mm rod passes through the left end wall to the power button (y +23.4, z 21.27).
  Each rod has a collar inside the wall that stops it falling out, an open-top U-cradle on the panel, and a 0.3 mm rest gap
  to the actuator. These are **side-actuated** switches on the board edges, so rods (not front holes) are the only way to reach them.
* **Battery** (integrated, see below) sits at **+x**, at the far end from the antenna. The antenna is on the hinge-side long
  edge, 70–88 mm from the non-USB end, so it is about 70 mm from the cell.
* **USB-C panel mount** goes on the **left end wall** (the wall nearest the PaperDIY port). It is offset to y = +2
  (the port is at y = −24) so the extension cable can loop. A 15 × 1 mm relief in the panel back clears the plug overmold.

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
   (flat wall at y = −46.5 / x = +101, same top chamfer). Added: panel-mount USB-C opening + 2 screw holes and the power-rod
   bore (left wall), 2 key-rod bores (front wall), battery ceiling relief. Camera window, label recess, vents, hinge and
   corner bosses unchanged.
3. **Keyboard (tray):** geometry unchanged by default (`KB_CUTS_ENABLED = False`). The original right-wall (y 26.3–36.7) and
   rear-wall (x 72.9–89.1) openings are kept; they are probably the CACOE port/switch cut-outs of the original design (not
   verified). If the real keyboard's port/switch are elsewhere, set `KB_CUTS_ENABLED = True`, measure `KB_*` and rebuild.
4. New parts: strap, 3 push-rods. Split versions of lid / tray / panel.

## Splitting for the A1 mini
* **Lid** at x = −72: clear of the hinge knuckle (|x| ≤ 44) and of the camera window (x ≥ −68.9 at the top).
  There are two internal **seam pads** on the front and back walls (12 × 12 × 7.7 mm, z 19.3–27, clear of the panel, rods and
  USB plug). Each pad has a **Ø3.3 dowel hole** through it (3 × 10 mm dowel) and an **M2 heat-set insert** (Ø3.2, 5 deep) in
  piece A. Piece B has a Ø2.4 clearance hole with a Ø4.2 × 2.5 counterbore facing the open cavity: use **M2×6 socket head**.
  Glue the ceiling butt joint as well.
* **Tray** at x = −72: clear of the hinge ears (|x| 46–61) and the rear opening. The tray interior is fully occupied by the
  keyboard and the floor is only 3 mm, so dowels or inserts would break the ≥ 1.6 mm wall rule or the outer silhouette.
  The joint is **3 glued dovetail keys** through the floor (neck 6, head 10, depth 6, 0.2 mm/side clearance) plus butt-glued
  walls. Use CA or epoxy.
* **Panel** at x = −72: same dovetail keys. Each piece keeps two of the original corner screws.

## Print-ready 3MF (A1 mini)
`3mf/plate1_lid.3mf` (lid A+B, needs supports at the hinge knuckle), `plate2_tray.3mf` (tray A+B),
`plate3_panel_strap.3mf` (panel A+B, strap) and `plate4_knobs_rods.3mf` (2x original hinge knob standing on its cap end,
3 push-rods): every part already in print orientation and laid out on a 180 x 180 mm plate, grouped by colour.
Regenerate with `python3 src/export_3mf.py` after `src/build.py`.

## Print orientation (suggested)
* Lid pieces: **top face down** (the original's ceiling is flat at z = 30). The hinge knuckle needs supports, as in the original.
* Panel pieces: **screen face down** (z = 15 on the bed). Lip, posts, cradles and bay frame grow upward with no supports.
* Tray pieces: **floor down** (as modelled). Hinge-ear bores as in the original.
* Strap: **top face down** (countersinks open toward the bed, pad up). Push-rods: **flat (D) side down**.

## Hardware
2× M2×4 (max M2×5) ISO 7046 countersunk for the strap standoff screw; 2× M2×6 ISO 7046 for the strap ends; 2 + 2 M2 inserts
Ø3.2 L3 (strap posts + lid seam); 2× M2×6 socket head (lid seam); 2× dowel Ø3 × 10; original 4× M2 inserts + 4× M2 panel
screws, 2× M3×40, M3 inserts, O-rings, knobs as in the original BOM; panel-mount USB-C extension; 1S LiPo with protection PCB
and a JST **SH1.0-2P** lead (PaperDIY battery input per M5 docs).

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
* Original enclosure geometry: sections and ray probes of the phone-enclosure STLs.

## Assumptions / placeholders — **measure on the real part**
* **TODO keyboard:** first fit the CACOE in the unmodified tray and check that the original openings reach its charge port
  and switch. Only if they don't: `KB_CUTS_ENABLED = True` and measure `KB_PORT_*` / `KB_SW_*` (placeholders: 10 × 5 opening
  at y = +10, z = 6.5 and an 8 mm notch down to z = 5.5 at y = −15, left short wall).
* **USB-C panel mount:** 13 × 7 opening, 2 × Ø3.4 holes, **28 mm spacing**, at y = +2, z = 22.5. The spacing is a guess for
  common screw-ear extensions: measure yours (M2 ears → set `USB_PM_SCREW_D = 2.4`). The plug overmold at the PaperDIY end
  must be ≤ ~6.4 mm thick (or use a right-angle plug).
* **Power button identity** is inferred: it is the lone switch on the USB short edge. The two long-edge switches are KEY1/KEY2,
  but which is which is not determined.
* Actuator heights (depth 2.95 / 3.27) come from the drawing's side view (± ~0.3). Rod gaps of 0.3 mm absorb this.
  The power actuator protrusion (0.7) comes from an extension line and the kit cap position.
* The ED047TC1 active area is **not** taken from a datasheet. The window is M5's kit window, which shows some inactive border.
* Battery default 50 × 34 × 10 is the requested default, not a specific cell. Check charge current vs. cell size (not verified).
* Fits: 0.3 mm lip, 0.4 mm on rod bores, 0.2 mm/side on dovetails, Ø3.3 for 3 mm dowels. Tune for your printer.

## Verification actually performed
STL re-load watertight / single body / bbox ≤ 175 mm for every part. Zero-volume interference (closed assembly) between
lid, panel, strap, rods, a PaperDIY envelope built from the drawing (glass, PCB + USB-end ears, module, standoff, USB-C,
actuators) and the battery box. Ray scan of the restored lid walls against the original. Renders inspected visually.
**Not done:** no slicer run, no physical test fit, no FEA of the strap or seams.

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
| `USB_PM_W` | `13.0` | ASSUMED | [A] opening width  (along y) |
| `USB_PM_H` | `7.0` | ASSUMED | [A] opening height (along z) |
| `USB_PM_R` | `1.0` | design choice |  |
| `USB_PM_Y` | `2.0` | ASSUMED | [A] offset from the PaperDIY port (y=-24) so the cable can loop |
| `USB_PM_Z` | `22.5` | design choice |  |
| `USB_PM_SCREW_SPACING` | `28.0` | ASSUMED | [A] typical screw-ear panel-mount USB-C extension -> MEASURE |
| `USB_PM_SCREW_D` | `3.4` | ASSUMED | [A] M3 clearance (use 2.4 for M2 ears) |
| `KB_PORT_WALL` | `"left"` | ASSUMED | [A] TODO measure: left short wall (x=-101) |
| `KB_PORT_Y` | `10.0` | ASSUMED | [A] TODO |
| `KB_PORT_Z` | `6.5` | ASSUMED | [A] TODO centre height (floor top is z=3) |
| `KB_PORT_W` | `10.0` | ASSUMED | [A] TODO |
| `KB_PORT_H` | `5.0` | ASSUMED | [A] TODO |
| `KB_SW_Y` | `-15.0` | ASSUMED | [A] TODO switch notch centre (same wall) |
| `KB_SW_W` | `8.0` | ASSUMED | [A] TODO |
| `KB_SW_BOTTOM_Z` | `5.5` | ASSUMED | [A] TODO notch bottom (wall top there is ~z 9.6) |
| `SPLIT_X_LID` | `-72.0` | design choice | clear of hinge knuckle (/x/<=44) and camera window (x>=-68.9) |
| `SPLIT_X_TRAY` | `-72.0` | design choice | clear of tray hinge ears (/x/ 46..61) and rear opening (x 72.9..89.1) |
| `SPLIT_X_PANEL` | `-72.0` | design choice | clear of the window bevel (x>=-52.1) |
| `MAX_PIECE` | `175.0` | design choice |  |
| `DOVETAIL` | `dict(neck=6.0, head=10.0, depth=6.0, clr=0.2)` | design choice | glued dovetail keys (0.4 total clearance) |
| `DOVETAIL_Y` | `(-25.0, 0.0, 25.0)` | design choice |  |
| `DOWEL_D` | `3.3` | design choice | for 3 mm dowel pins (3x10) |
| `LID_PAD` | `dict(half_len=6.0, depth=12.0, z0=19.3, dowel_off=3.0, dowel_z=22.6, ins_off=8.0, ins_z=24.6,` | design choice |  |
