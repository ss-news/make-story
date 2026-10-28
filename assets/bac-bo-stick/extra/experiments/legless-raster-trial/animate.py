"""Split the approved transparent model sheet and assemble an articulated GIF.
Usage: .venv/bin/python output/stung_treng/character-trial/animate.py
Pillow + NumPy only; no image-generation calls, no storyvid modifications.
"""
from pathlib import Path
import json, math, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
SOURCE_DIR=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out',type=Path,help='Output folder; defaults to the script folder')
args=parser.parse_args()
ROOT=(args.out or SOURCE_DIR).resolve();ROOT.mkdir(parents=True,exist_ok=True)
PARTS=ROOT/'parts';PARTS.mkdir(exist_ok=True)
SOURCE=SOURCE_DIR/'atlas-transparent.png'
W,H=800,760
FPS=15;DURATION=12
INK='#15191e'
# Coordinates refer to the preserved 1774x887 approved atlas.
BOXES={
 'hair_front':(440,637,671,874),'hair_back':(670,637,909,873),
 'head_blank':(906,671,1088,830),'torso':(1116,684,1331,854),
 'upper_arm_left':(1374,685,1412,759),'upper_arm_right':(1443,685,1479,758),
 'forearm_left':(1353,760,1383,834),'forearm_right':(1469,760,1498,834),
 'arm_straight_left':(1521,684,1558,764),'arm_straight_right':(1589,683,1626,763),
 'hand_left':(1520,777,1560,836),'hand_right':(1589,776,1628,835),
 'wisp':(150,710,320,846)}
FACEBOXES={
 'neutral':(639,108,781,222),'happy':(946,110,1077,224),
 'sad':(1249,110,1385,228),'scared':(1545,104,1679,225),
 'embarrassed':(632,440,776,554),'shy_happy':(937,435,1084,553),
 'crying':(1236,433,1381,554),'pleading':(1540,422,1680,551)}
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
def tight(im):
 box=im.getchannel('A').getbbox()
 if not box:raise ValueError('Empty alpha layer')
 return im.crop(box)
def save_part(id,im):
 im.save(PARTS/f'{id}.png');return im

