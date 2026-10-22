"""Export cast gallery, editable assembled SVGs and individually transparent part PNGs."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
import resvg_py
from storyvid.character import Character
from storyvid.character_catalog import PRESETS, resolve_character
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'character-library'
OUT.mkdir(parents=True, exist_ok=True)
font_path = '/System/Library/Fonts/Supplemental/Arial.ttf'
def font(n): return ImageFont.truetype(font_path,n)
host = json.loads((ROOT/'channel.json').read_text())['host']
sheet=Image.new('RGB',(1600,1180),'#eee9df'); d=ImageDraw.Draw(sheet)
d.text((50,30),'WEIRD VIETNAM / BỘ NHÂN VẬT',font=font(32),fill='#343c35')
d.text((50,76),'8 nhân vật · Mảnh SVG độc lập · Trang phục và phụ kiện theo từng video',font=font(20),fill='#777a6b')
for i,(preset,info) in enumerate(PRESETS.items()):
    x,y=40+(i%4)*390,125+(i//4)*510
    d.rounded_rectangle((x,y,x+365,y+485),radius=20,fill='#faf8f1')
    config=resolve_character(host,{'preset':preset,'outfit':['earth','indigo','moss','cream'][i%4], 'accessory':['none','bag','scarf','none'][i%4]})
    ch=Character(config,440)
    pic=ch.sprite('idle','neutral',0,False,False)
    sheet.paste(pic,(x+(365-pic.width)//2,y+3),pic)
    d.text((x+22,y+447),info['label'],font=font(21),fill='#3b453d')
    folder=OUT/preset; folder.mkdir(exist_ok=True)
    pic.save(folder/'character.png')
    (folder/'character.svg').write_text(ch.svg())
    (folder/'character.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
    for part,body in ch.parts.items():
        data=resvg_py.svg_to_bytes(svg_string=f'<svg xmlns="http://www.w3.org/2000/svg" width="240" height="300" viewBox="-120 -130 240 300">{body}</svg>')
        (folder/f'{part}.png').write_bytes(data)
sheet.save(OUT/'cast-gallery.png')
ch=Character(resolve_character(host,{'preset':'young_man'}),440)
parts=[p for p in ch.parts if not p.startswith(("eyes_","brows_","mouth_"))]+["eyes_neutral","eyes_closed","brows_angry","mouth_open"]
parts_sheet=Image.new('RGB',(1440,((len(parts)+5)//6)*350+100),'#eee9df');pd=ImageDraw.Draw(parts_sheet)
pd.text((30,25),'TÂM / CÁC MẢNH THAY THẾ',font=font(28),fill='#343c35')
for i,part in enumerate(parts):
    x,y=(i%6)*240,80+(i//6)*350
    pic=Image.open(OUT/'young_man'/f'{part}.png')
    parts_sheet.paste(pic,(x,y),pic)
    pd.text((x+15,y+310),part,font=font(17),fill='#3b453d')
parts_sheet.save(OUT/'parts-sheet.png')
print(OUT/'cast-gallery.png'); print(OUT/'parts-sheet.png')
