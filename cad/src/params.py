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
WHOLE_DIR = os.path.join(OUT_DIR, "whole")   # lid, tray and panel in one piece each, for bigger printers
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

# ---------------------------------------------------------------- PaperDIY Complete Kit, left in its own case (K159-B)
# PD_MOUNT = "kit":  the PaperDIY stays in the Complete Kit's 3D-printed case, lies in a thin lid and is held by a
#                    bezel panel (KIT_LID below). It runs on the kit's own 140 mAh LiPo (a power bank on the USB-C when
#                    that is not enough). Lid and tray both reprint; a snap tab keeps it shut.
# PD_MOUNT = "bare": the earlier design: bare Assembly Kit on a printed display panel, strap, push-rods, 2000 mAh cell.
PD_MOUNT = os.environ.get("PD_MOUNT", "kit")
# [M:K159-B STL] = m5stack/M5_Hardware Products/K159-B_PaperDIY_Complete_Kit/Structures/PaperDlY_Complete_Kit.stl
# (sha256 9258e3e2...3e58). Kit frame: front (window) up, USB end +x, KEY edge -y. Below, distances "toward the USB
# end" are from the case centre; in the lid the kit lies front down with its USB end at -x and the KEY edge at -y.
KIT_L, KIT_W, KIT_T = 120.0, 67.0, 6.3    # [M:K159-B STL] case outline without the button caps (docs: 120.0 x 68.2 x 6.3)
KIT_R = 3.0                   # [M:K159-B STL] plan corner radius
KIT_WIN = (105.0, 59.7)       # [M:K159-B STL] window at the front face
KIT_WIN_OFF = 4.0             # [M:K159-B STL] window centre from the case centre, away from the USB end
KIT_KEY_CAPS = ((9.6, 20.4), (21.6, 32.4))   # [M:K159-B STL] KEY1/2 caps on the -y long edge, toward the USB end
KIT_CAP_OUT = 1.2             # [M:K159-B STL] caps stand 1.2 proud of the case edge
KIT_CAP_Z = (2.1, 4.95)       # [M:K159-B STL] cap depth behind the front face
KIT_PWR_CAP_Y = (17.9, 28.8)  # [M:K159-B STL] power cap on the USB end (+y = away from the KEY edge)
KIT_PWR_CAP_OUT = 1.27        # [M:K159-B STL]
KIT_USB_Y = -24.0             # [M:K159-B STL] USB-C centre on the USB end (8.94 wide)
KIT_USB_Z = (2.44, 5.6)       # [M:K159-B STL] port depth behind the front face
KIT_SCREW_D = 20.0            # [M:K159-B STL] back-plate hole (4.2) over the M2 standoff, toward the USB end, centred
KIT_MASS_G = 43.1             # [M: docs.m5stack.com K159-B] with case, acrylic and 140 mAh cell
KIT_CX = -KIT_WIN_OFF         # [D] case centre x in the lid: puts the window centre at x = 0
KIT_FIT = 0.2                 # around the kit (pocket / panel rim), per side
KIT_GAP = 0.2                 # behind the kit (its back plate is flat; the ESP32 module sits in a window in it)
# Manufacturing (kit design): PLA on a Bambu Lab A1 mini (0.4 nozzle, 0.2 layers): 2 mm shells (1.2 mm ones printed
# too flexible), bosses and ribs; clearances for a tuned FDM printer; no supports. No chamfers; corner radii half of
# the original (r 6 -> 3).
WALL = 2.0                    # lid and tray walls, lid ceiling, tray floor (5 lines of a 0.4 nozzle, 9 of a 0.2 nozzle)
CORNER_R = 3.0 if PD_MOUNT == "kit" else 6.0   # plan corners of lid and tray (the original's r 6, halved)
RIB_T = 1.2                   # ribs, guides and guard rings (3 lines)
# keyboard tray (kit): a new thin shell with the original's outline and parting. Ribs on the inside of the walls stand
# out to the keyboard's faces (KB_FACE_*: the measured or estimated keyboard + KB_FIT), so it sits without play (behind
# it they stand on the deck's solid back strip). The charge-port opening in the back wall (x 72.9..89.1) starts 3.0
# above the floor, as in the original.
TRAY_KB_RIBS = dict(front_x=(-80.0, -40.0, 40.0, 80.0), back_x=(-80.0, -40.0, 0.0, 40.0, 66.0), end_y=(-25.0, 25.0))
TRAY_PORT = dict(x=(72.9, 89.1), above_floor=3.0)
# Deck (kit): a t thick face flush with the tray's rim that closes the gaps around the keyboard, so no boss or pad shows.
# Its opening is `clr` larger than the rib faces on every side (room to file the ribs if the keyboard is a little bigger
# than KB_SIZE), corner radius r. Along the front and end walls it rests on a 45 deg fillet (no supports); behind the
# keyboard it is the top of a solid strip from the floor up (the slicer fills it with infill; it takes in the hinge
# bosses and pads), open over the charge-port opening (the plug, and a switch there, stay reachable from above).
TRAY_DECK = dict(t=1.2, clr=0.5, r=3.0) if PD_MOUNT == "kit" else None
# Kit: TPU feet (print them with a 0.4 nozzle; TPU does not go through a 0.2 one).
# Feet: four non-slip pads pressed into `pocket` deep pockets in the tray's bottom at the corners, `t` thick, so they
# stand t - pocket proud: only 0.4 mm, so the open lid still comes down on the table (at ~169 deg) and stops there; with
# 1.2 mm feet it would swing on past 180 deg with nothing to stop it. Concentric with the corner radius and `inset` from
# the outer edges: the rear ones reach to 0.5 mm from the back edge, so the point the device tips about moves in only
# that much. The pocket's mouth is chamfered (elephant foot); the pad is `fit` larger than the pocket per side (TPU
# squeezes in) and chamfered on the table side.
TPU_FEET = dict(w=16.0, d=8.0, inset=0.5, pocket=0.8, t=1.2, fit=0.05, chamfer=0.3) if PD_MOUNT == "kit" else None
FOOT_H = TPU_FEET["t"] - TPU_FEET["pocket"] if TPU_FEET else 0.0      # the table is this far below the tray's bottom
# No dampers under the lid's front edge: the torque hinges spring back a little when the lid is let go (see LATCH), so
# the closed lid is always pressed up against the snap and cannot rattle; TPU springs there only added to that push.
TRAY_FLOOR = WALL if PD_MOUNT == "kit" else 3.0   # top of the tray floor (the original tray: 3.0)
# Keyboard: the CACOE stands above the tray rim (the original lid's panel face was at z = 15). The lid's inner face
# (and the kit's front face) is KB_CLR above the keyboard's highest point. MEASURE the keyboard's thickness over the
# keycaps: KB_TOP_Z = TRAY_FLOOR + KB_THICK.
KB_THICK = 11.5               # [A] from the original lid (panel face 15.0 over a 3.0 floor) -> MEASURE
KB_TOP_Z = TRAY_FLOOR + KB_THICK
KB_CLR = 0.5
# The CACOE sits loose in the original tray (reported: about 2 mm both ways). KB_SIZE = (width x, depth y) of the keyboard
# body. Kit: the tray's ribs stand KB_FIT off it (KB_FACE_*). Bare design: None = no pads; otherwise pads on the inner
# walls stand (inner size - keyboard) / 2 - KB_PAD["clr"] off the wall.
KB_SIZE = (194.0, 85.0) if PD_MOUNT == "kit" else None   # [A] kit: the original room (196 x 87) less the reported play -> MEASURE
KB_FIT = 0.15                 # kit: keyboard to the ribs, per side
KB_FACE_X, KB_FACE_Y = ((KB_SIZE[0] / 2 + KB_FIT, KB_SIZE[1] / 2 + KB_FIT) if PD_MOUNT == "kit" and KB_SIZE
                        else (LID_INNER_X, LID_INNER_Y))   # the ribs' faces toward the keyboard