def extract():
 atlas=Image.open(SOURCE).convert('RGBA')
 if atlas.size!=(1774,887):raise ValueError(f'Atlas changed dimensions: {atlas.size}; recalibrate crop boxes')
 assert atlas.getchannel('A').getextrema()==(0,255)
 data={}
 for id,box in BOXES.items():data[id]=save_part(id,tight(atlas.crop(box)))
 # Keep only ink/color from each face. Opaque white head stays a distinct layer.
 for id,box in FACEBOXES.items():
  im=atlas.crop(box).resize((200,164),Image.Resampling.LANCZOS)
  arr=np.asarray(im).copy();rgb=arr[:,:,:3].astype(float)
  lum=rgb.mean(axis=2);sat=rgb.max(axis=2)-rgb.min(axis=2)
  alpha=np.where(lum<195,np.clip((235-lum)/55,0,1),0)
  alpha=np.where((sat>24)&(lum<245),np.maximum(alpha,.8),alpha)
  alpha*=arr[:,:,3]/255
  arr[:,:,3]=(alpha*255).astype('uint8')
  # Decontaminate antialiased ink edges against the former white face.
  neutral=(sat<25)&(arr[:,:,3]>0)
  arr[neutral,:3]=np.minimum(arr[neutral,:3],40)
  # Hair/chin fragments touch the crop boundary. Flood them away, keeping only
  # internally isolated facial ink, blush and tears as a real separate layer.
  mask=arr[:,:,3]>0;seen=np.zeros(mask.shape,bool);stack=[]
  hh,ww=mask.shape
  for xx in range(ww):
   if mask[0,xx]:stack.append((xx,0))
   if mask[hh-1,xx]:stack.append((xx,hh-1))
  for yy in range(hh):
   if mask[yy,0]:stack.append((0,yy))
   if mask[yy,ww-1]:stack.append((ww-1,yy))
  while stack:
   xx,yy=stack.pop()
   if seen[yy,xx]:continue
   seen[yy,xx]=True
   for nx,ny in [(xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)]:
    if 0<=nx<ww and 0<=ny<hh and mask[ny,nx] and not seen[ny,nx]:stack.append((nx,ny))
  arr[seen,3]=0
  data['face_'+id]=save_part('face_'+id,Image.fromarray(arr))
 # Tear linework touches the chin in the source crop, so extract its cyan ink
 # separately and place it beneath the intact sad eyes rather than losing an eye.
 tear_source=np.asarray(atlas.crop(FACEBOXES['crying']).resize((200,164),Image.Resampling.LANCZOS)).copy()
 rgb=tear_source[:,:,:3].astype(float)
 cyan=(rgb[:,:,2]>rgb[:,:,0]*1.06)&(rgb[:,:,1]>rgb[:,:,0]*1.025)&((rgb.max(2)-rgb.min(2))>20)
 tear_source[:,:,3]=np.where(cyan,tear_source[:,:,3],0)
 crying=data['face_sad'].copy()
 for side,box,xy in [('left',(0,0,100,164),(32,77)),('right',(100,0,200,164),(132,77))]:
  tear=Image.fromarray(tear_source).crop(box)
  if tear.getbbox():
   tear=tight(tear).resize((14,56),Image.Resampling.LANCZOS)
   save_part('tear_'+side,tear);crying.alpha_composite(tear,xy)
 data['face_crying']=save_part('face_crying',crying)
 # Eye-close overlay: smile-eye linework from the happy source, mouth kept separately below.
 blink=data['face_happy'].copy();ba=np.asarray(blink).copy();ba[105:,:,3]=0
 data['eyes_closed']=save_part('eyes_closed',Image.fromarray(ba))
 for id in FACEBOXES:
  im=data['face_'+id];ar=np.asarray(im).copy()
  # Locate the isolated central mouth, since expressions move it vertically.
  mask=ar[:,:,3]>24;seen=np.zeros(mask.shape,bool);components=[]
  for yy,xx in zip(*np.where(mask)):
   if seen[yy,xx]:continue
   stack=[(int(xx),int(yy))];seen[yy,xx]=1;points=[]
   while stack:
    x,y=stack.pop();points.append((x,y))
    for nx,ny in [(x-1,y),(x+1,y),(x,y-1),(x,y+1)]:
     if 0<=nx<200 and 0<=ny<164 and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;stack.append((nx,ny))
   if len(points)>8:components.append(points)
  candidates=[c for c in components if 65<np.mean([x for x,y in c])<140 and np.mean([y for x,y in c])>70]
  assert candidates, 'No mouth found: '+id
  selected=min(candidates,key=lambda c:abs(np.mean([x for x,y in c])-100)*2+abs(np.mean([y for x,y in c])-130))
  mouth_mask=np.zeros(mask.shape,bool)
  for x,y in selected:mouth_mask[y,x]=True
  for name in ['brows','eyes','mouth']:
   layer=ar.copy()
   if name=='mouth':layer[~mouth_mask,3]=0
   else:
    layer[mouth_mask,3]=0
    if name=='brows':layer[48:,:,3]=0
    else:layer[:48,:,3]=0
   save_part(id+'_'+name,Image.fromarray(layer))
 (ROOT/'rig.json').write_text(json.dumps({'canvas':[W,H],'fps':FPS,'duration':DURATION,'source_canvas':[1774,887],'crop_boxes':BOXES,'face_boxes':FACEBOXES,'upper_arm_length':74,'forearm_length':86,'note':'Trial raster cutout rig, independent of storyvid; facial ink was extracted by the supplied script.'},indent=2)+'\n')
 return data

P=extract()
def resized(im,width):return im.resize((int(width),round(im.height*width/im.width)),Image.Resampling.LANCZOS)
def paste_center(dest,im,xy,opacity=1):
 if opacity!=1:
  im=im.copy();im.putalpha(im.getchannel('A').point(lambda a:round(a*opacity)))
 dest.alpha_composite(im,(round(xy[0]-im.width/2),round(xy[1]-im.height/2)))
