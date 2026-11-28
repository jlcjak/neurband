"""make_plate.py - write the Bambu Studio projects in to_print/, every part in print orientation on one plate:

  neurband_c2_x2d.3mf        tub, lid with its blue inlay as a second filament, bars x2, pods x6
  neurband_c2_x2d_plain.3mf  the same with a plain lid (no logo, no text), everything on filament 1 and the
                             first extruder, plus the bonding tray

The printer, filament and process settings are the ones of the rev C1 plate (ref/x2d_pla_matte_0.12_project_settings.config:
X2D, 0.4 mm nozzle, PLA Matte black + blue, 0.12 mm layers, Arachne walls). Per-object settings: tub and bars
solid (straight lines, not the project's gyroid) with extra walls; pods without a brim, because a brim fills
the 0.5 mm gaps under the wings.

Run: /usr/bin/freecadcmd -c "__file__='mech/rev_c2/make_plate.py'; exec(open(__file__).read())"
"""
import os, sys, json, uuid, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.neurband_lib = True
import FreeCAD, Part
import c2 as R
import params as P
sys.neurband_tray_lib = True
import case as C
import pod as PD
import tray as T

V = FreeCAD.Vector
OUT = os.path.join(R.HERE, 'to_print', 'neurband_c2_x2d.3mf')
OUT_PLAIN = os.path.join(R.HERE, 'to_print', 'neurband_c2_x2d_plain.3mf')
SETTINGS = os.path.join(R.HERE, 'ref', 'x2d_pla_matte_0.12_project_settings.config')
DEFLECTION = 0.01
NS = uuid.UUID('6d1c3a55-4a0e-4a59-9f43-0d2b3c6f6c20')


def uid(tag):
    return str(uuid.uuid5(NS, tag))


def mesh_xml(shape, oid, centre):
    pts, tris = shape.tessellate(DEFLECTION)
    out = [f'  <object id="{oid}" p:UUID="{uid("mesh%d" % oid)}" type="model">', '   <mesh>', '    <vertices>']
    out += [f'     <vertex x="{p.x - centre.x:.6f}" y="{p.y - centre.y:.6f}" z="{p.z - centre.z:.6f}"/>' for p in pts]
    out += ['    </vertices>', '    <triangles>']
    out += [f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tris]
    out += ['    </triangles>', '   </mesh>', '  </object>']
    return '\n'.join(out), len(tris)


def bed(sh):
    return R.on_bed(sh)


def plate_objects(plain=False):
    """(name, settings, [(part name, shape on the bed, extruder)], (x, y) on the plate)"""
    tub = bed(C.build_tub())
    lid = C.build_lid()
    lid_r = lid.copy()
    lid_r.rotate(V(0, 0, 0), V(1, 0, 0), 180)
    bb = lid_r.BoundBox
    shift = V(-bb.Center.x, -bb.Center.y, -bb.ZMin)
    lid_parts = []
    if plain:
        lid_parts.append(('Lid - plain', R.moved(lid_r, shift.x, shift.y, shift.z), 1))
    else:
        for (name, part, color), label, ext in zip(C.lid_materials(lid), ('Lid - black shell', 'Backplane logo and lettering - blue'), (1, 2)):
            c = part.copy()
            c.rotate(V(0, 0, 0), V(1, 0, 0), 180)
            c.translate(shift)
            lid_parts.append((label, c, ext))
    bar = bed(C.build_lug_bar())
    pod, _ = PD.build_pod()
    pod.rotate(V(0, 0, 0), V(0, 1, 0), -90)
    pod = bed(pod)
    solid = {'sparse_infill_density': '100%', 'sparse_infill_pattern': 'zig-zag', 'wall_loops': '5'}
    objs = [('tub', solid, [('tub.step', tub, 1)], (96.0, 158.0)),
            ('lid', {}, lid_parts, (146.0, 158.0)),
            ('lug_bar_1', {**solid, 'wall_loops': '4'}, [('lug_bar_x2.step', bar, 1)], (180.0, 158.0)),
            ('lug_bar_2', {**solid, 'wall_loops': '4'}, [('lug_bar_x2.step', bar, 1)], (192.0, 158.0))]
    for k in range(6):
        objs.append((f'pod_{k + 1}', {'brim_type': 'no_brim', 'wall_loops': '3'}, [('pod_x6.step', pod, 1)], (72.0 + 17.0 * k, 106.0)))
    if plain:
        objs.append(('bond_tray', {'brim_type': 'no_brim'}, [('bond_tray.step', bed(T.build_tray()), 1)], (128.0, 55.0)))
    return objs


HEAD = ('<?xml version="1.0" encoding="UTF-8"?>\n<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
        'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">\n')


