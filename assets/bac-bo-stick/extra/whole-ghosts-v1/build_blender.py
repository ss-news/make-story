"""Build an editable Blender 2.5D whole-pose ghost showcase. Blender 5.x.
blender --background --factory-startup --python build_blender.py -- --out <folder> [--render]
"""
import bpy,json,math,sys,argparse
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--pack',type=Path,default=P);ap.add_argument('--out',type=Path,default=P.parents[3]/'output/stung_treng/blender');ap.add_argument('--render',action='store_true');ap.add_argument('--frame',type=int)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
P=a.pack.resolve();O=a.out.resolve();O.mkdir(parents=True,exist_ok=True)
manifest=json.loads((P/'manifest.json').read_text())
# This script is executed in a fresh background process. Never touch the user's open scene.
scene=bpy.data.scenes.new('Stung Treng | Whole Ghosts v1');bpy.context.window.scene=scene
scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=16
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100
scene.render.fps=12;scene.frame_start=1;scene.frame_end=288
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.render.film_transparent=False
try:scene.view_settings.view_transform='Standard'
except TypeError:pass
scene.world=bpy.data.worlds.new('Midnight World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.006,.01,.016,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.05
collections={}
for name in ['01_Background','02_Ghosts','03_Smoke','04_Camera']:
 col=bpy.data.collections.new(name);scene.collection.children.link(col);collections[name]=col

def empty(name,col):
 ob=bpy.data.objects.new(name,None);col.objects.link(ob);return ob

def quad(name,w,h,col,grid=1):
 verts=[];uvs=[];faces=[]
 for j in range(grid+1):
  for i in range(grid+1):
   u=i/grid;v=j/grid;verts.append(((u-.5)*w,(v-.5)*h,0));uvs.append((u,v))
 for j in range(grid):
  for i in range(grid):
   k=j*(grid+1)+i;faces.append((k,k+1,k+grid+2,k+grid+1))
 me=bpy.data.meshes.new(name+' Mesh');me.from_pydata(verts,[],faces);me.update();uv=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  for li in poly.loop_indices:uv.data[li].uv=uvs[me.loops[li].vertex_index]
 ob=bpy.data.objects.new(name,me);col.objects.link(ob);return ob

def image_material(name,path):
 mat=bpy.data.materials.new(name);mat.use_nodes=True;mat.surface_render_method='BLENDED'
 n=mat.node_tree.nodes;n.clear();links=mat.node_tree.links
 out=n.new('ShaderNodeOutputMaterial');out.location=(640,0)
 trans=n.new('ShaderNodeBsdfTransparent');trans.location=(220,-120)
 emit=n.new('ShaderNodeEmission');emit.location=(220,100)
 tex=n.new('ShaderNodeTexImage');tex.location=(-500,100);tex.image=bpy.data.images.load(str(path),check_existing=True);tex.image.alpha_mode='STRAIGHT';tex.interpolation='Linear'
 opacity=n.new('ShaderNodeValue');opacity.label='Animated whole-pose opacity';opacity.name='Pose Opacity';opacity.outputs[0].default_value=1;opacity.location=(-500,-140)
 mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.location=(-100,-80);links.new(tex.outputs['Alpha'],mul.inputs[0]);links.new(opacity.outputs[0],mul.inputs[1])
 mix=n.new('ShaderNodeMixShader');mix.location=(440,0);links.new(mul.outputs[0],mix.inputs[0]);links.new(trans.outputs[0],mix.inputs[1]);links.new(emit.outputs[0],mix.inputs[2]);links.new(tex.outputs['Color'],emit.inputs['Color']);links.new(mix.outputs[0],out.inputs['Surface'])
 return mat,opacity.outputs[0]

def fade(socket,keys):
 for frame,value in keys:socket.default_value=value;socket.keyframe_insert(data_path='default_value',frame=frame)

bg=quad('Clean painted Cambodian courtyard',13.2,7.425,collections['01_Background']);bg.location.z=-.5
mat,_=image_material('Approved background',P/'backgrounds/camp_yard_night.png');bg.data.materials.append(mat)
camdata=bpy.data.cameras.new('Camera 16x9');cam=bpy.data.objects.new('Camera 16x9',camdata);collections['04_Camera'].objects.link(cam);cam.location=(0,0,12);camdata.type='ORTHO';camdata.ortho_scale=9.8;scene.camera=cam
# Structured timeline shows all four poses of all four ghosts.
pose_order={
 'legless_ghost_woman':['float_neutral','plead','bow','raise_head'],
 'kneeling_ghost_woman':['kneel','deep_bow','crawl','look_up'],
 'ghost_boy':['stand','hold_hand','turn','lower_head'],
 'fanged_ghost_child':['stand','lean','look_up','reach']}
controllers=[];timeline=[]
for ci,c in enumerate(manifest['characters']):
 col=bpy.data.collections.new(c['id']);collections['02_Ghosts'].children.link(col)
 root=empty(c['label']+' | whole-image controller',col);controllers.append(root)
 root['character_id']=c['id'];root['mode']='Whole RGBA pose; no limb slicing';root['hover_amount']=.06
 start=ci*72+1;end=start+71
 camera_scale,camera_y=[(9.8,0.0),(6.5,-1.0),(9.0,-.3),(7.0,-.6)][ci]
 for fr in [start,end]:
  camdata.ortho_scale=camera_scale;camdata.keyframe_insert(data_path='ortho_scale',frame=fr)
  cam.location.y=camera_y;cam.keyframe_insert(data_path='location',frame=fr)
 # Calm movement only. The kneeling ghost remains near the ground.
 hover=.035 if c['id']=='kneeling_ghost_woman' else .08
 for frame in range(start,end+1,6):
  t=(frame-start)/12;root.location=(math.sin(t*.65)*.05,hover*math.sin(t*1.8),.05)
  root.rotation_euler[2]=math.radians(1.2)*math.sin(t*.8)
  root.keyframe_insert(data_path='location',frame=frame);root.keyframe_insert(data_path='rotation_euler',frame=frame)
 ref=next(p for p in c['poses'] if p['id']==c['default_pose']);opaque_h=ref['bbox'][3]-ref['bbox'][1]
 plane_h=c['blender_height']/(opaque_h/1536);plane_w=plane_h*1024/1536
 baseline=-2.25 if c['id']!='legless_ghost_woman' else -1.60
 y=baseline-((.5-1390/1536)*plane_h)
 order=pose_order[c['id']]
 for pi,pose in enumerate(order):
  entry=next(p for p in c['poses'] if p['id']==pose)
  ob=quad(c['id']+' / '+pose,plane_w,plane_h,col,grid=14);ob.parent=root;ob.location=(0,y,.02*pi)
  ob['pose_id']=pose;ob['asset_file']=entry['file'];ob['anchor_px']=[512,1390]
  mat,alpha=image_material(c['id']+' | '+pose,P/entry['file']);ob.data.materials.append(mat)
  first=start+pi*18;last=first+17
  # Short dissolves, with one whole drawing visible through most of a hold.
  fade(alpha,[(1,0),(max(1,first-2),0),(first+1,.96),(last-1,.96),(min(289,last+2),0),(289,0)])
  # A very slight deformation at outer lower hair edges, with face/body center held still.
  ob.shape_key_add(name='Basis');key=ob.shape_key_add(name='Subtle silhouette drift')
  for idx,v in enumerate(key.data):
   x,yv,z=v.co;mask=max(0,abs(x)/(plane_w/2)-.42)*max(0,1-(yv/plane_h+.5)/.72)
   v.co.x+=math.sin(yv*2.7)*mask*.025
  for fr,val in [(first,0),(first+9,.8),(last,0)]:key.value=val;key.keyframe_insert(data_path='value',frame=fr)
  timeline.append(dict(character=c['id'],pose=pose,start=first,end=last))
# Three gentle procedural smoke puffs; shader alpha stays low and contains no baked artwork.
for i in range(3):
 ob=quad('Low ground mist '+str(i+1),2.1,1.0,collections['03_Smoke']);ob.location=(-.8+i*.8,-2.0,.25+i*.01)
 mat=bpy.data.materials.new(ob.name);mat.use_nodes=True;mat.surface_render_method='BLENDED';n=mat.node_tree.nodes;n.clear();l=mat.node_tree.links
 out=n.new('ShaderNodeOutputMaterial');trans=n.new('ShaderNodeBsdfTransparent');em=n.new('ShaderNodeEmission');em.inputs[0].default_value=(.25,.33,.36,1)
 coord=n.new('ShaderNodeTexCoord');dist=n.new('ShaderNodeVectorMath');dist.operation='DISTANCE';dist.inputs[1].default_value=(.5,.5,0);l.new(coord.outputs['UV'],dist.inputs[0])
 mult=n.new('ShaderNodeMath');mult.operation='MULTIPLY';mult.inputs[1].default_value=-2;l.new(dist.outputs['Value'],mult.inputs[0]);add=n.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=1;add.use_clamp=True;l.new(mult.outputs[0],add.inputs[0]);power=n.new('ShaderNodeMath');power.operation='POWER';power.inputs[1].default_value=2;l.new(add.outputs[0],power.inputs[0])
 gain=n.new('ShaderNodeMath');gain.operation='MULTIPLY';gain.inputs[1].default_value=.10;l.new(power.outputs[0],gain.inputs[0]);mix=n.new('ShaderNodeMixShader');l.new(gain.outputs[0],mix.inputs[0]);l.new(trans.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface']);ob.data.materials.append(mat)
 for fr in range(1,289,24):ob.location.x=-1+i*.8+math.sin(fr/45+i)*.25;ob.location.y=-2+math.cos(fr/40+i)*.08;ob.keyframe_insert(data_path='location',frame=fr)
# Markers make the saved timeline navigable by character and pose.
for item in timeline:scene.timeline_markers.new(item['character']+' / '+item['pose'],frame=item['start'])
scene['asset_standard']='storyvid.whole-character-assets/1';scene['README']='Whole-pose 2.5D showcase; each drawing is preserved intact; no Storyvid core changes.'
scene.frame_set(30)
# Pack every image, retain relative source paths and save a fully editable scene.
for image in bpy.data.images:
 if image.source=='FILE':image.pack()
blend=O/'stung-treng-whole-ghosts.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report={'blender_version':bpy.app.version_string,'scene':scene.name,'file':str(blend),'objects':len(scene.objects),'whole_pose_planes':len(timeline),'packed_images':sum(1 for x in bpy.data.images if x.packed_file),'frames':[1,288],'fps':12,'timeline':timeline,'missing_files':[x.filepath for x in bpy.data.images if x.source=='FILE' and not x.packed_file and not Path(bpy.path.abspath(x.filepath)).exists()]}
(O/'blender-verification.json').write_text(json.dumps(report,indent=2)+'\n')
if a.frame is not None:
 scene.frame_set(a.frame);scene.render.filepath=str(O/f'frame-{a.frame:04}.png');bpy.ops.render.render(write_still=True)
elif a.render:
 frames=O/'frames-final';frames.mkdir(exist_ok=True);scene.render.filepath=str(frames/'frame-');bpy.ops.render.render(animation=True)
print(json.dumps(report))