KB_PAD = dict(clr=0.15, w=6.0, z0=3.0, top_below_rim=1.0, lead=1.5, front_x=(-60.0, -22.0, 22.0, 60.0),
              back_x=(-60.0, -22.0, 22.0, 60.0), end_y=(-20.0, 8.0))
LID_UNDER = (10.4417, 0.05376)  # [M] lid underside (parting) plane z = a + b * y, fitted to the original (resid < 0.001)
LID_SKIN = 1.2                # least skin over a pocket or channel
LID_CHAMFER = 0.0 if PD_MOUNT == "kit" else 0.8   # top edge and seam chamfer (kit: none)
COVER_TOP_RIM = 0.8           # lid hinge covers: rim above the leaf mortise (sides keep COVER_RIM)
KIT_NOTCH = dict(out=7.0, depth=5.6, end=1.5, r=2.0)   # finger notches at the caps: 7 mm out from the pocket, 5.6 deep
USB_CH = dict(w=13.0, h=7.6)  # channel for a straight USB-C plug (overmold ~12 x 6.5) from the left end to the port
KIT_SCREW_SEAT = 1.6          # lid skin under the countersunk M2x4 head -> 2.2 mm into the kit (M5Stack: < 3 mm)
DOVETAIL_Y_KIT = (-37.0, 5.0, 36.0)   # lid keys clear of the USB channel (y -30.5..-17.5) and the power notch
# KIT_LID = "shell": hollow lid (thin walls and ceiling) and a printed bezel panel that holds the kit from the screen side,
#                   screwed to bosses in the lid (default). "solid": the solid deck lid with the kit in a pocket.
KIT_LID = "shell"
SHELL_WALL = WALL
SHELL_CEIL = WALL
USB_CEIL = 0.8                # ceiling left over the USB-C plug path (a relief from inside, 4 layers)
PANEL_T = 1.6                 # bezel panel (countersunk M2x8 heads: 1.2 deep)
PANEL_CLR = 0.2               # panel to the lid's walls and hinge pads
PANEL_WIN_CLR = 0.3           # window = the kit's window + 0.3 per side (the kit can shift by KIT_FIT), square edges
PANEL_RIM = dict(h=2.0, w=1.2)   # locating rim on the panel's back around the kit (below the caps at 2.1 mm)
PANEL_SLOT = dict(out=8.0, end=3.0, r=0.75)  # finger slots through the panel in front of the caps (KEY) and the power cap
# guard rings on the panel's back around the finger slots, up to the kit's back: whatever falls in a slot stays in that
# pocket (ring + the kit's edge) instead of getting into the lid
PANEL_GUARD = dict(t=RIB_T, clr=0.5)
PANEL_SCREWS = ((-91.0, -37.5), (91.0, -37.5), (-91.0, 46.0), (91.0, 46.0), (-62.0, -39.5), (-62.0, 40.0))  # clear of the housings
# Ribs on the panel's screw bosses (Ø6 columns hanging 6.4-8.6 mm from the lid's ceiling): toward a wall closer than
# `tie` a rib runs into the wall (full height), elsewhere a gusset `len` long (its edge slopes from the boss's foot to
# the ceiling); none into the kit's rim or the lid's splice-plate pockets. All stop `gap` above the panel's back.
PANEL_BOSS_R = 3.0
PANEL_BOSS_RIBS = dict(t=RIB_T, len=3.0, tie=5.5, gap=0.5, min_len=1.5)
# The panel is open over the USB-C plug path (left edge to the kit's port, like the button slots): a plug can be
# guided into the port by hand, and a panel-mount female's inner plug goes in and out without taking the panel off.
PANEL_USB_SLOT = dict(frame=2.2, half=6.6, r=0.75)  # None = closed; frame left at the panel's left edge
# snap detents: bumps on the panel's front and back edges click into shallow grooves in the lid's walls (which flex
# outward as the panel goes in), so the panel stays in without its screws. x: between the wall ribs, clear of the latch,
# the KEY slot and the hinge pads. Profile across the edge: a ridge with its peak h out from the panel edge at
# mid-thickness, so it goes in and comes out (prised at the finger slots) alike; h - PANEL_CLR = 0.25 mm past the wall.
# "h" sets the grooves (lid), "bump" the bumps (panel): tight -> lower "bump" and reprint the panel only.
PANEL_SNAP = dict(x_front=(-60.0, 26.0), x_back=(-23.0, 26.0), len=8.0, h=0.45, bump=0.45, clr=0.05)
# panel keys (split version for the A1 mini only): smaller than DOVETAIL so every web around them is >= 2.5 mm (build.py
# checks >= 2 mm): the front key between the front edge (y -45.1) and the USB slot (-30.6), the back one between the
# power slot (top 31.8) and the back edge (y 51.6). The panel is split at SPLIT_X_PANEL, clear of the power slot.
PANEL_DOVETAIL = dict(neck=4.5, head=7.0, depth=5.0, clr=0.2)
PANEL_DOVETAIL_Y = (-37.3, 0.0, 42.0)
KIT_RIBS_X = (-50.0, 0.0, 40.0)              # ribs from the ceiling onto the kit's back (clear of the ESP32 window)
USB_GUIDE_X = (-99.6, None)                  # USB-C guide ribs from the end wall (inner face -99.4) to the kit, either side of the plug path
SPLIT_BLOCK = None if PD_MOUNT == "kit" else dict(dx=7.0, dy=7.0, h=3.4)   # bare: thicker ceiling around the lid's keys
# Kit: how the A1 mini split pieces meet: "straight" (a plain cut at SPLIT_X_*: a straight seam, aligned and held by the
# splice plates below) or "dovetail" (three glued dovetail keys per seam besides, DOVETAIL / PANEL_DOVETAIL).
SPLIT_JOINT = "straight" if PD_MOUNT == "kit" else "dovetail"
# A1 mini split pieces (the one-piece parts have none): thin splice plates glued from the hidden side across each seam
# (on top of the tray floor under the keyboard, inside the lid's ceiling, on the panel's back), each t thick in a pocket
# half the wall deep in both halves, so they sit flush; the pockets face up in print (no bridging).
# x0/x1: the plate's ends relative to the split; y: the plates (clear of the USB-C channel, the slots, the rim and the
# screw bosses; the tray's: inside the keyboard's room, so it goes in from above past the deck).
SPLICE = dict(clr=0.3,                # per side (0.15 printed too tight: the plates print flat, with elephant foot)
              tray=dict(t=WALL / 2, x0=-10.0, x1=10.0, y=((-42.4, 42.4),)),
              lid=dict(t=WALL / 2, x0=-10.0, x1=6.0, y=((-44.0, -33.0), (-15.0, 50.5))),
              panel=dict(t=PANEL_T / 2, x0=-10.0, x1=8.4, y=((-42.35, -32.25), (-15.75, 13.25), (33.45, 48.85))))   # >= 1.5 mm from edges / slots
