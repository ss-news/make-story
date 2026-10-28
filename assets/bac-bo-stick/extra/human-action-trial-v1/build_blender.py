"""True 2D cutout armature pilot: walking, flashlight, startle and retreat.
Fresh-process invocation only; no changes to Storyvid or the user's open Blender scene.
"""
import bpy,math,json,sys,argparse
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=P.parents[3]/'output/stung_treng/human-action-blender');ap.add_argument('--render',action='store_true');ap.add_argument('--frame',type=int,default=125)
a=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []);O=a.out.resolve();O.mkdir(parents=True,exist_ok=True)
FPS=24;END=288
scene=bpy.data.scenes.new('Narrator | Articulated action pilot');bpy.context.window.scene=scene
scene.render.engine='BLENDER_EEVEE';scene.eevee.taa_render_samples=16
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=END
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
try:scene.view_settings.view_transform='Standard'
except:pass
scene.world=bpy.data.worlds.new('Night');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.015,.02,.03,1)
cols={}
for name in ['01_Background','02_Armature','03_Drawing_Layers','04_IK_Controls','05_Flashlight','06_Camera']:
 col=bpy.data.collections.new(name);scene.collection.children.link(col);cols[name]=col

def mesh(name,corners,col,grid=1):
 bl,br,tr,tl=[Vector(x) for x in corners];vs=[];uvs=[];faces=[]
 for j in range(grid+1):
  v=j/grid
  for i in range(grid+1):
   u=i/grid;vs.append(tuple(bl.lerp(br,u).lerp(tl.lerp(tr,u),v)));uvs.append((u,v))
 for j in range(grid):
  for i in range(grid):
   k=j*(grid+1)+i;faces.append((k,k+1,k+grid+2,k+grid+1))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],faces);me.update();uv=me.uv_layers.new(name='UVMap')
 for poly in me.polygons:
  for li in poly.loop_indices:uv.data[li].uv=uvs[me.loops[li].vertex_index]
 ob=bpy.data.objects.new(name,me);col.objects.link(ob);return ob

def quad(name,center,w,h,col,grid=1):
 x,y,z=center;return mesh(name,[(x-w/2,y-h/2,z),(x+w/2,y-h/2,z),(x+w/2,y+h/2,z),(x-w/2,y+h/2,z)],col,grid)

def material(name,path):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.surface_render_method='BLENDED';n=m.node_tree.nodes;n.clear();l=m.node_tree.links
 tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True);tex.image.alpha_mode='STRAIGHT'
 emit=n.new('ShaderNodeEmission');trans=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');out=n.new('ShaderNodeOutputMaterial')
 value=n.new('ShaderNodeValue');value.name='Visibility';value.outputs[0].default_value=1
 mult=n.new('ShaderNodeMath');mult.operation='MULTIPLY';l.new(tex.outputs['Alpha'],mult.inputs[0]);l.new(value.outputs[0],mult.inputs[1]);l.new(mult.outputs[0],mix.inputs[0]);l.new(tex.outputs['Color'],emit.inputs[0]);l.new(trans.outputs[0],mix.inputs[1]);l.new(emit.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs['Surface'])
 return m,value.outputs[0]

bg=quad('Painted courtyard',(0,1.4,-.7),8.6,4.84,cols['01_Background']);bg.data.materials.append(material('Background',P/'background.png')[0])
camdata=bpy.data.cameras.new('Action camera');cam=bpy.data.objects.new('Action camera',camdata);cols['06_Camera'].objects.link(cam);cam.location=(0,1.35,10);camdata.type='ORTHO';camdata.ortho_scale=6.8;scene.camera=cam

# All edit-bone Z axes face the camera. The character's limbs articulate in XY.
arm=bpy.data.armatures.new('Narrator Deform Skeleton');rig=bpy.data.objects.new('Narrator_ROOT',arm);cols['02_Armature'].objects.link(rig);rig.show_in_front=True
bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
REST={
 'DEF_pelvis':((0,.98,0),(0,1.12,0),None),
 'DEF_spine':((0,.98,0),(0,1.58,0),'DEF_pelvis'),
 'DEF_neck':((0,1.58,0),(0,1.69,0),'DEF_spine'),
 'DEF_head':((0,1.66,0),(0,2.15,0),'DEF_neck')}