def blend(a,b,u):return (a[0]+(b[0]-a[0])*u,a[1]+(b[1]-a[1])*u)
def ease(x):x=min(1,max(0,x));return x*x*(3-2*x)
def ik(shoulder,hand,side):
 a,b=74.,86.;dx,dy=hand[0]-shoulder[0],hand[1]-shoulder[1];r=max(1,min(a+b-.01,math.hypot(dx,dy)))
 along=(a*a-b*b+r*r)/(2*r);height=math.sqrt(max(0,a*a-along*along));ux,uy=dx/r,dy/r
 # Elbow bends away from the torso for both sides.
 ex=shoulder[0]+along*ux+side*height*uy;ey=shoulder[1]+along*uy-side*height*ux
 return ex,ey

def segment(dest,id,a,b):
 im=P[id];arr=np.asarray(im);yy,xx=np.where(arr[:,:,3]>100)
 coords=np.stack([xx,yy],axis=1);val,vec=np.linalg.eigh(np.cov(coords.T));axis=vec[:,-1]
 if axis[1]<0:axis=-axis
 source_angle=math.degrees(math.atan2(axis[0],axis[1]));target_angle=math.degrees(math.atan2(b[0]-a[0],b[1]-a[1]))
 span=np.ptp(coords@axis);scale=math.dist(a,b)/span
 im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
 im=im.rotate(target_angle-source_angle,resample=Image.Resampling.BICUBIC,expand=True)
 paste_center(dest,im,((a[0]+b[0])/2,(a[1]+b[1])/2))

def head_layer(expression='sad',look=0,blink=False):
 layer=Image.new('RGBA',(W,H))
 # Pieces share explicit placement coordinates, not regenerated silhouettes.
 paste_center(layer,resized(P['head_blank'],230),(430,285))
 face=P['face_'+expression].copy()
 if blink:
  ar=np.asarray(face).copy();ar[0:105,:,3]=0;face=Image.fromarray(ar)
  layer.alpha_composite(P['eyes_closed'],(330+look,210))
 layer.alpha_composite(face,(330+look,210))
 paste_center(layer,resized(P['hair_front'],350),(400,260))
 return layer

def figure(t):
 im=Image.new('RGBA',(W,H))
 bob=math.sin(t*math.pi*.9)*5
 prayer=ease((t-3.4)/1.5)
 if t>9.5:prayer=1-ease((t-9.5)/1.0)
 shoulderL=(343,403);shoulderR=(457,403)
 hands=[blend((326,542),(394,443),prayer),blend((474,542),(406,443),prayer)]
 elbows=[ik(shoulderL,hands[0],-1),ik(shoulderR,hands[1],1)]
 # Hair stays behind the body. It follows the same head pivot during the bow.
 back=Image.new('RGBA',(W,H));paste_center(back,resized(P['hair_back'],350),(400,260))
 bow=-10*math.sin(math.pi*ease((t-5.8)/1.9)) if 5.8<t<7.7 else 0
 if bow:back=back.rotate(bow,resample=Image.Resampling.BICUBIC,center=(400,385))
 im.alpha_composite(back)
 for side,sh,elbow in [('left',shoulderL,elbows[0]),('right',shoulderR,elbows[1])]:segment(im,'upper_arm_'+side,sh,elbow)
 paste_center(im,resized(P['torso'],202),(400,458))
 paste_center(im,resized(P['wisp'],122),(400,575),.80)
 for i,side in enumerate(['left','right']):
  segment(im,'forearm_'+side,elbows[i],hands[i])
  hand=resized(P['hand_'+side],16);paste_center(im,hand,hands[i])
 exp='sad';look=0;blink=False;angle=0
 if 1.35<t<1.53 or 3.0<t<3.17:blink=True
 if 1.8<t<2.5:look=-5
 elif 2.6<t<3.3:look=5
 if 4.6<t<6.8:exp='pleading'
 if 5.8<t<7.7:angle=-10*math.sin(math.pi*ease((t-5.8)/1.9))
 if 7.7<t<8.7:exp='crying'
 if 8.7<t<9.7:exp='shy_happy'
 head=head_layer(exp,look,blink)
 if angle:head=head.rotate(angle,resample=Image.Resampling.BICUBIC,center=(400,385))
 im.alpha_composite(head)
 # Whole-character float/fade happens after joints and all layers are assembled.
 moved=Image.new('RGBA',(W,H));moved.alpha_composite(im,(0,round(bob)))
 visibility=ease(t/.9)*(1-ease((t-10.5)/1.1))
 moved.putalpha(moved.getchannel('A').point(lambda a:round(a*visibility)))
 return moved