# USB-C at the left end: "direct" = a straight cable into the kit's port through the end-wall opening (default);
# lid A also comes for a screw-ear panel-mount female (USB_PM_*), at y = USB_PM_Y, so the end can be swapped later.
USB_PM_Y_KIT = 20.0            # clear of the lid's split blocks (y 5, 36) and the power slot
# Snap (no magnets, no slits): a lip in the middle of the lid's front wall runs below the parting into a recess in the
# tray's front face; a bump on its inside drops into a groove in the recess.
# What it has to do: the HG-MF08 are free-stop friction hinges in POM. Let go, they turn back a little (the twist stored
# in them and in their seats), so a lid pushed down onto the tray comes up again: 1 deg at the axis is 1.7 mm at the
# front edge, and it cannot be pushed past closed to make up for it. The snap holds the lid down against that: the two
# hinges' torque (0.157 N*m +-25 %) less the lid's weight leaves 0.5..1.3 N at the front edge.
# The lip is not cut free: a tab freed by two slits breaks from the slit ends (the strain gathers there, on a layer
# line: the lid prints ceiling down). Instead the front wall is thinned from inside over a zone round the lip (`flex`:
# x0..x1, to t, stopping `top` below the ceiling, 45 deg chamfers back to the full wall), and that zone bends outward
# as a plate (free air, so the keyboard's position does not matter). build.py solves it as a Kirchhoff plate
# (src/latch_plate.py): keep the strain across the layers under ~0.5 %.
# Engagement = bump - clr = 0.30 mm: a printer's +-0.15 mm leaves 0.15..0.45, i.e. still ~2.5 N of hold at the low end
# (the 0.20 mm of the earlier versions could shrink to nothing) and under 0.4 % strain at the high end.
# Lip 12 wide in the middle (nothing of the panel reaches the wall there), 2.2 below the parting, 1.0 thick; bump 0.45
# high, 1.4 below the parting (0.6 mm of tray above its groove). The zone stops short of the panel's snap groove at
# x 22..30.
LATCH = dict(x=0.0, w=12.0, t=1.0, below=2.2, bump=0.45, bump_at=1.4, clr=0.15,
             flex=dict(x0=-20.0, x1=20.0, t=1.1, top=2.0),
             close_deg=45.0, open_deg=35.0, tray_wall_min=1.2)

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
# The display's far (right) end would otherwise be free to lift: the two arms carry on as ribbed rails to near the end of
# the glass, with feet at x = 18 and 49 that stand on the display's back (same height as the legs' feet). The rails stay
# at y +-20..29.5, so the battery lead runs between them.
STRAP_RAILS = dict(x_end=52.3, width=6.0, rib_t=1.6, rib_bottom=20.4, feet_x=(18.0, 49.0), foot_len=4.0)
STRAP_SCREW_LEN = 4.0         # ISO 7046 M2x4 countersunk -> 1.5 mm into the standoff (M2x5 -> 2.5 mm, still < 3)
CSK_D = 4.2                   # countersink for M2 ISO 7046 (head 3.8)
M2_CLEAR = 2.4