for side,x in [('l',-.25),('r',.25)]:
 REST['DEF_upper_arm_'+side]=((x,1.48,0),(x*1.25,1.08,0),'DEF_spine')
 REST['DEF_forearm_'+side]=((x*1.25,1.08,0),(x*1.48,.70,0),'DEF_upper_arm_'+side)
 REST['DEF_hand_'+side]=((x*1.48,.70,0),(x*1.48+.12,.70,0),'DEF_forearm_'+side)
 hx=-.13 if side=='l' else .13
 REST['DEF_thigh_'+side]=((hx,.98,0),(hx+.065,.50,0),'DEF_pelvis')
 REST['DEF_shin_'+side]=((hx+.065,.50,0),(hx,.06,0),'DEF_thigh_'+side)
 REST['DEF_foot_'+side]=((hx,.06,0),(hx+.18,.06,0),'DEF_shin_'+side)
for name,(head,tail,parent) in REST.items():
 b=arm.edit_bones.new(name);b.head=head;b.tail=tail;b.align_roll(Vector((0,0,1)))
 if parent:b.parent=arm.edit_bones[parent];b.use_connect=False
bpy.ops.object.mode_set(mode='OBJECT')
for pb in rig.pose.bones:pb.rotation_mode='XYZ'

def control(name,pos):
 ob=bpy.data.objects.new(name,None);cols['04_IK_Controls'].objects.link(ob);ob.location=pos;ob.empty_display_type='SPHERE';ob.empty_display_size=.045;ob.hide_render=True;return ob
controls={};constraints={}
for side in ['l','r']:
 for kind,lower in [('hand','forearm'),('foot','shin')]:
  target=control('CTRL_'+kind+'_'+side,REST['DEF_'+lower+'_'+side][1]);pole=control('POLE_'+kind+'_'+side,(0,0,0))
  c=rig.pose.bones['DEF_'+lower+'_'+side].constraints.new('IK');c.name='Two-bone IK';c.target=target;c.pole_target=pole;c.chain_count=2;c.use_stretch=False
  controls[(kind,side)]=(target,pole);constraints[(kind,side)]=c
 # Feet stay flat while planted; hand rotation separately aims the flashlight.
 for kind in ['foot','hand']:
  c=rig.pose.bones['DEF_'+kind+'_'+side].constraints.new('COPY_ROTATION');c.target=controls[(kind,side)][0];c.target_space='WORLD';c.owner_space='WORLD'

# Skin images with real vertex groups + Armature modifiers.
def skin(ob,bone,weights=None):
 if weights:
  groups={name:ob.vertex_groups.new(name=name) for name in weights}
  for i,v in enumerate(ob.data.vertices):
   for name,fn in weights.items():groups[name].add([i],fn(v.co),'REPLACE')
 else:
  vg=ob.vertex_groups.new(name=bone);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE')
 ob.parent=rig
 mod=ob.modifiers.new('Armature skin','ARMATURE');mod.object=rig;return ob

def part(id,center,w,h,bone,z=.1,grid=1,weights=None):
 ob=quad(id,(center[0],center[1],z),w,h,cols['03_Drawing_Layers'],grid);ob.data.materials.append(material(id,P/'parts'/f'{id}.png')[0]);skin(ob,bone,weights);return ob

def segment(id,bone,width,z):
 h,t,_=REST[bone];h=Vector(h);t=Vector(t);v=(h-t).normalized();u=Vector((v.y,-v.x,0));center=(h+t)/2;L=(h-t).length+.035
 corners=[center-u*width/2-v*L/2,center+u*width/2-v*L/2,center+u*width/2+v*L/2,center-u*width/2+v*L/2]
 for c in corners:c.z=z
 ob=mesh(id,corners,cols['03_Drawing_Layers'],grid=3);ob.data.materials.append(material(id,P/'parts'/f'{id}.png')[0]);skin(ob,bone);return ob
