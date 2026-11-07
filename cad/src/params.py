"""All parameters for the PaperDIY PDA clamshell (derivative of unkyulee/phone-enclosure).

Coordinate frame = the original STL frames, unchanged:
  Lid ("Display.stl") / panel ("Display Panel.stl"): x = long axis (-101..101), y = front(-) .. hinge(+),
  z: panel outer (screen) face at z=15, panel back at z=18, lid ceiling underside z=27, lid top z=30.
  Tray ("Keyboard.stl"): its own frame, floor z=0..3.
Tags:  [M:<source>] measured,  [D] derived from measured values,  [A] ASSUMED / placeholder -> measure on the real part.
"""
import os

HOME = os.path.expanduser("~")
CAD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # this cad/ folder
# Original phone-enclosure STLs (read-only). Override with PHONE_ENCLOSURE_STL=/path/to/phone-enclosure/STL
ORIG_DIR = os.environ.get("PHONE_ENCLOSURE_STL", os.path.join(HOME, "phone-enclosure", "STL"))
# The build is pinned to this exact version of the original (tools/fetch_original.sh checks it out). load() refuses
# files with other hashes unless PHONE_ENCLOSURE_ANY_VERSION=1 is set.
ORIG_REPO = "https://github.com/unkyulee/phone-enclosure"
ORIG_COMMIT = "a21bfd68f2ea34cf692f1949acb148828ce725f7"
ORIG_SHA256 = {
    "Display.stl": "2188adead638975e6771400a9e7e2d71514c39e89124e272f8b621aac154d6a9",
    "Display Panel.stl": "4eb2cd96efcbd444e6a30ada45c0da93fa6e0db02f44e29c41e5a021859a13cd",
    "Keyboard.stl": "fb50e86de54be06af042fb841576a606359eda2263e10f1100b8d4b1eafd8daf",
}
OUT_DIR = os.path.join(CAD_DIR, "out")
SPLIT_DIR = os.path.join(OUT_DIR, "split")
RENDER_DIR = os.path.join(CAD_DIR, "renders")

# ---------------------------------------------------------------- original enclosure (measured from the STLs)
PANEL_Z_FRONT = 15.0          # [M:Display Panel.stl] screen-side face
PANEL_Z_BACK = 18.0           # [M:Display Panel.stl] back face, seats against lid corner bosses
LID_CEILING_Z = 27.0          # [M:Display.stl] ceiling underside (ceiling 27..30, 3.0 thick)
LID_CEIL_THK = 3.0            # [M:Display.stl]
LID_INNER_Y = 43.5            # [M:Display.stl] inner wall faces at y=+-43.5, x=+-98
LID_INNER_X = 98.0
LID_LABEL_POCKET = (21.7, 78.0, 21.34, 32.5)  # [M:Display.stl] x0,x1,y0,y1 of top label recess (ceiling only 1.5 thick)
LID_FRONT_SLOT_X = (-51.5, -6.5)   # [M:Display.stl] Palma side-button slot in front wall, z 19..27 + ceiling edge
LID_RIGHT_OPEN_Y = (-6.0, 6.0)     # [M:Display.stl] Palma USB opening in right wall (x=+101), z 19..27
INSERT_M2_D = 3.2             # [M:Display.stl corner bosses d=3.18; readme: M2 insert OD3.2 L3]
INSERT_M2_L = 3.0             # [M:readme]