def write(out=OUT, plain=False):
    objs = plate_objects(plain)
    files, res, items, cfg, inst, rels = {}, [], [], [], [], []
    nid = 0
    for n, (name, settings, parts, (px, py)) in enumerate(objs, 1):
        whole = Part.makeCompound([s for _, s, _ in parts])
        o0 = V(whole.BoundBox.Center.x, whole.BoundBox.Center.y, 0.0)
        meshes, comps, pcfg, faces = [], [], [], 0
        for k, (pname, sh, ext) in enumerate(parts):
            nid += 1
            c = sh.BoundBox.Center
            xml, nt = mesh_xml(sh, nid, c)
            faces += nt
            meshes.append(xml)
            d = c.sub(o0)
            comps.append(f'    <component p:path="/3D/Objects/object_{n}.model" objectid="{nid}" p:UUID="{uid("comp%d" % nid)}" '
                         f'transform="1 0 0 0 1 0 0 0 1 {d.x:.6f} {d.y:.6f} {d.z:.6f}"/>')
            pcfg.append(f'    <part id="{nid}" subtype="normal_part" uuid="{uid("part%d" % nid)}">\n'
                        f'      <metadata key="name" value="{pname}"/>\n'
                        f'      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>\n'
                        f'      <metadata key="extruder" value="{ext}"/>\n'
                        f'      <mesh_stat face_count="{nt}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>\n'
                        f'    </part>')
        nid += 1
        oid = nid
        files[f'3D/Objects/object_{n}.model'] = HEAD + ' <metadata name="BambuStudio:3mfVersion">1</metadata>\n <resources>\n' + '\n'.join(meshes) + '\n </resources>\n</model>\n'
        rels.append(f' <Relationship Target="/3D/Objects/object_{n}.model" Id="rel-{n}" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>')
        res.append(f'  <object id="{oid}" p:UUID="{uid("obj%d" % oid)}" type="model">\n   <components>\n' + '\n'.join(comps) + '\n   </components>\n  </object>')
        items.append(f'  <item objectid="{oid}" p:UUID="{uid("item%d" % oid)}" transform="1 0 0 0 1 0 0 0 1 {px:.4f} {py:.4f} 0" printable="1"/>')
        meta = ''.join(f'    <metadata key="{k}" value="{v}"/>\n' for k, v in [('name', name), ('extruder', '1')] + sorted(settings.items()))
        cfg.append(f'  <object id="{oid}">\n{meta}    <metadata face_count="{faces}"/>\n' + '\n'.join(pcfg) + '\n  </object>')
        inst.append(f'    <model_instance>\n      <metadata key="object_id" value="{oid}"/>\n      <metadata key="instance_id" value="0"/>\n'
                    f'      <metadata key="identify_id" value="{200 + 11 * n}"/>\n    </model_instance>')
    model = (HEAD + ' <metadata name="Application">BambuStudio-02.09.01.70</metadata>\n <metadata name="BambuStudio:3mfVersion">1</metadata>\n'
             f' <metadata name="Title">neurband rev C2{" (one filament)" if plain else ""}</metadata>\n <resources>\n' + '\n'.join(res) + '\n </resources>\n'
             f' <build p:UUID="{uid("build")}">\n' + '\n'.join(items) + '\n </build>\n</model>\n')
    mode, maps = ('Manual', '1 1') if plain else ('Auto For Flush', '1 2')
    plate = ('  <plate>\n    <metadata key="plater_id" value="1"/>\n    <metadata key="plater_name" value="neurband rev C2"/>\n'
             f'    <metadata key="locked" value="false"/>\n    <metadata key="filament_map_mode" value="{mode}"/>\n'
             f'    <metadata key="filament_maps" value="{maps}"/>\n    <metadata key="filament_volume_maps" value="0 0"/>\n' + '\n'.join(inst) + '\n  </plate>\n')
    files['3D/3dmodel.model'] = model
    files['3D/_rels/3dmodel.model.rels'] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                                            + '\n'.join(rels) + '\n</Relationships>\n')
    files['Metadata/model_settings.config'] = '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n' + '\n'.join(cfg) + '\n' + plate + '  <assemble>\n  </assemble>\n</config>\n'
    settings = json.load(open(SETTINGS))
    if plain:                                          # everything on the first extruder
        settings['filament_map_mode'] = 'Manual'
        settings['filament_map'] = ['1', '1']
        settings['enable_prime_tower'] = '0'
    files['Metadata/project_settings.config'] = json.dumps(settings, indent=4)
    files['_rels/.rels'] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
                            ' <Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>\n')
    files['[Content_Types].xml'] = ('<?xml version="1.0" encoding="UTF-8"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                                    ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                                    ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
                                    ' <Default Extension="png" ContentType="image/png"/>\n <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>\n')
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in ['[Content_Types].xml', '_rels/.rels', '3D/3dmodel.model', '3D/_rels/3dmodel.model.rels'] + sorted(k for k in files if k.startswith('3D/Objects/')) + \
                ['Metadata/model_settings.config', 'Metadata/project_settings.config']:
            z.writestr(name, files[name])
    return objs


log = R.Log('plate')
for out, plain in ((OUT, False), (OUT_PLAIN, True)):
    objs = write(out, plain)
    log(f"  wrote {os.path.relpath(out, R.ROOT)}: " + ', '.join(n for n, *_ in objs))
R.finish(log)
