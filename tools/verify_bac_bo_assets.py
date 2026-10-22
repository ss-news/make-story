"""Validate the delivered library and all renderer poses, including flipped/walk states."""
import json
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from storyvid.character import ARM_POSES
from tools.export_bac_bo_assets import OUT, PACK, EXPRESSIONS, make_character


def main():
    manifest=json.loads((OUT/'manifest.json').read_text())
    counts=Counter(a['group'] for a in manifest['assets'])
    assert counts=={'animals':9,'props':19,'backgrounds':16,'effects':8},counts
    xml_count=0
    for file in (OUT/'sources').rglob('*.svg'):
        ET.fromstring(file.read_text());xml_count+=1
    png_count=0
    for file in OUT.rglob('*.png'):
        with Image.open(file) as pic:
            pic.verify()
        png_count+=1
    for item in manifest['assets']:
        with Image.open(OUT/item['png']) as pic:
            assert pic.mode=='RGBA',(item['id'],pic.mode)
            if item['group']!='backgrounds':
                alpha=pic.getchannel('A')
                assert alpha.getextrema()[0]==0,item['id']
                assert alpha.getbbox(),item['id']
            else:
                assert pic.size==(1920,1080)
                assert pic.getchannel('A').getextrema()==(255,255)
    states=0
    for preset in manifest['characters']:
        ch=make_character(preset,320)
        for pose in ARM_POSES:
            for exp in EXPRESSIONS:
                for flip in (False,True):
                    pic=ch.sprite(pose,exp,states%3,states%11==0,flip,step=states%4)
                    bounds=pic.getbbox()
                    assert bounds and bounds[0]>0 and bounds[1]>0 and bounds[2]<pic.width and bounds[3]<pic.height,(preset,pose,exp,flip,bounds)
                    assert pic.getpixel((0,0))[3]==0
                    states+=1
    print(json.dumps({'source_svgs':xml_count,'png_files':png_count,'render_states_checked':states,'asset_counts':dict(counts),'characters':len(manifest['characters'])},indent=2))


if __name__=='__main__':
    main()