for side in ['l','r']:
 segment('thigh_'+side,'DEF_thigh_'+side,.18,.06)
 segment('shin_'+side,'DEF_shin_'+side,.155,.07)
 hx=REST['DEF_foot_'+side][0][0]
 ob=part('foot_'+side,(hx+.035,.055),.255,.12,'DEF_foot_'+side,z=.08)
 if side=='r':
  for uv in ob.data.uv_layers.active.data:uv.uv.x=1-uv.uv.x
 segment('upper_arm_'+side,'DEF_upper_arm_'+side,.20,.12)
# Shirt is a small weighted mesh, instead of a rigid picture being rotated whole.
def upper_weight(co):return min(1,max(0,(co.y-1.0)/.38))
part('torso',(0,1.24),.66,.80,'DEF_spine',z=.15,grid=12,weights={'DEF_pelvis':lambda co:1-upper_weight(co),'DEF_spine':upper_weight})
for side in ['l','r']:
 segment('forearm_'+side,'DEF_forearm_'+side,.048,.22)
 h=REST['DEF_hand_'+side][0];part('hand_'+side,(h[0],h[1]),.075,.105,'DEF_hand_'+side,z=.25)
heads={}
for i,id in enumerate(['head_front','head_turn','head_scared','head_blink']):
 ob=quad(id,(0,2.13,.30+i*.002),1.10,1.08,cols['03_Drawing_Layers'],grid=6);m,vis=material(id,P/'parts'/f'{id}.png');ob.data.materials.append(m);skin(ob,'DEF_head');heads[id]=vis
part('flashlight',(.52,.72),.33,.16,'DEF_hand_r',z=.28)

# A composited beam is tied to the hand aim. It does not claim to relight the baked background.
beam=mesh('Flashlight cone',[(0,0,.0),(2.2,-.52,.0),(2.2,.52,.0),(0,0,.0)],cols['05_Flashlight'])
bm=bpy.data.materials.new('Warm flashlight beam');bm.use_nodes=True;bm.surface_render_method='BLENDED';n=bm.node_tree.nodes;n.clear();l=bm.node_tree.links
out=n.new('ShaderNodeOutputMaterial');em=n.new('ShaderNodeEmission');em.inputs[0].default_value=(1,.86,.53,1);tr=n.new('ShaderNodeBsdfTransparent');mix=n.new('ShaderNodeMixShader');gain=n.new('ShaderNodeValue');gain.name='Beam opacity';gain.outputs[0].default_value=.1;l.new(gain.outputs[0],mix.inputs[0]);l.new(tr.outputs[0],mix.inputs[1]);l.new(em.outputs[0],mix.inputs[2]);l.new(mix.outputs[0],out.inputs[0]);beam.data.materials.append(bm)

# Deterministic motion curves, with planted-foot targets during each stance interval.
def ease(u):u=max(0,min(1,u));return u*u*(3-2*u)
def lerp(a,b,u):return a+(b-a)*u
def root_x(t):
 if t<4:return -1.40+.425*t
 if t<7.5:return .30
 if t<10.7:return .30-.40625*(t-7.5)
 return -1.0

def foot_goal(t,side):
 off=0 if side=='l' else .5;spread=-.105 if side=='l' else .105
 if t<3.8 or 7.5<t<10.5:
  retreat=t>7;origin=7.5 if retreat else 0;speed=-.40625 if retreat else .425;period=.86 if retreat else .78
  local=t-origin;phase=local/period+off;k=math.floor(phase);p=phase-k
  base=(.30 if retreat else -1.40)+speed*((k-off)*period)+spread+speed*.16
  if p<.62:return (base,.06,0),0
  u=(p-.62)/.38;return (base+speed*period*ease(u),.06+.13*math.sin(math.pi*u),0),-.22*math.sin(math.pi*u)
 # Settle in place at stops, avoiding continued leg cycling while looking around.
 return (root_x(t)+spread,.06,0),0