# ---------------------------------------------------------------- PaperDIY (Assembly Kit) — K159 model-size PDF + K159-B kit STL
PD_L = 115.3                  # [M:K159 PDF] display/board length
PD_W = 62.5                   # [M:K159 PDF] display/board width
PD_T = 5.5                    # [M:K159 PDF] overall thickness (front face -> tallest part)
PD_PCB_TOP_FROM_TOP = 67.9    # [M:K159 PDF] PCB starts 67.9 from the non-USB end
PD_PCB_OVERHANG = 0.85        # [M:K159 PDF] PCB 'ears' 64.2 wide vs display 62.5 (0.85/side) only for v>=108.9 (USB end); depth 1.4..2.4
PD_M2_FROM_TOP = 77.9         # [M:K159 PDF] single M2 standoff, centred across width (30.2 from edge line @61.45 -> 31.25)
PD_M2_STANDOFF_H = 5.4        # [M:K159 PDF side view] standoff top depth from screen face (PCB back at 2.4 -> 3.0 tall)
PD_M2_STANDOFF_OD = 4.0       # [M:K159 PDF] d4 circle (thread M2 d2)
PD_MAX_THREAD = 3.0           # [given] screws must engage < 3 mm into the PaperDIY standoff
PD_KEY_FROM_TOP = (72.9, 84.9)  # [M:K159 PDF] side keys (12.0 apart; 30.14 dim) on long edge, actuator 1.72 wide
PD_KEY_DEPTH = 2.95           # [M:K159 PDF side view] actuator centre depth from screen face (2.67..3.23)
PD_KEY_PROTRUDE = 0.05        # [M:K159 PDF] actuator tip beyond display edge
PD_PWR_FROM_KEYEDGE = 62.5 - 7.85  # [M:K159 PDF 6.84+1.72/2 from far edge] power button on USB short edge  (=54.65)
PD_PWR_DEPTH = 3.27           # [M:K159 PDF side view, 2.84..3.69] (inferred to be the power button: the lone short-edge switch)
PD_PWR_PROTRUDE = 0.7         # [M:K159 PDF ext. line @116.0 vs edge 115.3; kit cap at 0.72]
PD_USB_FROM_KEYEDGE = 62.5 - 55.25  # [M:K159 PDF 50.78..59.72] USB-C centre 7.25 from the key edge
PD_USB_W = 8.94               # [M:K159 PDF]
PD_USB_DEPTH = (1.64, 4.8)    # [M:K159 PDF side view]
PD_USB_PROTRUDE = 1.75        # [M:K159 PDF 117.05 - 115.3]
PD_WIN_W = 105.0              # [M:K159-B kit STL window 105.01 x 59.72 at inner face]
PD_WIN_H = 59.72
PD_WIN_FROM_TOP = 1.39        # [M:K159-B kit STL] window offset from non-USB end
PD_WIN_FROM_USB = 8.90        # [M:K159-B kit STL] window offset from USB end (FPC/bond area hidden)
PD_ANTENNA_FROM_TOP = (70.0, 88.0)  # [M:K159 PDF] WROOM-1 antenna zone, on the long edge opposite the keys

# ---------------------------------------------------------------- layout choices (lid frame)
# PaperDIY: screen faces -z, USB end at -x, key edge toward the front wall (-y), antenna edge toward hinge (+y).
PD_TOP_X = 55.8               # [D] x of the non-USB end; USB end = 55.8-115.3 = -59.5
PD_CY = 0.0                   # [D] centred across the lid
FIT = 0.3                     # [A] display-to-rim clearance per side
RIM_W = 1.6                   # locating lip width (>= MIN_WALL)
RIM_H = 1.0                   # rim z 18..19 stays below PCB (z 19.4) and USB-C (z 19.64)
WIN_CHAMFER = 1.5             # [D: same 1.5/side bevel as original panel window]
PANEL_KEEP_VENTS = False      # original Palma "speaker" slots: filled (left ones sit over the battery pocket)

# M2 retention strap across the PaperDIY back
STRAP_X = -22.6               # strap centre line (standoff at x=-22.1, posts at x=-22.6)
STRAP_W = 8.0
STRAP_THK = 2.0
STRAP_PAD_DROP = 0.5          # pad under the screw reaches the standoff top; elsewhere 0.5 higher (module is 5.45 tall)
STRAP_POST_Y = 36.0
STRAP_POST_SIZE = 6.4
# The Assembly Kit's PCB is loose on the back of the display and the strap holds it at its single standoff only, so it
# could turn about that screw. Two arms off the strap end in legs that stand just past the PCB's inner end (x = -12.1),
# one each side of the centre line, so the PCB cannot turn; their feet stop 0.2 mm above the display's back. They keep
# clear of the ESP32 module (ends at x = -14.1) and leave the middle free for the battery lead.
STRAP_LEGS = dict(gap=0.2, t=2.0, leg_y=(22.0, 29.0), arm_y=(20.0, 29.5), foot_clear=0.2)
STRAP_SCREW_LEN = 4.0         # ISO 7046 M2x4 countersunk -> 1.5 mm into the standoff (M2x5 -> 2.5 mm, still < 3)
CSK_D = 4.2                   # countersink for M2 ISO 7046 (head 3.8)
M2_CLEAR = 2.4

# push-rods (separate prints)
ROD_D = 3.0
ROD_HOLE = 3.4                # +0.4 slide clearance
ROD_GAP = 0.3                 # rest gap rod tip -> actuator
ROD_COLLAR_D = 5.5
ROD_COLLAR_T = 1.2
ROD_PROUD = 1.0               # rod end proud of the outer wall
ROD_FLAT = 0.9                # flat underside this far below the axis: 2.4 mm wide on the bed (was 1.2 -> 1.8 mm,
                              # which the slicer flags as low bed adhesion); the cradles are raised to match