def background():
 im=Image.new('RGBA',(W,H),'#24313a');d=ImageDraw.Draw(im)
 d.ellipse((230,588,570,620),fill='#1b262d')
 f=ImageFont.truetype(FONT,22);small=ImageFont.truetype(FONT,16)
 d.text((400,40),'THỬ RÁP NHÂN VẬT TÁCH MẢNH',font=f,fill='#e9e6dc',anchor='mm')
 d.text((400,71),'Mảnh PNG từ mẫu duyệt · khớp tay điều khiển bằng script',font=small,fill='#b7c4c9',anchor='mm')
 return im

def label(t):
 if t<1.2:return 'Xuất hiện'
 if t<3.4:return 'Chớp mắt · nhìn trái, nhìn phải'
 if t<5.8:return 'Đưa tay lên · chắp tay cầu xin'
 if t<7.7:return 'Cúi đầu'
 if t<8.7:return 'Buồn · rơi nước mắt'
 if t<10.5:return 'Đổi biểu cảm · hạ tay'
 return 'Mờ dần'

def main():
 frames=[];bg=background();f=ImageFont.truetype(FONT,22)
 for i in range(round(DURATION*FPS)):
  t=i/FPS;frame=bg.copy();frame.alpha_composite(figure(t))
  ImageDraw.Draw(frame).text((400,700),label(t),font=f,fill='#e9e6dc',anchor='mm')
  frames.append(frame.convert('RGB'))
  if i in [20,65,95,120,140]:frame.save(ROOT/f'frame-{i:03}.png')
 # One global palette prevents per-frame color flicker and preserves face whites.
 sample=Image.new('RGB',(W*3,H*2))
 for j,k in enumerate([20,40,65,95,120,140]):sample.paste(frames[k],(j%3*W,j//3*H))
 palette=sample.quantize(colors=256,method=Image.Quantize.MEDIANCUT)
 paletted=[x.quantize(palette=palette,dither=Image.Dither.NONE) for x in frames]
 paletted[0].save(ROOT/'character-actions.gif',save_all=True,append_images=paletted[1:],duration=[round((i+1)*100/FPS)*10-round(i*100/FPS)*10 for i in range(len(paletted))],loop=0,optimize=False,disposal=2)
 # Contact sheet permits visual inspection of the joint extremes.
 sheet=Image.new('RGB',(W*3//2,H))
 for j,k in enumerate([20,40,65,95,120,140]):sheet.paste(frames[k].resize((W//2,H//2),Image.Resampling.LANCZOS),(j%3*(W//2),j//3*(H//2)))
 sheet.save(ROOT/'contact-sheet.jpg',quality=93)
 # Review board of real extracted alpha layers.
 board=Image.new('RGB',(1000,750),'#d2cfc6');d=ImageDraw.Draw(board);font=ImageFont.truetype(FONT,16)
 keys=['hair_front','hair_back','head_blank','torso','upper_arm_left','upper_arm_right','forearm_left','forearm_right','hand_left','hand_right','face_sad','face_crying']
 for j,key in enumerate(keys):
  im=P[key].copy();im.thumbnail((225,200));x=j%4*250;y=j//4*250
  board.paste(im,(x+(250-im.width)//2,y+10),im);d.text((x+125,y+225),key,font=font,fill='#22292d',anchor='mm')
 board.save(ROOT/'separated-parts.jpg',quality=94)
 print('Created:',ROOT/'character-actions.gif')
 print('Layers:',len(list(PARTS.glob('*.png'))),'Frames:',len(frames),'FPS:',FPS)
if __name__=='__main__':main()