# push-rods (separate prints)
ROD_D = 3.0
ROD_HOLE = 3.4                # +0.4 slide clearance
ROD_GAP = 0.3                 # rest gap rod tip -> actuator
ROD_COLLAR_D = 5.5
ROD_COLLAR_T = 0.8            # inside the wall (was 1.2): with the snap tip pushed fully in, the KEY collars stay 0.2 mm
                              # short of the panel's cradles, so the panel still drops in
ROD_PROUD = 1.0               # rod end proud of the outer wall (plain rods, ROD_SNAP = None)
# Snap tip: the outer end is split by a vertical slot and each half carries a barb, so a rod pushed in from inside the
# lid clicks past the outer face and stays there before the panel goes in (the plain rods fell out while assembling).
# The wall is held between the collar (inside) and the barbs (outside) with `play` of travel for the button press; the
# barbs are circles of the bore's radius set `catch` off the axis, so with the halves squeezed together they just fill
# the bore. Prongs `slot_len` long keep the bending strain about 1.2 % (bore printed 0.1 mm small). The split part is
# flattened on top as well (`top` above the axis, like the flat underside) so no layer of a prong is a sliver.
ROD_SNAP = dict(play=0.9, catch=0.35, slot=1.0, slot_len=7.5, land=0.5, lead=0.6, tip_r=1.2, top=0.9)
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
KB_PLUG = dict(x=81.0, z=TRAY_FLOOR + 6.4, w=12.0, h=6.5, y0=44.0, len=28.0)   # centre 6.4 above the tray floor

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
SPLIT_X_PANEL = -74.2 if PD_MOUNT == "kit" else -72.0   # kit: 2.2 mm clear of the power slot (x >= -72.0), panel B 173.0 mm; bare: of the window bevel
MAX_PIECE = 175.0
WHOLE_BED = 220.0   # the unsplit plates are laid out on a 220 x 220 mm bed (fits 220 mm beds and bigger)
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
# face mounting + covers: printed plates (case colour) over each leaf so only the barrels show, open or closed.
# Kit design: 1.0 mm covers sit flush in a pocket in the back face, and the leaves sit COVER_T deeper, so the hinge axis
# stays 0.15 mm outside the back face (clear to 180 deg; a thicker flush cover would put the axis inside the face and the
# lid's and tray's back edges would collide when opening). Under each screw hole a cone on the cover fills the leaf's
# countersink, so the hinge's own M2x8 screws, countersunk in the cover, hold cover and leaf together: no glue.
# Bare design: 1.0 mm covers glued on top of the back face (1.0 mm proud).
HINGE_COVER = True
COVER_FLUSH = PD_MOUNT == "kit"
COVER_SCREWED = COVER_FLUSH   # held by the hinge screws (bare design: glued)
COVER_T = 1.0                 # plate thickness (kit: flush in the back face; bare: proud of it)
COVER_RIM = 1.5               # overlap onto the case around the leaf mortise
COVER_R0 = 3.6                # covers start this far from the axis (barrel + clearance for rotation)
COVER_POCKET_CLR = 0.25       # kit: pocket around each cover, per side (0.15 printed too tight)
COVER_EDGE_CHAMFER = 0.3      # kit: 45 deg chamfer round the cover's outer face, which prints on the bed (elephant foot)
COVER_R = 0.5 if COVER_FLUSH else 1.0   # plan corner radius of the covers (kit: halved)
# kit: 90 deg countersink for the M2 flat head (dk 3.5-3.8) at the outer face, clearance hole, and the cone under it that
# fills the leaf's countersink (catalogue 4.2, assumed 90 deg) with 0.1 mm radial clearance
COVER_CSK = dict(top_d=4.0, hole_d=2.3, cone_d=4.1, cone_h=0.7)
HINGE_SINK = COVER_T if COVER_FLUSH else 0.0   # the leaves sit this much deeper than in a plain mortise
# kit: crush ribs on the side edges of each flush cover, so it stays in its pocket when pressed in, before (or without)
# the screws. Each rib stands out COVER_POCKET_CLR at the inner face (just touching the pocket wall: the lead-in) and h
# where the outer chamfer starts, so the interference grows from 0 to h - COVER_POCKET_CLR (0.1 mm) per side as the cover
# goes in. The ribs are on the covers, so the fit is tuned by reprinting them (tight: lower h; loose: raise it).
COVER_RIBS = dict(per_side=2, h=COVER_POCKET_CLR + 0.1, r=0.9) if COVER_FLUSH else None
# optional: a lip on each side edge of a cover, reaching d further into a deeper strip of the pocket (outside the leaf's
# mortise), e.g. dict(w=1.0, d=1.1, clr=0.2) for a 2.1 mm deep cover (SLA / MJF minimums). None: a plain 1 mm plate.
COVER_LIP = None
HINGE_MODEL = "Sugatsune HG-MF08-BL x2 (free-stop, 0.0784 N*m +-25% each, POM)"
HINGE_TORQUE = 0.0784         # [M] N*m each (0.8 kgf*cm), free stop in both directions
HINGE_TORQUE_TOL = 0.25       # [M] +-25 %
# [M] Sugatsune spec table (global.sugatsune.com, 21651_t): HG-MF08 L 20, W 25, t 2, W2 16, H2 10, holes 2.4 / csk 4.2
HINGE_LEN = 20.0              # [M] L: length along the axis
HINGE_WIDTH = 25.0            # [M] W: both leaves + barrel, open flat
HINGE_LEAF_T = 2.0            # [M] t
HINGE_BARREL_D = 5.5          # [M: Sugatsune 3D viewer, end view ~5.4-5.5] not in the spec table (channel takes ~6.2)
# [M: Sugatsune 3D viewer] the back of the hinge is flat; the barrel stands on the front only, its axis ~3.2 mm above
# the flat back (barrel top ~5.9). Seated flat-side-down in a 2.05 mm mortise, the axis is ~1.15 mm OUTSIDE the back face;
# with the leaves sunk under flush covers (kit), ~0.15 mm.
HINGE_AXIS_ABOVE_BACK = 3.2
HINGE_HOLE_PITCH_X = 10.0     # [M] H2: hole pitch along the axis
HINGE_HOLE_OFF = 8.0          # [M] W2 16 / 2: hole centres from the axis
HINGE_SCREW = ("M2x8 countersunk tapping screws x8, heads in the covers, through the leaf holes (2.4 / csk 4.2)"
               if COVER_SCREWED else "M2x8 countersunk tapping screws x8 (leaf holes 2.4 / csk 4.2)")
