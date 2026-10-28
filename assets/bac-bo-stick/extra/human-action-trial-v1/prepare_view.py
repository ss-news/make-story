"""Open the saved action scene in camera/material view; no animation changes."""
import bpy

def setup_view():
 for screen in bpy.data.screens:
  for area in screen.areas:
   if area.type=='VIEW_3D':
    space=area.spaces.active;space.region_3d.view_perspective='CAMERA';space.shading.type='MATERIAL';space.overlay.show_overlays=False

if __name__=='__main__':
 setup_view()
 assert bpy.data.filepath
 bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
 print('Camera view prepared; toggle overlays to inspect/edit the armature.')