def desired_elbow(start,end,a,b,sign):
 v=end-start;r=min(a+b-.001,max(.001,v.length));u=v.normalized();dist=(a*a-b*b+r*r)/(2*r);h=math.sqrt(max(0,a*a-dist*dist));perp=Vector((-u.y,u.x,0));return start+u*dist+perp*h*sign

max_foot_error=0;max_joint_z=0;calibrated={};foot_samples=[]
for frame in range(1,END+1):
 t=(frame-1)/FPS;scene.frame_set(frame)
 walking=t<3.8 or 7.5<t<10.5
 bob=.014*math.cos(t*math.pi*4/.78) if walking else .003*math.sin(t*2)
 startle=math.sin(math.pi*ease((t-6.25)/1.0)) if 6.25<t<7.25 else 0
 body_y=-.005+bob+.10*startle
 for side in ['l','r']:
  fg,_=foot_goal(t,side);hip_x=root_x(t)+(-.13 if side=='l' else .13);dx=fg[0]-hip_x
  body_y=min(body_y,fg[1]+.10*startle+math.sqrt(max(.01,.925**2-dx**2))-.98)
 rig.location=(root_x(t),body_y,0);rig.keyframe_insert(data_path='location',frame=frame)
 lean=math.radians(-4 if t<4 else 0)
 if 6.25<t<7.5:lean=math.radians(9)*startle
 if 7.5<t<10.5:lean=math.radians(5)
 spine=rig.pose.bones['DEF_spine'];spine.rotation_euler[2]=lean;spine.keyframe_insert(data_path='rotation_euler',frame=frame)
 head=rig.pose.bones['DEF_head'];turn=ease((t-4.0)/.8)*(1-ease((t-6.2)/.35));head.rotation_euler=(0,math.radians(12)*turn,math.radians(-6)*turn+math.radians(8)*startle);head.keyframe_insert(data_path='rotation_euler',frame=frame)
 bpy.context.view_layer.update()
 # Both hands are controlled independently from the chest and feet.
 scan=ease((t-4.0)/.9)*(1-ease((t-6.25)/.4))
 rx=root_x(t)+lerp(.40,.76,scan);ry=lerp(.78,1.48,scan)+.07*math.sin(t*2)*scan
 lx=root_x(t)-.40;ly=.78
 if walking:ry+=.045*math.sin(t*math.pi*2/.78);ly-=.05*math.sin(t*math.pi*2/.78)
 if startle:rx-=.18*startle;ry+=.55*startle;lx+=.06*startle;ly+=.65*startle
 goals={('hand','l'):Vector((lx,ly,0)),('hand','r'):Vector((rx,ry,0))}
 for side in ['l','r']:
  fg,angle=foot_goal(t,side);goals[('foot',side)]=Vector((fg[0],fg[1]+.10*startle,fg[2]))
  controls[('foot',side)][0].rotation_euler=(0,0,-math.pi/2+angle)
 for kind in ['hand','foot']:
  for side in ['l','r']:
   target,pole=controls[(kind,side)];target.location=goals[(kind,side)]
   if kind=='hand':target.rotation_euler=(0,0,-math.pi/2+math.radians(8)*scan*math.sin(t*1.5))
   upper='DEF_'+('upper_arm' if kind=='hand' else 'thigh')+'_'+side;lower='DEF_'+('forearm' if kind=='hand' else 'shin')+'_'+side
   bpy.context.view_layer.update();start=rig.matrix_world@rig.pose.bones[upper].head
   a_len=arm.bones[upper].length;b_len=arm.bones[lower].length
   sign=1 if kind=='foot' else -1
   elbow=desired_elbow(start,target.location,a_len,b_len,sign)
   pole.location=elbow+(elbow-(start+target.location)/2)*3
   c=constraints[(kind,side)]
   # Calibrate the pole offset to the authored planar bend, then keep it fixed.
   if (kind,side) not in calibrated:
    best=None
    for angle in [-math.pi,-math.pi/2,0,math.pi/2]:
     c.pole_angle=angle;bpy.context.view_layer.update();actual=rig.matrix_world@rig.pose.bones[lower].head;err=(actual-elbow).length
     if best is None or err<best[0]:best=(err,angle)
    calibrated[(kind,side)]=best[1];c.pole_angle=best[1]
   target.keyframe_insert(data_path='location',frame=frame);target.keyframe_insert(data_path='rotation_euler',frame=frame);pole.keyframe_insert(data_path='location',frame=frame)
 bpy.context.view_layer.update()
 for side in ['l','r']:
  shin=rig.pose.bones['DEF_shin_'+side];actual=rig.matrix_world@shin.tail;err=(actual-goals[('foot',side)]).length;max_foot_error=max(max_foot_error,err)
  max_joint_z=max(max_joint_z,abs((rig.matrix_world@shin.head).z))
 if frame%12==1:foot_samples.append({'frame':frame,'root_x':rig.location.x,'left_goal':list(goals[('foot','l')]),'right_goal':list(goals[('foot','r')])})
 # Whole heads are expression/angle drawings; body action still comes from the skeleton.
 state='head_scared' if t>=6.25 else ('head_turn' if turn>.35 else 'head_front')
 if any(abs(t-blink)<.065 for blink in [1.2,2.7,4.7,10.9]) and state!='head_scared':state='head_blink'
 for id,socket in heads.items():socket.default_value=1 if id==state else 0;socket.keyframe_insert(data_path='default_value',frame=frame)
 wrist=rig.matrix_world@rig.pose.bones['DEF_hand_r'].head
 beam.location=(wrist.x+.12,wrist.y,.005);beam.rotation_euler[2]=math.radians(8)*scan*math.sin(t*1.5);beam.keyframe_insert(data_path='location',frame=frame);beam.keyframe_insert(data_path='rotation_euler',frame=frame)
 gain.outputs[0].default_value=.065*scan;gain.outputs[0].keyframe_insert(data_path='default_value',frame=frame)