# battery bay (integrated in panel; lid gets a ceiling relief)
BATT_L = 50.0                 # [A] cell length (along y)   default 50x34x10 "~2000 mAh"
BATT_W = 34.0                 # [A] cell width  (along x)
BATT_T = 10.0                 # [A] cell thickness
BATT_CLR = 0.5                # side clearance and minimum top clearance
BATT_WALL = 1.6
BATT_CX = 76.9                # bay centre x (between PaperDIY end and right wall)
BATT_CY = -4.5                # shifted -y so the ceiling relief stays clear of the 1.5 mm-thin label recess
MIN_WALL = 1.6

# panel-mount USB-C on the left end wall (nearest the PaperDIY USB-C). The wall is in lid piece A (x < -72),
# so only that small piece depends on the cable: plate 1 carries the default spacing and 3mf/usb_variants/ holds
# lid A for other common spacings (pick the one that matches your cable; no rebuild needed).
USB_PM_W = 13.0               # [A] opening width  (along y); narrowed for close screw spacings (see USB_PM_WEB)
USB_PM_H = 7.0                # [A] opening height (along z)
USB_PM_R = 1.0
USB_PM_Y = 1.0                # [A] offset from the PaperDIY port (y=-24) so the cable can loop; 30 mm ears clear the power rod
USB_PM_Z = 22.5
USB_PM_SCREW_SPACING = 28.0   # [A] default in plate 1 -> MEASURE your cable (centre to centre of the two ear holes)
USB_PM_SCREW_D = 3.4          # [A] M3 clearance (use 2.4 for M2 ears)
USB_PM_WEB = 1.2              # minimum wall left between the opening and a screw hole
USB_PM_VARIANTS = (0.0, 16.0, 18.0, 20.0, 22.0, 25.0, 28.0, 30.0)   # lid-A variants (0 = opening only, for glue-in)
# rough envelope of a screw-ear female end behind the wall, for the fit check of each variant
USB_PM_EAR = dict(beyond_hole=4.0, h=8.0, t=3.0)      # ears reach 4 mm past each hole centre, 8 tall, 3 thick
USB_PM_BODY = dict(w=13.0, h=7.0, len=25.0)           # housing behind the ears

# keyboard charge port at the back: the original tray opening (x 73..89, open from z ~6.0 up to the lid at 12.8)
# was a 3 mm deep hole in the 3 mm back wall. Thickening the back wall to 9.5 mm made it a 9.5 mm tunnel, so a
# bay is cut from the outside back to the original wall face (y = 46.5): the plug sees the same 3 mm wall as in the
# original design. The bay crosses the parting line, so lid and tray both get their part of it.
# Front clip (accessory; nothing else changes): a U pushed onto the front edge of the closed case keeps the lid shut in a
# bag. It follows the case's front profile at CLIP_X with CLIP_CLR all round; a CLIP_BUMP ridge near each lip tip presses
# on the lid top and tray bottom so the clip stays on. It fits anywhere along the front except over the KEY push-rods.
CLIP_X = 20.0                 # where the profile is taken and where build_log checks it
CLIP_W = 20.0
CLIP_T = 1.6
CLIP_LIP = 12.0               # the lips reach this far back from the front face (the case's 3 mm chamfers included)
CLIP_CLR = 0.1
CLIP_BUMP = 0.2               # interference of each ridge with the case (spring preload)
CLIP_BUMP_R = 0.8
# Magnetic catch (retrofit; nothing printed changes): 4 pairs of 2 x 3 mm magnets set into the front walls where lid and
# tray meet (the walls touch on a ~1 mm land at z = 8.0, y -45.5..-44.5). Holes are drilled with printed corner jigs that
# straddle the front wall and stop against the end face, so lid and tray holes line up. MAGNET_HOLES = True prints the
# holes into lid and tray instead (for a fresh print).
MAGNETS = dict(d=2.0, l=3.0, depth=4.0, y=-44.8, from_end=(17.0, 57.0), land_z=8.05)
MAG_JIG = dict(clr=0.15, guide_d=2.15, h=8.0, finger=3.0, wall=1.6, fence_t=2.0, fence_y=(-38.0, -30.0),
               straight_x=-94.5, corner_z=9.4)
