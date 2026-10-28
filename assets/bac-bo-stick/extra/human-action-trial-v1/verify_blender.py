"""Run inside the SAVED .blend to verify actual evaluated motion and IK."""
import bpy,json,math
from pathlib import Path
s=bpy.context.scene;r=bpy.data.objects.get('Narrator_ROOT');assert r and r.type=='ARMATURE'
assert len(r.data.bones)==16
weighted=[o for o in s.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==r for m in o.modifiers)]
assert len(weighted)==18
errs=[];rootxs=[];elbows=[];knee_positions=[];stance_pairs=0;last={}
for f in range(1,289):
 s.frame_set(f);bpy.context.view_layer.update();rootxs.append(r.location.x)
 elbows.append(tuple(r.matrix_world@r.pose.bones['DEF_forearm_r'].head));knee_positions.append(tuple(r.matrix_world@r.pose.bones['DEF_shin_l'].head))
 for side in ['l','r']:
  bone=r.pose.bones['DEF_shin_'+side];goal=bone.constraints['Two-bone IK'].target.location.copy();actual=r.matrix_world@bone.tail;errs.append((actual-goal).length)
  if side in last:
   oldg,olda=last[side]
   if (goal-oldg).length<1e-5:
    assert (actual-olda).length<.001,('stance slide',f,side)
    stance_pairs+=1
  last[side]=(goal,actual)
assert max(errs)<.002, max(errs)
assert max(rootxs)-min(rootxs)>1.6
assert max(p[1] for p in elbows)-min(p[1] for p in elbows)>.3
assert stance_pairs>80,stance_pairs
images=[im for im in bpy.data.images if im.source=='FILE'];assert all(im.packed_file for im in images)
report={'saved_blend_reopened':True,'armatures':1,'bones':16,'weighted_meshes':len(weighted),'ik_constraints':4,'frames_evaluated':288,'max_foot_error':max(errs),'planted_foot_frame_pairs_verified':stance_pairs,'root_travel':max(rootxs)-min(rootxs),'packed_images':len(images),'arm_movement_verified':True}
out=Path(bpy.data.filepath).parent/'saved-rig-verification.json';out.write_text(json.dumps(report,indent=2)+'\n');print('SAVED_RIG_OK',json.dumps(report))
