"""Export transparent PNGs, usable rigs, a visual catalogue and an animation preview."""
import html
import io
import json
import math
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import resvg_py
from PIL import Image, ImageDraw, ImageFont
from storyvid.character import Character, ARM_POSES
from storyvid.character_catalog import PRESETS
from storyvid.ffmpeg import ffmpeg_exe

ROOT=Path(__file__).resolve().parents[1]
PACK=ROOT/'assets'/'bac-bo-stick'
OUT=ROOT/'output'/'bac-bo-stick'
FONT='/System/Library/Fonts/Supplemental/Arial.ttf'
EXPRESSIONS=('neutral','happy','scared','surprised','sad','angry','smirk')
PALETTES=('#88624a','#88624a','#766044','#80614d','#485f6a','#b07859','#7c7053','#88624a')


def font(size):
    return ImageFont.truetype(FONT,size)


def raster(source,width=None,height=None):
    args={'svg_string':source}
    if width: args['width']=width
    if height: args['height']=height
    return Image.open(io.BytesIO(resvg_py.svg_to_bytes(**args))).convert('RGBA')


def make_character(preset,height=440):
    color=PALETTES[list(PRESETS).index(preset)]
    return Character({'preset':preset,'outfit':'earth','accessory':'none','shirt_color':color,
                      'skin_color':'#ffffff','hair_color':'#272525','outline_color':'#24211f'},height,
                     asset_root=PACK/'characters')


def contain(image,size):
    image=image.copy()
    image.thumbnail(size,Image.Resampling.LANCZOS)
    return image


