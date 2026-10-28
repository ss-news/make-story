"""Encode and validate Blender output. No image generation or Storyvid changes."""
import sys,json,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;ROOT=R.parents[3];sys.path.insert(0,str(ROOT))
from storyvid.ffmpeg import ffmpeg_exe
O=ROOT/'output/stung_treng/blender';frames=O/'frames-final';files=sorted(frames.glob('frame-*.png'))
assert len(files)==288, f'Incomplete Blender render: {len(files)}/288 frames'
for f in files:
 im=Image.open(f);im.load();assert im.size==(960,540),f
ff=ffmpeg_exe()
def run(args):subprocess.run([ff,'-y','-v','error',*map(str,args)],check=True)
video=O/'whole-ghosts-preview.mp4';gif=O/'whole-ghosts-preview.gif';palette=O/'palette.png'
run(['-framerate','12','-i',frames/'frame-%04d.png','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',video])
run(['-i',video,'-vf','fps=8,scale=640:-1:flags=lanczos,palettegen=stats_mode=diff','-frames:v','1',palette])
run(['-i',video,'-i',palette,'-lavfi','fps=8,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle','-loop','0',gif])
# Decode the whole encoded MP4, not only its header.
run(['-i',video,'-f','null','-'])
from PIL import ImageSequence
im=Image.open(gif);dur=0;n=0
for fr in ImageSequence.Iterator(im):fr.load();dur+=fr.info.get('duration',0);n+=1
assert 23900<=dur<=24100,(n,dur)
board=Image.new('RGB',(1920,1080))
for i,frame in enumerate([28,82,154,226]):board.paste(Image.open(frames/f'frame-{frame:04}.png').convert('RGB'),((i%2)*960,(i//2)*540))
board.save(O/'blender-contact.jpg',quality=94)
rep={'blender_frames':288,'resolution':[960,540],'fps':12,'duration_seconds':24,'gif_frames':n,'gif_duration_seconds':dur/1000,'mp4_full_decode':True,'frame_images_verified':True,'source_pack':str(R/'manifest.json')}
(O/'render-verification.json').write_text(json.dumps(rep,indent=2)+'\n');print(rep)
