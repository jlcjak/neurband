#!/usr/bin/env python3
"""neurband product renders - single entry point.

Re-exports every input on each run (KiCad board -> GLB, electrode flex -> GLB if its layout exists,
mech/rev_c STEP -> GLB through FreeCAD), then renders all shots in Blender/Cycles, one Blender
process per shot, spread over the GPUs (one queue worker per GPU).

  python3 render/make_renders.py                 # final: 2048 px long side, 768 spp + OptiX denoise
  python3 render/make_renders.py --quick         # previews: 40 % size, 64 spp
  python3 render/make_renders.py --shots xray,pcb_top --no-export --save-blend
  python3 render/make_renders.py --video             # also the turntable MP4 + GIF (--video-only for just that)

Outputs: render/out/<shot>.png, logs in render/build/logs/, scenes in render/scenes/ (--save-blend).
"""
import argparse, json, os, queue, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BUILD = os.path.join(HERE, 'build')
LOGS = os.path.join(BUILD, 'logs')
KICAD = os.environ.get('KICAD_ROOT', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4'))
KICAD_CLI = os.path.join(KICAD, 'bin', 'kicad-cli')
FREECAD = '/usr/bin/freecad'
BLENDER = '/usr/bin/blender'
MAIN_PCB = os.path.join(ROOT, 'boards/neurband_c/neurband_c.kicad_pcb')
FLEX_PCB = os.path.join(ROOT, 'boards/neurband_c_flex/neurband_c_flex.kicad_pcb')
STEPS = ['band_assembly', 'module_assy', 'fit_160', 'pod_with_flex']      # mech/rev_c/<name>.step
# heaviest first so the two GPU queues finish together
SHOTS = ['hero_arm', 'hero_arm_wide', 'hero_crop', 'hero_dark', 'hero_dark_wide', 'arm_volar', 'xray', 'flatlay', 'band_product', 'band_bone',
         'exploded', 'pods_inside', 'flex_detail', 'pcb_top', 'pcb_pair']
GLB_FLAGS = ['--force', '--no-dnp', '--subst-models', '--cut-vias-in-body', '--include-tracks', '--include-pads',
             '--include-zones', '--include-silkscreen', '--include-soldermask']


def run(cmd, log, timeout=600, env=None):
    t = time.time()
    with open(log, 'w') as f:
        p = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, timeout=timeout, env=env)
    print('  %-60s exit %d  %.0f s' % (os.path.basename(log), p.returncode, time.time() - t), flush=True)
    return p.returncode


def export():
    os.makedirs(LOGS, exist_ok=True)
    env = dict(os.environ, KICAD10_3DMODEL_DIR=os.path.join(KICAD, 'share/kicad/3dmodels'))
    print('export: main board ->', os.path.relpath(MAIN_PCB, ROOT), flush=True)
    # DRC status of the board being rendered (recorded, not a gate: layout is work in progress)
    drc = os.path.join(BUILD, 'main_board_drc.json')
    run([KICAD_CLI, 'pcb', 'drc', '--format', 'json', '-o', drc, MAIN_PCB], os.path.join(LOGS, 'drc.log'), env=env)
    try:
        d = json.load(open(drc))
        sev = {}
        for v in d.get('violations', []):
            sev[v['severity']] = sev.get(v['severity'], 0) + 1
        print('  DRC: violations %s, unconnected %d' % (sev, len(d.get('unconnected_items', []))), flush=True)
    except Exception as e:
        print('  DRC report unreadable:', e)
    out = os.path.join(BUILD, 'main_board.glb')
    if run([KICAD_CLI, 'pcb', 'export', 'glb'] + GLB_FLAGS + ['-o', out, MAIN_PCB],
           os.path.join(LOGS, 'main_board_glb.log'), env=env):
        sys.exit('main board GLB export failed, see render/build/logs/main_board_glb.log')
    flex = os.path.join(BUILD, 'flex_board.glb')
    if os.path.exists(flex):
        os.remove(flex)
    if os.path.exists(FLEX_PCB):
        print('export: electrode flex ->', os.path.relpath(FLEX_PCB, ROOT), flush=True)
        if run([KICAD_CLI, 'pcb', 'export', 'glb'] + GLB_FLAGS + ['-o', flex, FLEX_PCB],
               os.path.join(LOGS, 'flex_board_glb.log'), env=env) and os.path.exists(flex):
            os.remove(flex)
    else:
        print('export: no electrode flex layout yet; flex_detail uses the flex modelled in band_assembly.step')
    print('export: mech/rev_c STEP -> GLB (FreeCAD)', flush=True)
    pairs = []
    for n in STEPS:
        src = os.path.join(ROOT, 'mech/rev_c', n + '.step')
        dst = os.path.join(BUILD, n + '.glb')
        if os.path.exists(dst):
            os.remove(dst)
        pairs.append(src + '=' + dst)
    env2 = dict(os.environ, QT_QPA_PLATFORM='offscreen', STEP2GLB=';'.join(pairs))
    run([FREECAD, os.path.join(HERE, 'step2glb.py')], os.path.join(LOGS, 'step2glb.log'), timeout=600, env=env2)
    missing = [n for n in STEPS if not os.path.exists(os.path.join(BUILD, n + '.glb'))]
    if missing:
        sys.exit('STEP -> GLB failed for %s, see render/build/logs/step2glb.log' % missing)


