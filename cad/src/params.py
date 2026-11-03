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

# battery bay (integrated in panel; lid gets a ceiling relief)
BATT_L = 50.0                 # [A] cell length (along y)   default 50x34x10 "~2000 mAh"
BATT_W = 34.0                 # [A] cell width  (along x)
BATT_T = 10.0                 # [A] cell thickness
BATT_CLR = 0.5                # side clearance and minimum top clearance
BATT_WALL = 1.6
BATT_CX = 76.9                # bay centre x (between PaperDIY end and right wall)
BATT_CY = -4.5                # shifted -y so the ceiling relief stays clear of the 1.5 mm-thin label recess
MIN_WALL = 1.6

# panel-mount USB-C on the left end wall (nearest the PaperDIY USB-C)
USB_PM_W = 13.0               # [A] opening width  (along y)
USB_PM_H = 7.0                # [A] opening height (along z)
USB_PM_R = 1.0
USB_PM_Y = 2.0                # [A] offset from the PaperDIY port (y=-24) so the cable can loop
USB_PM_Z = 22.5
USB_PM_SCREW_SPACING = 28.0   # [A] typical screw-ear panel-mount USB-C extension -> MEASURE
USB_PM_SCREW_D = 3.4          # [A] M3 clearance (use 2.4 for M2 ears)

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
