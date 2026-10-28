"""Normalize approved whole-character RGBA poses, validate and build a contact sheet.
Run after generation: .venv/bin/python assets/bac-bo-stick/extra/whole-ghosts-v1/normalize.py
"""
import json,hashlib,math
from pathlib import Path
from collections import deque
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
CHARS={
 'legless_ghost_woman':dict(label='The Woman',poses=['float_neutral','plead','bow','raise_head'],head_width=325,default='plead',height=3.5),
 'kneeling_ghost_woman':dict(label='Kneeling Woman',poses=['kneel','deep_bow','crawl','look_up'],head_width=None,default='kneel',height=1.3),
 'ghost_boy':dict(label='Boy',poses=['stand','hold_hand','turn','lower_head'],head_width=290,default='stand',height=3.0),
 'fanged_ghost_child':dict(label='Small Child',poses=['stand','lean','look_up','reach'],head_width=230,default='stand',height=2.1)}
SIZE=(1024,1536);BASELINE=1390

def largest_white(a):
 rgb=a[:,:,:3].astype(float)
 mask=(rgb.min(2)>215)&((rgb.max(2)-rgb.min(2))<38)&(a[:,:,3]>200)
 # Bounding box of the largest white connected region: the opaque face, not teeth.
 seen=np.zeros(mask.shape,bool);best=[];H,W=mask.shape
 for y,x in zip(*np.where(mask)):
  if seen[y,x]:continue
  q=[(int(x),int(y))];seen[y,x]=True;pts=[]
  while q:
   xx,yy=q.pop();pts.append((xx,yy))
   for nx,ny in [(xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)]:
    if 0<=nx<W and 0<=ny<H and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;q.append((nx,ny))
  if len(pts)>len(best):best=pts
 if len(best)<180:return None
 return [min(x for x,y in best),min(y for x,y in best),max(x for x,y in best)+1,max(y for x,y in best)+1]

out={'format':'storyvid.whole-character-assets/1','canvas':list(SIZE),'anchor':[512,BASELINE],'units':'pixels','render_mode':'whole_pose_rgba','characters':[],'generation':'ImageGen edits from approved reference; no limb slicing; native PNG alpha preserved'}
for id,spec in CHARS.items():
 entries=[]
 for pose in spec['poses']:
  dest=R/'characters'/id/f'{pose}.png';raw=R/'source'/id/f'{pose}.png';raw.parent.mkdir(parents=True,exist_ok=True)
  if not raw.exists():raw.write_bytes(dest.read_bytes())
  im=Image.open(raw).convert('RGBA');a=np.array(im)
  if a[:,:,3].min()!=0:raise ValueError(f'{id}/{pose}: not transparent')
  a[a[:,:,3]<8,3]=0
  im=Image.fromarray(a)
  bbox=im.getchannel('A').getbbox()
  if bbox is None:raise ValueError(f'{id}/{pose}: empty')
  if min(bbox[0],bbox[1],im.width-bbox[2],im.height-bbox[3])<2:raise ValueError(f'{id}/{pose}: silhouette touches canvas edge')
  face=largest_white(a) if spec['head_width'] else None
  crop=im.crop(bbox);scale=spec['head_width']/(face[2]-face[0]) if face else 750/crop.width
  # Full image is scaled as one piece. No stretching or redrawing.
  target_h={
   'legless_ghost_woman':{'float_neutral':1130,'plead':1130,'bow':1070,'raise_head':1150},
   'ghost_boy':{'stand':1060,'hold_hand':1060,'turn':1060,'lower_head':1030},
   'fanged_ghost_child':{'stand':790,'lean':770,'look_up':800,'reach':800}}
  if id in target_h:scale=target_h[id][pose]/crop.height
  scale=min(scale,900/crop.width,1250/crop.height)
  crop=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
  aa=np.asarray(crop).copy();aa[aa[:,:,3]<4,3]=0;crop=Image.fromarray(aa)
  crop=crop.crop(crop.getchannel('A').getbbox())
  canvas=Image.new('RGBA',SIZE);pos=(round((SIZE[0]-crop.width)/2),BASELINE-crop.height)
  canvas.alpha_composite(crop,pos);canvas.save(dest)
  box=canvas.getchannel('A').getbbox()
  entries.append(dict(id=pose,file=str(dest.relative_to(R)),source=str(raw.relative_to(R)),bbox=list(box),size=list(SIZE),anchor=[512,BASELINE],scale_from_source=scale,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
 out['characters'].append(dict(id=id,label=spec['label'],default_pose=spec['default'],blender_height=spec['height'],poses=entries))
(R/'manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
O=R.parents[3]/'output/stung_treng/blender';O.mkdir(parents=True,exist_ok=True)
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',19)
cell=(320,480);sheet=Image.new('RGB',(cell[0]*4,cell[1]*4),'#c8c9c3');d=ImageDraw.Draw(sheet)
for row,c in enumerate(out['characters']):
 for col,item in enumerate(c['poses']):
  im=Image.open(R/item['file']);im.thumbnail((295,415),Image.Resampling.LANCZOS)
  x=col*cell[0];y=row*cell[1];sheet.paste(im,(x+(cell[0]-im.width)//2,y+5),im)
  d.text((x+160,y+440),c['label'],font=font,fill='#20282c',anchor='mm');d.text((x+160,y+466),item['id'],font=font,fill='#20282c',anchor='mm')
sheet.save(O/'whole-ghosts-contact.jpg',quality=94)
print('Normalized 16 whole-pose images:',R/'manifest.json')
