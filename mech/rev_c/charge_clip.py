"""charge_clip.py - rev C charger: a printed clip that snaps onto the module (band off the wrist)
and presses two P50 pogo pins into the J3 window. No magnets.

Module frame (see module.py), the clip as fitted:
- a block under the module's centre strip (x +/-BLK_HW, between the pod 3/4 pads; y from Y0, proximal
  of the flex spine, to past the proximal end) whose top matches the R42 underside; the two pins stand
  in it at the VCHG (0, 6.2) and GND (0, 3.2) pads, tips POGO_TIP_FREE above the contact face at rest;
- a back that rises outside the proximal end face, with a KEY tab that only fits the 3 mm pry notch
  (so the clip only goes on the proximal end, centred: it cannot go on reversed);
- a hook over the lid's proximal top edge. The pins (2 x POGO_F_WORK) push the module up against it.
Wiring: the cut USB cable's red (5 V) goes to the pin nearer the cable exit (VCHG), black to the other;
the solder joints sit in the open pocket under the block. The pins are glued with a drop of CA.
Run: QT_QPA_PLATFORM=offscreen timeout 300 /usr/bin/freecad mech/rev_c/charge_clip.py
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import rc as R
import cadutil as U
import module as M

V = FreeCAD.Vector

# ---------------- parameters (mm) ----------------
BLK_HW = 4.0                        # block half-width: pod 3/4 pads start at |x| 5.75
Y0 = 1.3                            # block distal end: the flex spine ends at y 0.6
BACK_T = 3.0                        # back plate behind the proximal end face (stiff: the pins must not lift the module)
BACK_GAP = 0.25                     # back plate to the proximal face
BACK_HW = 7.0                       # back plate and hook half-width
HOOK_REACH = 2.4                    # hook over the crown, from the proximal face inward
HOOK_T = 1.4
HOOK_CATCH = 0.4                    # interference over the crown edge (the back flexes to snap on)
KEY = (2.6, 1.0, 0.8)               # key tab (x width, z height, depth into the notch); notch 3.0 x 1.2 x 1.1
PIN_Y = M.CHG_PADS_Y                # VCHG, GND (module y)
CAV = (2.6, 6.0, 2.5)               # wiring pocket under the block (x, y half extents.., z height)


def build():
    y1 = M.Y_MAX + BACK_GAP
    z_bot = M.Z_PCB + R.POGO_TIP_FREE - R.POGO_L - 2.8          # block bottom (pins' tails 0.5 into the pocket)
    blk = R.box(-BLK_HW, BLK_HW, Y0, y1, z_bot, 1.0).common(M.ucyl(M.R_U))   # top = the R42 underside
    # back plate and hook
    z_hook = M.z_top(0) + 0.0
    back = R.box(-BACK_HW, BACK_HW, y1, y1 + BACK_T, z_bot, z_hook + HOOK_T)
    hook = R.box(-BACK_HW, BACK_HW, M.Y_MAX - HOOK_REACH, y1 + 0.01, z_hook, z_hook + HOOK_T)
    s = blk.fuse([back, hook])
    s = s.cut(M.body())                                  # clear the module
    # catch: the hook's inner edge dips HOOK_CATCH below the crown at its tip (rides over the top fillet)
    tip = R.box(-BACK_HW, BACK_HW, M.Y_MAX - HOOK_REACH, M.Y_MAX - HOOK_REACH + 1.1, z_hook - HOOK_CATCH, z_hook + 0.01)
    s = s.fuse(tip.cut(M.body()))
    # key tab into the pry notch
    kw, kh, kd = KEY
    s = s.fuse(R.box(-kw / 2, kw / 2, M.Y_MAX - kd, y1 + 0.01, M.H_BASE + 0.0, M.H_BASE + kh))
    s = s.removeSplitter()
    # pins (through holes, glued) and the wiring pocket with a cable exit at the back
    zc = z_bot + CAV[2]
    for y in PIN_Y:
        s = s.cut(Part.makeCylinder(R.POGO_HOLE / 2, 30, V(0, y, z_bot - 1)))
    s = s.cut(R.box(-CAV[0], CAV[0], Y0 + 1.0, y1 + BACK_T + 1, z_bot - 1, zc))
    return s.removeSplitter(), z_bot


def pins():
    out = []
    for y in PIN_Y:
        zt = M.Z_PCB                                  # tip as fitted (pressed on the pad)
        out.append(Part.makeCylinder(R.POGO_D / 2, R.POGO_L - R.POGO_WORK, V(0, y, zt - (R.POGO_L - R.POGO_WORK))))
    return Part.makeCompound(out)


if not getattr(sys, 'neurband_clip_lib', False):
    log = R.Log('charge_clip')
    clip, z_bot = build()
    clip = U.check(clip, 'charge_clip', log)
    base = Part.read(os.path.join(R.HERE, 'module_base.step'))
    lid = Part.read(os.path.join(R.HERE, 'module_lid.step'))
    I = M.internals()
    fpoly, fgold, ffoam = M.flex_on_module()
    def clash(a, b):
        return round(a.common(b).Volume, 3)
    def dist(a, b):
        return round(a.distToShape(b)[0], 2)
    pp = pins()
    chk = dict(clip_vs_base=clash(clip, base), clip_vs_lid=clash(clip, lid),
               clip_to_pod34_pads=dist(clip, Part.makeCompound(fgold)), clip_to_foam=dist(clip, Part.makeCompound(ffoam)),
               clip_to_flex=dist(clip, Part.makeCompound(fpoly)), pins_vs_base=clash(pp, base), pins_to_pcb=dist(pp, I['pcb']))
    F = 2 * R.POGO_F_WORK
    chk['pin_preload_N'] = round(F, 2)
    # the back as a cantilever from the block to the hook, loaded by the pin force at the hook
    Lb = M.z_top(0) - z_bot
    Ib = 2 * BACK_HW * BACK_T ** 3 / 12
    chk['hook_lift_under_pins_mm'] = round(F * Lb ** 3 / (3 * 1700 * Ib), 3)
    log("  charge clip checks: " + json.dumps(chk))
    log(f"  clip {clip.BoundBox.XLength:.1f} x {clip.BoundBox.YLength:.1f} x {clip.BoundBox.ZLength:.1f} mm; pins at y {PIN_Y} "
        f"(VCHG nearer the cable exit), tips {R.POGO_TIP_FREE:.1f} above the contact face at rest")
    with open(os.path.join(R.HERE, 'logs', 'charge_clip_checks.json'), 'w') as f:
        json.dump(chk, f, indent=1)
    R.save('charge_clip', [('charge_clip', clip, R.C_POD)], log)
    R.save('charge_clip_fit', [('charge_clip', clip, R.C_POD), ('module_base', base, R.C_HOUSING), ('module_lid', lid, R.C_HOUSING),
                               ('pogo_pins', pp, R.C_GOLD), ('main_board', I['pcb'], R.C_PCB)], log)
    R.fab('charge_clip', 'neurband rev C charging clip (2 x P50 pogo pins, no magnets)', clip, 2, 'mjf', 'pa12', 'black', log)
    R.finish(log)
