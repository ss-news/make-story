"""Encode the real Blender renders as a 12-second MP4/GIF and inspect every frame."""
from pathlib import Path
import sys,subprocess,json
from PIL import Image,ImageSequence
P=Path(__file__).resolve().parent;ROOT=P.parents[3];sys.path.insert(0,str(ROOT))
from storyvid.ffmpeg import ffmpeg_exe
O=ROOT/'output/stung_treng/human-action-blender';F=O/'frames';frames=sorted(F.glob('frame-*.png'));assert len(frames)==288,len(frames)
for p in frames:
 im=Image.open(p);im.load();assert im.size==(960,540)
ff=ffmpeg_exe()
def run(args):subprocess.run([ff,'-y','-v','error',*map(str,args)],check=True)
mp4=O/'narrator-actions.mp4';gif=O/'narrator-actions.gif';palette=O/'palette.png'
run(['-framerate','24','-i',F/'frame-%04d.png','-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',mp4])
run(['-i',mp4,'-vf','fps=12,scale=640:-1:flags=lanczos,palettegen=stats_mode=diff','-frames:v','1',palette])
run(['-i',mp4,'-i',palette,'-lavfi','fps=12,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse=dither=sierra2_4a:diff_mode=rectangle','-loop','0',gif])
run(['-i',mp4,'-f','null','-'])
im=Image.open(gif);dur=0;n=0
for frame in ImageSequence.Iterator(im):frame.load();dur+=frame.info.get('duration',0);n+=1
assert 11900<=dur<=12100
board=Image.new('RGB',(1920,540))
for i,f in enumerate([24,60,96,126,162,192,228,270]):board.paste(Image.open(F/f'frame-{f:04}.png').convert('RGB').resize((480,270),Image.Resampling.LANCZOS),((i%4)*480,(i//4)*270))
board.save(O/'action-contact.jpg',quality=94)
report={'source':'Blender armature render','frames':288,'fps':24,'seconds':12,'size':[960,540],'mp4_full_decode':True,'gif_frames':n,'gif_seconds':dur/1000}
(O/'render-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(report)