def sheet(title,items,destination,cols=4,cell=(350,340)):
    cw,ch=cell
    pic=Image.new('RGB',(cols*cw,math.ceil(len(items)/cols)*ch+100),'#faf7ef')
    d=ImageDraw.Draw(pic)
    d.text((28,18),title,font=font(27),fill='#292521')
    d.text((28,58),'BẮC BỘ / MẪU 10 · NGƯỜI QUE VẼ TAY',font=font(16),fill='#776b5d')
    for i,(label,asset) in enumerate(items):
        x,y=(i%cols)*cw,100+(i//cols)*ch
        d.rounded_rectangle((x+8,y+4,x+cw-8,y+ch-9),radius=12,fill='#ffffff',outline='#e1dacd')
        asset=contain(asset,(cw-36,ch-65))
        pic.paste(asset,(x+(cw-asset.width)//2,y+12+(ch-65-asset.height)//2),asset)
        d.text((x+18,y+ch-40),label,font=font(18),fill='#292521')
    pic.save(destination)
    return pic


def export_characters():
    gallery=[]
    expressions=[]
    for preset,info in PRESETS.items():
        folder=OUT/'characters'/preset
        for sub in ('parts','poses','expressions','mouths'):
            (folder/sub).mkdir(parents=True,exist_ok=True)
        ch=make_character(preset)
        default='surprised' if preset in ('young_man','boy','middle_man') else 'scared'
        pic=ch.sprite('scared',default,0,False,False)
        pic.save(folder/'character.png')
        (folder/'character.svg').write_text(ch.svg('scared',default))
        (folder/'character.json').write_text(json.dumps(ch.config,ensure_ascii=False,indent=2)+'\n')
        gallery.append((info['label'],pic))
        for name,body in ch.parts.items():
            source=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-140 -150 280 330" width="280" height="330">{body}</svg>'
            raster(source).save(folder/'parts'/(name+'.png'))
        for pose in ARM_POSES:
            ch.sprite(pose,default,0,False,False).save(folder/'poses'/(pose+'.png'))
            (folder/'poses'/(pose+'.svg')).write_text(ch.svg(pose,default))
        for exp in EXPRESSIONS:
            pic=ch.sprite('idle',exp,0,False,False)
            pic.save(folder/'expressions'/(exp+'.png'))
            (folder/'expressions'/(exp+'.svg')).write_text(ch.svg('idle',exp))
            if preset=='young_man': expressions.append((exp,pic))
        for mouth in range(3):
            ch.sprite('talk','neutral',mouth,False,False).save(folder/'mouths'/f'{mouth}.png')
        ch.sprite('idle','neutral',0,True,False).save(folder/'expressions'/'blink.png')
        for step in range(4):
            ch.sprite('idle','neutral',0,False,False,step=step).save(folder/'poses'/f'walk-{step}.png')
    sheet('8 NHÂN VẬT / BIỂU CẢM CƯỜNG ĐIỆU',gallery,OUT/'cast-gallery.png',cell=(350,450))
    sheet('BIỂU CẢM / MẮT — MÀY — MIỆNG ĐỘC LẬP',expressions,OUT/'expressions-sheet.png',cols=7,cell=(220,320))
    return gallery


def export_assets(manifest):
    sheets={}
    for item in manifest['assets']:
        source=PACK/item['svg']
        dest=OUT/item['group']/(item['id']+'.png')
        dest.parent.mkdir(exist_ok=True)
        bg=item['group']=='backgrounds'
        pic=raster(source.read_text(),1920 if bg else 960,1080 if bg else 720)
        pic.save(dest)
        item['png']=str(dest.relative_to(OUT))
        sheets.setdefault(item['group'],[]).append((item['label'],pic))
    titles={'animals':'ĐỘNG VẬT / NÉT TAY TỐI GIẢN','props':'ĐẠO CỤ VÀ TRANG PHỤC BẮC BỘ','backgrounds':'BỐI CẢNH / NGÀY VÀ ĐÊM','effects':'HIỆU ỨNG TRUYỆN TRANH'}
    for group,items in sheets.items():
        sheet(titles[group],items,OUT/(group+'-sheet.png'),cols=4,cell=(420,300) if group=='backgrounds' else (350,290))


def compose_preview():
    bg=Image.open(OUT/'backgrounds'/'courtyard_day.png').convert('RGBA').resize((1600,900))
    # Background remains sparse; characters occupy the lower reading plane.
    old=make_character('elder_man',620).sprite('scared','surprised',0,False,False)
    woman=make_character('young_woman',620).sprite('scared','scared',0,False,False)
    buffalo=Image.open(OUT/'animals'/'buffalo.png').convert('RGBA').resize((600,450))
    bg.alpha_composite(old,(135,245));bg.alpha_composite(woman,(580,245));bg.alpha_composite(buffalo,(970,405))
    bg.convert('RGB').save(OUT/'scene-preview.png')


def export_catalog(manifest):
    cards=[]
    for preset,info in PRESETS.items():
        cards.append(f'<article data-group="characters"><img src="characters/{preset}/character.png" alt="{html.escape(info["label"])}"><h3>{html.escape(info["label"])}</h3><a href="characters/{preset}/character.svg">SVG ghép</a> · <a href="sources/characters/{preset}/rig.json">Rig + mảnh</a></article>')
    for item in manifest['assets']:
        cards.append(f'<article data-group="{item["group"]}"><img loading="lazy" src="{item["png"]}" alt="{html.escape(item["label"])}"><h3>{html.escape(item["label"])}</h3><a href="sources/{item["svg"]}">SVG</a> · <a href="{item["png"]}">PNG</a></article>')
    (OUT/'index.html').write_text('''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Bắc Bộ — Người que vẽ tay</title><style>
*{box-sizing:border-box}body{margin:0;background:#faf7ef;color:#28231e;font:16px system-ui}header,main{max-width:1400px;margin:auto;padding:24px}h1{font-size:clamp(26px,4vw,44px);margin-bottom:8px}p{line-height:1.6}nav{display:flex;gap:8px;flex-wrap:wrap;margin:24px 0}button{padding:10px 15px;border:1px solid #bdad96;background:white;border-radius:8px;cursor:pointer}button[aria-pressed=true]{background:#88624a;color:white}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:18px}article{background:white;border:1px solid #e4ddcf;padding:16px;border-radius:12px}article[hidden]{display:none}article img{width:100%;height:240px;object-fit:contain;background:repeating-conic-gradient(#f5f3ed 0% 25%,white 0% 50%) 50%/20px 20px}h3{font-size:17px}a{color:#775138}.hero{width:100%;border-radius:12px}video{width:100%;max-height:500px;background:white}.hint{color:#796d5d}</style><header>
<p>BỘ ASSETS / MẪU 10 ĐÃ DUYỆT</p><h1>Người que vẽ tay · Làng quê Bắc Bộ</h1><p>8 nhân vật tách mảnh, 9 động vật, 19 đạo cụ/trang phục, 16 nền ngày/đêm và 8 hiệu ứng. Nguồn SVG có thể sửa; PNG nền trong suốt trừ cảnh nền.</p><img class="hero" src="scene-preview.png" alt="Cảnh thử ông lão, cô gái và trâu"><p class="hint">Tạo hình hoạt hình cách điệu; clip bên dưới kiểm tra chuyển động, không có lời kể.</p><video controls preload="metadata" src="motion-demo.mp4" poster="cast-gallery.png"></video>
<nav aria-label="Lọc assets">'''+''.join(f'<button type="button" data-filter="{key}" aria-pressed="{str(key=="all").lower()}">{label}</button>' for key,label in [('all','Tất cả'),('characters','Nhân vật'),('animals','Động vật'),('props','Đạo cụ'),('backgrounds','Cảnh nền'),('effects','Hiệu ứng')])+'''</nav></header><main class="grid">'''+''.join(cards)+'''</main><script>document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));document.querySelectorAll('article').forEach(x=>x.hidden=b.dataset.filter!=='all'&&x.dataset.group!==b.dataset.filter)})</script></html>''')


def export_motion():
    w,h,fps=960,540,15
    ffmpeg=ffmpeg_exe()
    cmd=[ffmpeg,'-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-an','-c:v','libx264','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT/'motion-demo.mp4')]
    proc=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    bg=Image.open(OUT/'backgrounds'/'courtyard_day.png').convert('RGB').resize((w,h))
    buffalo=Image.open(OUT/'animals'/'buffalo.png').convert('RGBA').resize((330,248))
    for index,(preset,info) in enumerate(PRESETS.items()):
        character=make_character(preset,420)
        for frame in range(3*fps):
            pic=bg.copy();d=ImageDraw.Draw(pic)
            d.rectangle((0,0,w,62),fill='#faf7ef')
            d.text((22,12),f'{info["label"]} / MẪU 10',font=font(24),fill='#28231e')
            block=frame//9
            pose=('idle','talk','scared','wave','point')[block]
            exp=('neutral','happy','scared','surprised','angry')[block]
            actor=character.sprite(pose,exp,frame%3,frame%37==0,index%2==1,step=frame%4 if block==0 else None)
            pic.paste(actor,(210,80+round(math.sin(frame*.4)*2)),actor)
            pic.paste(buffalo,(580,264),buffalo)
            proc.stdin.write(pic.tobytes())
    proc.stdin.close()
    if proc.wait()!=0: raise RuntimeError('ffmpeg motion export failed')
    subprocess.run([ffmpeg,'-v','error','-i',str(OUT/'motion-demo.mp4'),'-f','null','-'],check=True)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    shutil.copytree(PACK,OUT/'sources',dirs_exist_ok=True)
    manifest=json.loads((PACK/'manifest.json').read_text())
    export_characters()
    export_assets(manifest)
    compose_preview()
    export_motion()
    export_catalog(manifest)
    manifest['counts']=dict(Counter(a['group'] for a in manifest['assets']))
    manifest['counts']['characters']=len(PRESETS)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest['counts']))
    print(OUT/'index.html')


if __name__=='__main__':
    main()
