"""Render previews/transparent PNGs and editable assembled SVGs, without changing core."""
import json,io,math,re,sys
from pathlib import Path
import resvg_py
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from storyvid.character import Character
from storyvid.character_catalog import resolve_character
from storyvid import pack
E=ROOT/'assets/bac-bo-stick/extra';O=ROOT/'output/stung_treng/characters';O.mkdir(parents=True,exist_ok=True)
meta=json.loads((E/'stung-character-library.json').read_text());expressions=meta['runtime_expressions']+meta['source_expressions']
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
small=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',14)
colors={c['id']:c for c in json.loads((E/'manifest.json').read_text())['characters']}
access={c['id']:c['default_accessory'] for c in meta['characters']}
def render(s,w=300,h=400):return Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=s,width=w,height=h))).convert('RGBA')
def face_state(c,exp):
 for kind in ['eyes','brows','mouth']:
  c.parts[kind+'_neutral']=c._load_part({'file':kind+'_'+exp+'.svg'})
def body_svg(c,exp):
 face_state(c,exp)
 s=c.svg('idle','neutral')
 # Preserve uniquely named layers in assembled source; limb definitions are reused twice by the engine.
 counts={}
 def unique(m):
  key=m[1];n=counts.get(key,0);counts[key]=n+1
  return f'id="{key}_{n}"'
 return re.sub('id="([^"]+)"',unique,s)
def face_svg(c,exp):
 face_state(c,exp)
 body=''.join(c._part(n) for n in ['hair_back','head','brows_neutral','eyes_neutral','mouth_neutral','hair_front'])
 box='-130 145 260 280' if c.preset=='kneeling_ghost_woman' else '-130 -125 260 260'
 return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}">{body}</svg>'
ids=[c['id'] for c in meta['characters']]+meta['npcs']
checks=[]
for id in ids:
 out=O/id;out.mkdir(exist_ok=True)
 c=Character(resolve_character({},dict(preset=id,accessory=access.get(id,'none'))),640)
 # These SVGs are redrawn editable vector sources, not automatic raster cutouts.
 for exp in expressions:
  s=body_svg(c,exp);(out/f'{exp}.svg').write_text(s)
  im=render(s,360,480);im.save(out/f'{exp}.png')
  assert im.getpixel((0,0))[3]==0
  assert im.getbbox() is not None
 (E/'characters'/id/'assembled.svg').write_text(body_svg(c,'neutral'))
 # One face sheet per character, including NPCs.
 cw,ch,cols=240,265,6
 sheet=Image.new('RGB',(cols*cw,math.ceil(len(expressions)/cols)*ch),'#d6d3c8');d=ImageDraw.Draw(sheet)
 for j,exp in enumerate(expressions):
  im=render(face_svg(c,exp),220,220);x=j%cols*cw;y=j//cols*ch
  sheet.paste(im,(x+10,y+4),im);d.text((x+cw/2,y+240),exp,font=font,fill='#24282a',anchor='mm')
 sheet.save(out/'expressions.jpg',quality=93)
 checks.append({'id':id,'expressions':len(expressions),'transparent_exports':True})
 print('exported',id,flush=True)

def lineup(id_list,file,cols=4):
 cw,ch=300,380;sheet=Image.new('RGB',(cw*cols,ch*math.ceil(len(id_list)/cols)),'#cecdc5');d=ImageDraw.Draw(sheet)
 for i,id in enumerate(id_list):
  x=i%cols*cw;y=i//cols*ch
  exp='sad' if id in ['legless_ghost_woman','kneeling_ghost_woman'] else 'neutral'
  im=Image.open(O/id/f'{exp}.png').convert('RGBA');im.thumbnail((280,330))
  sheet.paste(im,(x+(cw-im.width)//2,y+7),im)
  d.text((x+cw/2,y+355),colors[id]['label'],font=font,fill='#20282c',anchor='mm')
 sheet.save(O/file,quality=94)
lineup([x['id'] for x in meta['characters'][:9]],'people.jpg',3)
lineup([x['id'] for x in meta['characters'][9:]],'ghosts.jpg',4)
lineup(meta['npcs'],'npcs.jpg',4)
# Effect sources and exported transparent PNGs.
fxdir=O/'effects';fxdir.mkdir(exist_ok=True)
sheet=Image.new('RGB',(1200,720),'#d3d0c5');d=ImageDraw.Draw(sheet)
for i,id in enumerate(meta['effects']):
 im=pack.raster(id,180);im.save(fxdir/f'{id}.png');im.thumbnail((260,195));x=i%4*300;y=i//4*240
 sheet.paste(im,(x+(300-im.width)//2,y+5),im);d.text((x+150,y+220),id.replace('stung_',''),font=font,fill='#22282d',anchor='mm')
sheet.save(O/'effects.jpg',quality=94)
# Exploded source-parts board for Narrator. Every tile is from an actual SVG part.
c=Character({'preset':'stung_narrator'},640);names=['head','hair_front','hair_back','neck','torso','upper_arm','forearm','hand','thigh','shin','foot','bag','scarf','flashlight','eyes_neutral','brows_neutral','mouth_neutral','mouth_open']
sheet=Image.new('RGB',(1200,math.ceil(len(names)/6)*220),'#d4d1c8');d=ImageDraw.Draw(sheet)
for i,name in enumerate(names):
 text=(E/'characters/stung_narrator'/f'{name}.svg').read_text();im=render(text,170,180)
 x=i%6*200;y=i//6*220;sheet.paste(im,(x+15,y),im);d.text((x+100,y+200),name,font=small,fill='#22282d',anchor='mm')
sheet.save(O/'parts.jpg',quality=94)
(O/'verification.json').write_text(json.dumps({'characters':checks,'source_expressions':expressions,'effects':len(meta['effects']),'engine_expressions':meta['runtime_expressions'],'note':'22 expressions exported as independent source and transparent previews; only seven enums selectable in scenes/1.'},indent=2)+'\n')
print('Previews and editable assembled sources:',O)
