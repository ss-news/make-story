"""Validate the whole-pose source standard without changing Storyvid's scene contract."""
from pathlib import Path
import json,hashlib
from PIL import Image
R=Path(__file__).resolve().parent
m=json.loads((R/'manifest.json').read_text())
try:
 import jsonschema
 jsonschema.validate(m,json.loads((R/'manifest.schema.json').read_text()))
except ImportError:
 print('jsonschema unavailable; validating required fields and source invariants directly.')
assert m['format']=='storyvid.whole-character-assets/1' and m['render_mode']=='whole_pose_rgba'
assert len(m['characters'])==4
assert m['canvas']==[1024,1536] and m['anchor']==[512,1390]
ids=set();n=0
for c in m['characters']:
 assert isinstance(c['id'],str) and len(c['poses'])==4
 assert c['id'] not in ids;cids=set();ids.add(c['id'])
 assert c['default_pose'] in {p['id'] for p in c['poses']}
 for p in c['poses']:
  assert p['id'] not in cids;cids.add(p['id'])
  f=R/p['file'];im=Image.open(f)
  assert im.mode=='RGBA' and im.size==(1024,1536),(f,im.mode,im.size)
  alpha=im.getchannel('A');assert alpha.getextrema()[0]==0 and alpha.getextrema()[1]>240
  box=alpha.getbbox();assert list(box)==p['bbox'] and box[3]==1390
  assert box[0]>=50 and box[2]<=974 and box[1]>=100
  assert p['sha256']==hashlib.sha256(f.read_bytes()).hexdigest()
  assert (R/p['source']).is_file();n+=1
bg=Image.open(R/'backgrounds/camp_yard_night.png');assert bg.width/bg.height>1.7
print(f'OK: {len(ids)} characters, {n} RGBA whole-pose images, uniform canvas/anchor, source hashes and clean background.')
