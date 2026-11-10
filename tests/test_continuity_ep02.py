"""Local integration test against the user's EP02 source, without AI/network calls.

The source is private and gitignored; this suite is skipped on checkouts without it.
All approvals and generated outputs belong to a disposable test project only.
"""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw
from storyvid import continuity, visuals, contract, auto
from storyvid.web.__main__ import app, OUTPUT

SOURCE = OUTPUT / "The Preacher's Satchel/source/EPISODES/EP02_FULL.md"


def build(d: Path):
    text = SOURCE.read_text()
    sections = re.split(r'^CẢNH (\d+) \([^\n]+\):[^\n]*\n', text, flags=re.M)
    sets = dict(re.findall(r'^(SET-\d+) ([^\n]+)', text, re.M))
    # SET LOCK only; later descriptions are resolved by the stable set code.
    sets = {k:v for k,v in sets.items() if k in {f'SET-{i:02d}' for i in range(1,7)}}
    style = text.split('[STYLE LOCK]:\n')[1].split('\n\n')[0]
    negative = text.split('[NEGATIVE]:\n')[1].split('\n\n')[0]
    actors = [('elias','Elias Crane','ELIAS'), ('henry','Henry Voss','HENRY'),
              ('peele','Mr. Peele','PEELE'), ('rigg','Amos Rigg','RIGG'), ('hattie','Hattie Coles','HATTIE')]
    looks = re.findall(r'^([A-Z .]+) — (.+)$',text,re.M)
    plan = {'format':'storyvid.visuals/1','scenes_file':'scenes.json','ratio':'16:9','style':style,
            'cast':[], 'scenes':[], 'continuity':'off'}
    script = {'format':'storyvid.scenes/1','title':'EP02 — The Paper With the Wrong Date (TEST)',
              'lang':'en','cast':[], 'short':{'scenes':[0]}, 'scenes':[]}
    assets = []
    (d / 'muse/cast').mkdir(parents=True,exist_ok=True)
    (d / 'refs/test').mkdir(parents=True,exist_ok=True)
    def picture(path,label):
        img=Image.new('RGB',(640,360),'#ded5c2');ImageDraw.Draw(img).text((24,24),'TEST ONLY — '+label,fill='#292a28');img.save(path)
    for cid,name,token in actors:
        look=next(v for k,v in looks if token in k)
        sheet=f'muse/cast/{cid}.png';picture(d/sheet,name)
        script['cast'].append({'id':cid,'name':name,'preset':'elder_woman' if cid=='hattie' else 'elder_man',
                              'outfit':'earth','accessory':'none','kind':'human'})
        plan['cast'].append({'id':cid,'look':look,'sheet':sheet})
    for set_id,desc in sets.items():
        key=set_id.lower().replace('-','_');image=f'refs/test/{key}.png';picture(d/image,desc)
        assets.append({'id':key,'kind':'place','name':desc.split(' — ')[0], 'description':desc,
                       'scenes':[],'image':image})
    for pos in range(1,len(sections),2):
        number=int(sections[pos]); body=sections[pos+1]
        def field(label):
            return re.search(r'^'+re.escape(label)+r': (.+)$',body,re.M).group(1)
        set_id=re.search(r'SET-\d+',field('Bối cảnh')).group()
        asset=next(a for a in assets if a['id']==set_id.lower().replace('-','_'))
        asset['scenes'].append(number)
        video=field('Prompt video')
        present=[{'id':cid,'position':'center','pose':'idle','expression':'neutral','action':'none'}
                 for cid,_,token in actors if re.search(r'\b'+token+r'\b',video)]
        script['scenes'].append({'bg_id':'courtyard_day','bg_prompt':asset['description'], 'camera':'static',
            'actors':present, 'props':[], 'lines':[{'speaker':'narrator','text':field('Voice')}], 'ambience':'wind_trees'})
        plan['scenes'].append({'image_prompt':field('Prompt ảnh khung đầu')+' Setting: '+asset['description'],
            'video_prompt':video+' Setting: '+asset['description'], 'negative':negative,'image':'','clip':''})
    assert len(sets) == 6
    assets = [a for a in assets if a["scenes"]]  # STORE is declared but unused by the source
    assert len(assets) == 5
    # A recurring story prop, explicitly limited to the first stove shots with at most one actor.
    stove_scenes=[i+1 for i,s in enumerate(plan['scenes'][:14]) if 'stove' in s['image_prompt'].split(' Setting: ')[0].lower()
                  and len(script['scenes'][i]['actors'])<=1]
    picture(d/'refs/test/stove.png','Cracked cast-iron stove')
    assets.append({'id':'stove','kind':'prop','name':'Voss stove', 'description':'Cracked cast-iron door, wired pipe',
                   'scenes':stove_scenes,'image':'refs/test/stove.png'})
    (d/'scenes.json').write_text(json.dumps(script));visuals.save(d,plan)
    (d/'meta.json').write_text(json.dumps({'name':'TEST EP02 — Khóa hình ảnh','lang':'en','genre':'drama',
        'approved_script':visuals.script_digest(script),'approved_cast':visuals.cast_digest(d,plan)}))
    (d/'story.txt').write_text('TEST ONLY: '+str(SOURCE))
    continuity.save(d,{'assets':assets})
    return script,plan,assets


