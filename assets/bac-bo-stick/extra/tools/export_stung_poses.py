"""Additional authored poses as editable SVGs; no new scenes/1 enums."""
from pathlib import Path
import sys,json,io
import resvg_py
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from storyvid.character import Character
E=ROOT/'assets/bac-bo-stick/extra';O=ROOT/'output/stung_treng/characters'
meta=json.loads((E/'stung-character-library.json').read_text())
for info in meta['characters']:
 id=info['id'];c=Character({'preset':id},640);folder=E/'characters'/id
 # The existing rig does not expose a prayer enum. These explicit transforms
 # remain reusable editable source without adding invalid values to scenes.json.
 s=c.svg('idle','sad')
 s=s.replace('translate(166 294) rotate(8)','translate(166 294) rotate(28.5)').replace('translate(234 294) rotate(-8)','translate(234 294) rotate(-28.5)')
 s=s.replace('translate(0 68) rotate(-5)','translate(0 68) rotate(-129.6)').replace('translate(0 68) rotate(5)','translate(0 68) rotate(129.6)')
 poses=folder/'poses';poses.mkdir(exist_ok=True);(poses/'prayer.svg').write_text(s)
 out=O/id/'poses';out.mkdir(exist_ok=True)
 im=Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=s,width=360,height=480))).convert('RGBA');im.save(out/'prayer.png')
 (poses/'placements.json').write_text(json.dumps({'prayer':{'shoulder_L':28.5,'elbow_L':-129.6,'shoulder_R':-28.5,'elbow_R':129.6},'note':'Authored source pose; requires renderer support before selecting prayer in scenes/1.'},indent=2)+'\n')
# The kneeling design has a source-specific pose: split the fixed bent-body arm artwork
# away from the body for editors, while retaining the compatible runtime torso.
id='kneeling_ghost_woman';folder=E/'characters'/id;poses=folder/'poses'
for name,d in [('arm_left','M36 118L24 206 9 276'),('arm_right','M66 138L67 218 50 276')]:
 (poses/(name+'.svg')).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-140 -150 280 430"><path id="{name}" d="{d}" fill="none" stroke="#17191a" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>')
# Cover comparison: approved lead now has a pleading source pose assembled from the rig parts.
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',20)
sheet=Image.new('RGB',(900,520),'#cecdc5');d=ImageDraw.Draw(sheet)
for i,id in enumerate(['stung_narrator','legless_ghost_woman','stung_mrs_chan']):
 im=Image.open(O/id/'poses/prayer.png');sheet.paste(im,(i*300-30,0),im);d.text((i*300+150,495),id.replace('stung_',''),font=font,fill='#20282c',anchor='mm')
sheet.save(O/'prayer-pose.jpg',quality=94)
print('Authored prayer pose source + kneeling arm sources exported.')