MAGNET_HOLES = False
KB_PORT_BAY = True            # only used with BACK_STYLE = "solid" (the 3 mm wall of "housings" needs no bay)
KB_PORT_BAY_X = (70.5, 91.5)  # 2.5 mm wider than the opening on each side (overmold + fingers)
KB_PORT_BAY_Z = (4.0, 15.5)   # floor 1 mm above the bottom chamfer, 2.65 mm up into the lid wall
KB_PORT_BAY_R = 1.5
# a typical straight USB-C plug overmold, for the fit / lid-opening check (centred on the original opening)
KB_PLUG = dict(x=81.0, z=9.4, w=12.0, h=6.5, y0=44.0, len=28.0)

# keyboard tray: charge port + power-switch notch (positions unknown -> placeholders)
# Off by default: the original tray (designed for the same CACOE keyboard) already has openings in the
# right short wall (y 26.3..36.7) and the rear wall (x 72.9..89.1), which are probably the port and switch.
# Fit the real keyboard first; only if its port/switch are elsewhere, set True and measure the values below.
KB_CUTS_ENABLED = False
KB_PORT_WALL = "left"         # [A] TODO measure: left short wall (x=-101)
KB_PORT_Y = 10.0              # [A] TODO
KB_PORT_Z = 6.5               # [A] TODO centre height (floor top is z=3)
KB_PORT_W = 10.0              # [A] TODO
KB_PORT_H = 5.0               # [A] TODO
KB_SW_Y = -15.0               # [A] TODO switch notch centre (same wall)
KB_SW_W = 8.0                 # [A] TODO
KB_SW_BOTTOM_Z = 5.5          # [A] TODO notch bottom (wall top there is ~z 9.6)

# A1 mini splitting
SPLIT_X_LID = -72.0           # clear of hinge knuckle (|x|<=44) and camera window (x>=-68.9)
SPLIT_X_TRAY = -72.0          # clear of tray hinge ears (|x| 46..61) and rear opening (x 72.9..89.1)
SPLIT_X_PANEL = -72.0         # clear of the window bevel (x>=-52.1)
MAX_PIECE = 175.0
DOVETAIL = dict(neck=6.0, head=10.0, depth=6.0, clr=0.2)   # glued dovetail keys (0.4 total clearance)
DOVETAIL_Y = (-25.0, 0.0, 25.0)
DOWEL_D = 3.3                 # for 3 mm dowel pins (3x10)
LID_PAD = dict(half_len=6.0, depth=12.0, z0=19.3, dowel_off=3.0, dowel_z=22.6, ins_off=8.0, ins_z=24.6,
               ins_depth=5.0, cb_d=4.2, cb_depth=2.5)

# ---------------------------------------------------------------- hinge: 2 torque hinges flush in the back face
# The original knob/pin hinge (knuckle on an axis at y=54, z=7.5, red knobs, M3x40, O-rings) is replaced by two
# off-the-shelf free-stop torque hinges recessed into the back faces of lid and tray. The hinge axis moves to the
# outer back edge on the parting line, the knuckle/ears/trough strip behind the case is removed, and the back walls
# are thickened outward so the hinge screws have material.
# HINGE_MOUNT = "parting": leaves folded flat in the parting plane inside the back walls (hidden when closed; only the
#                         barrels show at the back edge). Needs back walls >= 12.5 mm deep -> back face +11.5 mm.
# HINGE_MOUNT = "face":    leaves flush in the outer back face (visible plates on the back), back face +3.5 mm.
HINGE_MOUNT = "face"
# face mounting + covers: thin printed plates (case colour) glued over each leaf so only the barrels show,
# open or closed. They stand 1.0 mm proud of the back face (a flush cover would push the axis inside the face).
HINGE_COVER = True
COVER_T = 1.0                 # plate thickness, proud of the back face
COVER_RIM = 1.5               # overlap onto the case around the leaf mortise (glue land)
COVER_R0 = 3.6                # covers start this far from the axis (barrel + clearance for rotation)
HINGE_MODEL = "Sugatsune HG-MF08-BL x2 (free-stop, 0.0784 N*m +-25% each, POM)"
# [M] Sugatsune spec table (global.sugatsune.com, 21651_t): HG-MF08 L 20, W 25, t 2, W2 16, H2 10, holes 2.4 / csk 4.2
HINGE_LEN = 20.0              # [M] L: length along the axis
HINGE_WIDTH = 25.0            # [M] W: both leaves + barrel, open flat
HINGE_LEAF_T = 2.0            # [M] t
HINGE_BARREL_D = 5.5          # [M: Sugatsune 3D viewer, end view ~5.4-5.5] not in the spec table (channel takes ~6.2)
# [M: Sugatsune 3D viewer] the back of the hinge is flat; the barrel stands on the front only, its axis ~3.2 mm above
# the flat back (barrel top ~5.9). Seated flat-side-down in the 2.05 mm mortise, the axis is ~1.15 mm OUTSIDE the back face.
HINGE_AXIS_ABOVE_BACK = 3.2
HINGE_HOLE_PITCH_X = 10.0     # [M] H2: hole pitch along the axis
HINGE_HOLE_OFF = 8.0          # [M] W2 16 / 2: hole centres from the axis
HINGE_SCREW = "M2x8 countersunk tapping screws x8 (leaf holes 2.4 / csk 4.2)"
HINGE_X = 52.0                # hinge centres at x = +-52: clear of the lid/tray split (x=-72) and the tray rear opening (x>=72.9)
HINGE_CLR = 0.25              # mortise clearance per side
HINGE_PILOT_HOLES = True      # print pilot holes at the catalogue hole positions
HINGE_PILOT_D = 1.8           # for M2 tapping screws in PLA
BACK_OLD_Y = 46.5             # [M] original outer back face of lid and tray
BACK_EXTRA = 11.5 if HINGE_MOUNT == "parting" else 6.5   # back walls 3.0 -> 14.5 mm (parting) / 9.5 mm (face: M2x8 + 1.5 mm skin)
Y_BACK = BACK_OLD_Y + BACK_EXTRA   # new outer back face (the leaves sit flush in it)
HINGE_AXIS_Y = (Y_BACK - HINGE_LEAF_T - 0.05 + HINGE_AXIS_ABOVE_BACK if HINGE_MOUNT == "face"   # real rotation axis,
                else Y_BACK)                                                                # ~Y_BACK + 1.15