HINGE_X = 52.0                # hinge centres at x = +-52: clear of the lid/tray split (x=-72) and the tray rear opening (x>=72.9)
HINGE_CLR = 0.25              # mortise clearance per side
HINGE_PILOT_HOLES = True      # print pilot holes at the catalogue hole positions
HINGE_PILOT_D = 1.8           # for M2 tapping screws in PLA
BACK_OLD_Y = 46.5             # [M] original outer back face of lid and tray
BACK_EXTRA = 11.5 if HINGE_MOUNT == "parting" else 6.5   # back walls 3.0 -> 14.5 mm (parting) / 9.5 mm (face: M2x8 + 1.5 mm skin)
Y_BACK = BACK_OLD_Y + BACK_EXTRA   # new outer back face (the leaves sit flush in it)
HINGE_AXIS_Y = (Y_BACK - HINGE_SINK - HINGE_LEAF_T - 0.05 + HINGE_AXIS_ABOVE_BACK if HINGE_MOUNT == "face"   # real axis,
                else Y_BACK)                                    # ~Y_BACK + 0.15 (kit, leaves sunk) / + 1.15 (bare)
Z_PART = 12.85                # [M] parting line at the back (lid underside 12.78..12.89, tray top 12.83..12.89)
# Only the hinges need the 9.5 mm back wall (2 mm leaf mortise + 6 mm of M2x8 + 1.5 mm). "housings" keeps the original
# 3 mm back wall everywhere else and puts a 9.5 mm deep housing behind each hinge, blended into the wall by a tapered
# rib on each side; "solid" is the v0.3 design (whole back wall 9.5 mm). The slicer fills thick walls with 15 % infill,
# so hollowing them would not save material: the saving comes from the smaller outer shape.
# The kit design uses "solid" for lid and tray: with the back face only at the housings, the lid's back edge between the
# hinges sat 7.65 mm in front of the hinge axis and swung up ~11 mm off the tray when opened, leaving a slot between screen
# and keyboard. With the whole back at the hinge plane the edge is 1.15 mm from the axis and the seam stays ~2 mm.
BACK_STYLE = ("solid" if PD_MOUNT == "kit" else "housings") if HINGE_MOUNT == "face" else "solid"
HOUSING_HALF = 13.5           # housing half-length along x: cover 23.5 mm + 1.75 mm of glue land each side
# kit (thin shells): instead of a solid 9.5 mm housing, each hinge sits on a pad (the cover pocket + WALL around it, the
# mortise + WALL deep) with a screw boss behind each pilot hole, out to the screw tip + 1.5 mm and down (tray) / up (lid)
# to the floor / ceiling as a rib
HINGE_PAD = dict(boss_wall=1.6, skin=1.5)
# kit: the lid's lower back edge and the tray's upper back edge (along the parting, at the hinge axis) are rounded with
# this radius. With the axis only 0.15 mm outside the back face (flush covers), the square edges would rub as soon as
# the real axis sits a little lower than the catalogue model suggests; the radius gives that room.
HINGE_EDGE_R = 1.5 if PD_MOUNT == "kit" else 0.0
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
# hinge screws: head flush in the back face either way (kit: in the cover; bare: in the leaf countersink), so the tip ends
# at the same place; past the leaf seat that is 5 mm (kit: cover 1 + leaf 2) or 6 mm (bare)
HINGE_SCREW_LEN = TAP_SCREW_LEN
HINGE_SCREW_DEPTH = HINGE_SCREW_LEN - HINGE_SINK - HINGE_LEAF_T
LID_CORNER_HOLES = [(sx * 92.8, sy * 38.78) for sx in (-1, 1) for sy in (-1, 1)]   # [M] panel screw bosses in the lid
LID_FILL_CAMERA = True        # fill the Boox Palma camera window (x -67..-25, y -32..-20.5 + 1.6 mm bevel)
CAMERA_FILL = (-69.5, -22.5, -34.8, -17.8)
LID_SEAM = "dovetail"         # lid halves joined like tray / panel: 3 glued dovetail keys in the 3 mm ceiling
TOP_PLATE = True              # optional blank plate for the lid-top recess (accent colour)
