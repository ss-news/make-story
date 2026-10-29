"""Build an editable Blender layout reference from an approved web document.
Run in a fresh background Blender process; does not retarget the existing action rig.
"""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path
import bpy

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('layout_contract',HERE/'serve.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
ap=argparse.ArgumentParser();ap.add_argument('--layout',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--render',action='store_true');ap.add_argument('--force',action='store_true')
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
if a.out.exists() and not a.force:raise SystemExit('Output already exists; choose another --out or pass --force.')
if a.layout.stat().st_size>contract.MAX_BODY:raise ValueError('Layout exceeds 100 KB.')
doc=contract.validate_document(json.loads(a.layout.read_text()));cw=doc['canvas']['width'];ch=doc['canvas']['height'];scale=200
scene=bpy.data.scenes.new('Approved 2D layout');bpy.context.window.scene=scene
scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=16
scene.render.resolution_x=int(cw);scene.render.resolution_y=int(ch);scene.render.resolution_percentage=100
scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='Standard';scene.world=bpy.data.worlds.new('Layout world')
col=bpy.data.collections.new('01_Editable PNG layers');scene.collection.children.link(col)

def corner(p,u,v):
    dx=(u-p['pivotX'])*p['width'];dy=(v-p['pivotY'])*p['height'];r=math.radians(p['rotation'])
    x=p['x']+math.cos(r)*dx-math.sin(r)*dy;y=p['y']+math.sin(r)*dx+math.cos(r)*dy
    return ((x-cw/2)/scale,(ch-y)/scale,0)

for index,p in enumerate(sorted(doc['parts'],key=lambda p:p['z'])):
    # Mesh local origin is the editable pivot; clockwise screen degrees become Blender -Z.
    verts=[((u-p['pivotX'])*p['width']/scale,-(v-p['pivotY'])*p['height']/scale,0) for u,v in [(0,1),(1,1),(1,0),(0,0)]]
    mesh=bpy.data.meshes.new(p['id']);mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap')
    for loop,coord in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):loop.uv=coord
    ob=bpy.data.objects.new(p['id'],mesh);col.objects.link(ob)
    ob.location=((p['x']-cw/2)/scale,(ch-p['y'])/scale,p['z']*.001+index*.000001);ob.rotation_euler[2]=-math.radians(p['rotation']);ob.hide_render=not p['visible'];ob.hide_set(not p['visible']);ob['layout_part']=json.dumps(p,ensure_ascii=False)
    mat=bpy.data.materials.new(p['id']);mat.use_nodes=True;mat.surface_render_method='BLENDED';nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
    tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(contract.ASSETS[p['asset']]),check_existing=True);tex.image.pack()
    emission=nodes.new('ShaderNodeEmission');trans=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');out=nodes.new('ShaderNodeOutputMaterial')
    links.new(tex.outputs['Color'],emission.inputs[0]);links.new(tex.outputs['Alpha'],mix.inputs[0]);links.new(trans.outputs[0],mix.inputs[1]);links.new(emission.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface']);mesh.materials.append(mat)
camdata=bpy.data.cameras.new('Layout camera');cam=bpy.data.objects.new('Layout camera',camdata);scene.collection.objects.link(cam);cam.location=(0,ch/(2*scale),10);camdata.type='ORTHO';camdata.ortho_scale=max(cw,ch)/scale;scene.camera=cam
# Blender orthographic scale is the longer frame dimension for AUTO sensor fit.
scene['layout_format']=doc['format'];scene['layout_source']=str(a.layout.resolve());scene['layout_units_per_pixel']=1/scale
text=bpy.data.texts.new('approved-layout.json');text.write(json.dumps(doc,ensure_ascii=False,indent=2))
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.overlay.show_overlays=False;area.spaces.active.shading.type='MATERIAL'
a.out.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(a.out.resolve()))
if a.render:
    scene.render.filepath=str(a.out.with_suffix('.png').resolve());bpy.ops.render.render(write_still=True)
print(json.dumps({'blend':str(a.out),'parts':len(doc['parts']),'packed_images':sum(bool(i.packed_file) for i in bpy.data.images),'kind':'editable-layout-reference; no skeletal rig'}))