Z_PART = 12.85                # [M] parting line at the back (lid underside 12.78..12.89, tray top 12.83..12.89)
# Only the hinges need the 9.5 mm back wall (2 mm leaf mortise + 6 mm of M2x8 + 1.5 mm). "housings" keeps the original
# 3 mm back wall everywhere else and puts a 9.5 mm deep housing behind each hinge, blended into the wall by a tapered
# rib on each side; "solid" is the v0.3 design (whole back wall 9.5 mm). The slicer fills thick walls with 15 % infill,
# so hollowing them would not save material: the saving comes from the smaller outer shape.
BACK_STYLE = "housings" if HINGE_MOUNT == "face" else "solid"
HOUSING_HALF = 13.5           # housing half-length along x: cover 23.5 mm + 1.75 mm of glue land each side
HOUSING_GUSSET = 5.5          # tapered rib each side of a housing (plan view 5.5 mm long, 6.5 mm deep at the housing)
# triangular ribs (gussets) inside the lid between the long walls and the ceiling, 1.6 mm thick (4 lines);
# x positions stay clear of the strap (x -22.6), the key push-rods (x -17.1, -29.1) and the USB-C cable loop (x < -62)
LID_RIBS = dict(t=1.6, depth=7.0, drop=7.5,
                back_x=(-52.0, -40.0, -6.0, 16.0, 36.0, 52.0, 74.0),
                front_x=(-52.0, -42.0, -4.0, 16.0, 36.0, 56.0, 76.0))
BACK_ZONE_X = 62.0            # |x| <= this: knuckle / ears / trough removed and the back wall rebuilt from its profile
CORNER_C = (95.0, 40.5)       # [M] centre of the outer back-corner arcs (r = 6.0) in plan view
LID_HINGE_BOSS = dict(w=18.0, depth=4.0, z0=18.5, z1=LID_CEILING_Z + 0.05)  # one screw boss per hinge, inside the lid

# ---------------------------------------------------------------- manufacturing / assembly choices
# FASTENING = "tapping": every case screw is an M2x8 countersunk tapping screw into a printed 1.8 mm pilot hole
#                        (no heat-set inserts, no soldering iron). "inserts": the original M2 heat-set inserts.
FASTENING = "tapping"
SCREW_PILOT_D = 1.8           # M2 tapping screw in PLA
TAP_SCREW_LEN = 8.0           # the one tapping-screw length used everywhere (M2x8)
LID_CORNER_HOLES = [(sx * 92.8, sy * 38.78) for sx in (-1, 1) for sy in (-1, 1)]   # [M] panel screw bosses in the lid
LID_FILL_CAMERA = True        # fill the Boox Palma camera window (x -67..-25, y -32..-20.5 + 1.6 mm bevel)
CAMERA_FILL = (-69.5, -22.5, -34.8, -17.8)
LID_SEAM = "dovetail"         # lid halves joined like tray / panel: 3 glued dovetail keys in the 3 mm ceiling
TOP_PLATE = True              # optional blank plate for the lid-top recess (accent colour)