def render(shots, gpus, quick, samples, save_blend):
    os.makedirs(LOGS, exist_ok=True)
    q = queue.Queue()
    for s in shots:
        q.put(s)
    failed = []

    def worker(gpu):
        while True:
            try:
                s = q.get_nowait()
            except queue.Empty:
                return
            cmd = [BLENDER, '-b', '--python', os.path.join(HERE, 'nb_blender.py'), '--', '--shots', s]
            if quick:
                cmd.append('--quick')
            if samples:
                cmd += ['--samples', str(samples)]
            if save_blend:
                cmd.append('--save-blend')
            env = dict(os.environ, CUDA_VISIBLE_DEVICES=str(gpu))
            try:
                rc = run(cmd, os.path.join(LOGS, 'render_%s.log' % s), timeout=3600, env=env)
            except subprocess.TimeoutExpired:
                rc = -1
            if rc:
                failed.append(s)
    ts = [threading.Thread(target=worker, args=(g,)) for g in gpus]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return failed


def video(gpus, quick, samples):
    """turntable: frames split over the GPUs, then H.264 MP4 + small GIF with ffmpeg."""
    import glob
    out = os.path.join(BUILD, 'turntable')
    os.makedirs(out, exist_ok=True)
    for f in glob.glob(os.path.join(out, 'f_*.png')):
        os.remove(f)
    n = 135
    procs = []
    for k, g in enumerate(gpus):
        cmd = [BLENDER, '-b', '--python', os.path.join(HERE, 'nb_blender.py'), '--',
               '--turntable', '%d:%d:%d' % (k, n, len(gpus))]
        if quick:
            cmd.append('--quick')
        if samples:
            cmd += ['--samples', str(samples)]
        log = open(os.path.join(LOGS, 'turntable_gpu%d.log' % g), 'w')
        procs.append(subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                      env=dict(os.environ, CUDA_VISIBLE_DEVICES=str(g))))
    t = time.time()
    for p in procs:
        p.wait(timeout=7200)
    have = len(glob.glob(os.path.join(out, 'f_*.png')))
    print('  turntable frames %d/%d  %.0f s' % (have, n, time.time() - t), flush=True)
    if have != n:
        sys.exit('turntable render incomplete, see render/build/logs/turntable_gpu*.log')
    src = os.path.join(out, 'f_%04d.png')
    mp4 = os.path.join(HERE, 'out', 'turntable.mp4')
    gif = os.path.join(HERE, 'out', 'turntable.gif')
    run(['ffmpeg', '-y', '-framerate', '30', '-i', src, '-c:v', 'libx264', '-preset', 'slow', '-crf', '18',
         '-pix_fmt', 'yuv420p', '-movflags', '+faststart', mp4], os.path.join(LOGS, 'ffmpeg_mp4.log'))
    run(['ffmpeg', '-y', '-framerate', '30', '-i', src, '-vf',
         'fps=15,scale=-2:720:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];'
         '[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle', '-loop', '0', gif],
        os.path.join(LOGS, 'ffmpeg_gif.log'))
    for f in (mp4, gif):
        print('  %s %.1f MB' % (os.path.relpath(f, ROOT), os.path.getsize(f) / 1e6), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--quick', action='store_true', help='small low-sample previews')
    ap.add_argument('--shots', default=','.join(SHOTS), help='comma list, default all: ' + ','.join(SHOTS))
    ap.add_argument('--no-export', action='store_true', help='reuse render/build/*.glb')
    ap.add_argument('--gpus', default='0,1', help='CUDA device indices, one Blender worker per GPU')
    ap.add_argument('--samples', type=int, default=0, help='override samples per pixel')
    ap.add_argument('--save-blend', action='store_true', help='also save render/scenes/<shot>.blend')
    ap.add_argument('--video', action='store_true', help='also render the turntable (render/out/turntable.mp4/.gif)')
    ap.add_argument('--video-only', action='store_true', help='only the turntable (implies --video)')
    a = ap.parse_args()
    t = time.time()
    if not a.no_export:
        export()
    shots = [] if a.video_only else [s for s in a.shots.split(',') if s]
    print('render: %d shots on GPUs %s (%s)' % (len(shots), a.gpus, 'quick' if a.quick else 'final'), flush=True)
    failed = render(shots, [int(g) for g in a.gpus.split(',')], a.quick, a.samples, a.save_blend)
    if a.video or a.video_only:
        print('render: turntable (135 frames, 1080 x 1350)', flush=True)
        video([int(g) for g in a.gpus.split(',')], a.quick, a.samples)
    print('done in %.1f min; outputs in render/out/' % ((time.time() - t) / 60))
    if failed:
        sys.exit('failed shots: %s (logs in render/build/logs/)' % failed)


if __name__ == '__main__':
    main()
