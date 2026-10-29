"""Run after reopening the generated layout .blend in background Blender."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
scene=bpy.context.scene;doc=json.loads(bpy.data.texts['approved-layout.json'].as_string());cw=doc['canvas']['width'];ch=doc['canvas']['height'];scale=200
bpy.context.view_layer.update();maximum=0
for part in doc['parts']:
    ob=bpy.data.objects[part['id']]
    assert ob.hide_render == (not part['visible'])
    for vertex,(u,v) in zip(ob.data.vertices,[(0,1),(1,1),(1,0),(0,0)]):
        p=ob.matrix_world@vertex.co
        pixel=Vector((p.x*scale+cw/2,ch-p.y*scale))
        dx=(u-part['pivotX'])*part['width'];dy=(v-part['pivotY'])*part['height'];a=math.radians(part['rotation'])
        expected=Vector((part['x']+math.cos(a)*dx-math.sin(a)*dy,part['y']+math.sin(a)*dx+math.cos(a)*dy))
        maximum=max(maximum,(pixel-expected).length)
    tex=next(n for n in ob.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE')
    assert tex.image.packed_file
    assert Path(bpy.path.abspath(tex.image.filepath)).stem==part["asset"], (part["id"],tex.image.filepath,part["asset"])
assert maximum<.001,maximum
assert scene.render.resolution_x==cw and scene.render.resolution_y==ch
report={'parts':len(doc['parts']),'max_corner_error_pixels':maximum,'all_textures_packed':True,'visibility_preserved':True}
Path(bpy.data.filepath).with_suffix('.verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