@unittest.skipUnless(SOURCE.is_file(), 'Private EP02 source is not present')
class Ep02ContinuityTest(unittest.TestCase):
    def test_full_source_mapping_approval_and_generation(self):
        pid='_test_ep02_continuity_api';d=OUTPUT/pid;d.mkdir(exist_ok=True)
        self.addCleanup(lambda:shutil.rmtree(d,ignore_errors=True))
        script,plan,assets=build(d)
        self.assertEqual(len(script['scenes']),160)
        self.assertEqual(contract.validate_visuals(plan,script,d),[])
        self.assertEqual(contract.validate(script)[0],[])
        set_scenes=[n for a in assets if a['kind']=='place' for n in a['scenes']]
        self.assertEqual(sorted(set_scenes),list(range(1,161)))
        self.assertEqual(len(set(set_scenes)),160)
        self.assertIn(2,assets[0]['scenes'])
        self.assertEqual(continuity.errors(d),[])
        client=app.test_client();base=f'/api/projects/{pid}'
        with mock.patch('storyvid.web.__main__.start_job') as start:
            self.assertEqual(client.post(base+'/visuals/scenes',json={}).status_code,409)
            start.assert_not_called()
        self.assertEqual(client.post(base+'/continuity/approve',json={'reviewed':True}).status_code,200)
        with mock.patch('storyvid.web.__main__.start_job') as start:
            self.assertEqual(client.post(base+'/visuals/scenes',json={'only':'0,1','images_only':True}).status_code,200)
            self.assertIn('0,1',start.call_args.args[3])
            start.reset_mock()
            self.assertEqual(client.post(base+'/visuals/scenes',json={'only':'1,nope'}).status_code,400)
            self.assertEqual(client.post(base+'/visuals/scenes',json={'only':'160'}).status_code,400)
            start.assert_not_called()
        seen=[]
        def generate(media,prompt,size,target,references,negative=''):
            seen.append((media,prompt,references));target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes((media+str(target)).encode());return target
        # Generate one shot per set plus both initial shots: all source locations are exercised.
        only=sorted({0,1,*[a['scenes'][0]-1 for a in assets]})
        with mock.patch.object(visuals,'_generate',side_effect=generate),mock.patch.object(visuals,'ready_accounts',return_value=1):
            self.assertEqual(visuals.make_scenes(d,only,False,False),0)
        self.assertEqual(len(seen),len(only)*2)
        self.assertTrue(all(len(refs)<=4 for _,_,refs in seen))
        for i in only:
            self.assertTrue(continuity.current(d,i,'image'))
            self.assertTrue(continuity.current(d,i,'clip'))
        initial=continuity.references(d,0)[1];second=continuity.references(d,1)[1]
        self.assertTrue(set(initial)&set(second))
        # Change the Voss house: old results can no longer be silently reused, auto stops.
        assets[0]['description']+=' Changed roof.'
        continuity.save(d,{'assets':assets})
        self.assertFalse(continuity.status(d)['approved'])
        self.assertIn(1,continuity.status(d)['stale'])
        with mock.patch.object(auto,'step') as step:
            self.assertEqual(auto.run(d,'1080','offline'),0)
            step.assert_not_called()
        self.assertFalse(continuity.current(d,0,'clip'))
        self.assertTrue(continuity.current(d,assets[2]['scenes'][0]-1,'clip'))