for frame,label in [(1,'Walk in'),(97,'Stop / look / aim flashlight'),(151,'Startle'),(181,'Step backward'),(253,'Recover')]:scene.timeline_markers.new(label,frame=frame)
rig['instructions']='Move CTRL_hand_* / CTRL_foot_* and poles to pose; shirt uses a weighted mesh. Object location drives travel.'
scene['demo_scope']='True armature-driven 2D cutout action pilot, not a sequence of whole-body pose swaps.'
scene.frame_set(a.frame);bpy.context.view_layer.update()
for image in bpy.data.images:
 if image.source=='FILE':image.pack()
sys.path.insert(0,str(P))
from prepare_view import setup_view
setup_view()
blend=O/'narrator-action-rig.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
report={'blender':bpy.app.version_string,'scene':scene.name,'armatures':1,'bones':len(arm.bones),'ik_constraints':len(constraints),'weighted_meshes':sum(1 for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)),'max_foot_target_error':max_foot_error,'max_knee_out_of_plane':max_joint_z,'pole_offsets':{str(k):v for k,v in calibrated.items()},'foot_samples':foot_samples,'packed_images':sum(1 for x in bpy.data.images if x.packed_file),'frames':END,'fps':FPS,'blend':str(blend)}
(O/'rig-verification.json').write_text(json.dumps(report,indent=2)+'\n')
if a.render:
 folder=O/'frames';folder.mkdir(exist_ok=True);scene.render.filepath=str(folder/'frame-');bpy.ops.render.render(animation=True)
else:scene.render.filepath=str(O/f'frame-{a.frame:04}.png');bpy.ops.render.render(write_still=True)
print('RIG_REPORT',json.dumps({k:v for k,v in report.items() if k!='foot_samples'}))
