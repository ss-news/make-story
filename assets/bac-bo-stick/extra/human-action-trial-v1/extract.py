"""Extract the 20 approved drawing layers, without redrawing their contours."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent;O=R/'parts';O.mkdir(exist_ok=True)
names=['head_front','head_turn','head_scared','head_blink','torso','upper_arm_l','upper_arm_r','forearm_l','forearm_r','hand_l','hand_r','thigh_l','thigh_r','shin_l','shin_r','foot_l','foot_r','flashlight','shoulder_l','shoulder_r']
im=Image.open(R/'atlas.png').convert('RGBA');W,H=im.size;metadata={'format':'blender.layered-character/1','character':'Narrator','source_size':[W,H],'grid':[4,5],'parts':[]}
font=ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf',17)
board=Image.new('RGB',(1000,1250),'#cdd0c8');d=ImageDraw.Draw(board)
for i,name in enumerate(names):
 col=i%4;row=i//4;box=[round(col*W/4),round(row*H/5),round((col+1)*W/4),round((row+1)*H/5)]
 part=im.crop(box);a=np.asarray(part).copy();a[a[:,:,3]<8,3]=0;part=Image.fromarray(a)
 bounds=part.getchannel('A').getbbox();assert bounds is not None,name
 # A few atlas edge pixels can belong to a neighbor; crop the largest visible component.
 mask=a[:,:,3]>40;seen=np.zeros(mask.shape,bool);best=[];h,w=mask.shape
 for y,x in zip(*np.where(mask)):
  if seen[y,x]:continue
  q=[(int(x),int(y))];seen[y,x]=1;points=[]
  while q:
   xx,yy=q.pop();points.append((xx,yy))
   for nx,ny in [(xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)]:
    if 0<=nx<w and 0<=ny<h and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;q.append((nx,ny))
  if len(points)>len(best):best=points
 assert best,name
 x0=max(0,min(x for x,y in best)-3);y0=max(0,min(y for x,y in best)-3);x1=min(w,max(x for x,y in best)+4);y1=min(h,max(y for x,y in best)+4)
 part=part.crop((x0,y0,x1,y1));part.save(O/f'{name}.png')
 metadata['parts'].append({'id':name,'file':f'parts/{name}.png','atlas_cell':box,'size':list(part.size),'sha256':hashlib.sha256((O/f'{name}.png').read_bytes()).hexdigest()})
 thumb=part.copy();thumb.thumbnail((220,210));x=col*250;y=row*250;board.paste(thumb,(x+(250-thumb.width)//2,y+8),thumb);d.text((x+125,y+232),name,font=font,fill='#22282b',anchor='mm')
(R/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
P=R.parents[3]/'output/stung_treng/human-action-blender';P.mkdir(parents=True,exist_ok=True);board.save(P/'parts-contact.jpg',quality=94)
print('Extracted 20 RGBA drawing layers from',im.size)
