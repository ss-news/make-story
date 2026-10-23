import copy
import io
import json
import unittest
from pathlib import Path
from PIL import Image
from storyvid.character import Character
from storyvid.script import _normalize

ROOT = Path(__file__).resolve().parents[1]
HOST = json.loads((ROOT / 'channel.json').read_text())['host']
SCENE = {'bg_id': 'village_path_day', 'bg_prompt': '', 'camera': 'static',
         'actors': [{'id': 'host', 'position': 'center', 'pose': 'talk', 'expression': 'neutral', 'action': 'none'}],
         'lines': [{'speaker': 'narrator', 'text': 'Một câu chuyện.'}]}

class CharactersTest(unittest.TestCase):
    def test_video_selection_survives_normalization(self):
        source = {'title': 'Test', 'character': {'preset': 'elder_woman', 'outfit': 'indigo', 'accessory': 'bag'}, 'scenes': [SCENE]}
        self.assertEqual(_normalize(source).get('character'), source['character'])

    def test_invalid_selection_is_rejected(self):
        with self.assertRaises(ValueError):
            _normalize({'character': {'preset': '../../bad'}, 'scenes': [SCENE]})

    def test_script_without_character_does_not_gain_an_override(self):
        self.assertNotIn('character', _normalize({'scenes': [SCENE]}))

    def test_variants_are_independent(self):
        from storyvid.character_catalog import resolve_character
        before = copy.deepcopy(HOST)
        a = resolve_character(HOST, {'preset': 'girl', 'outfit': 'earth', 'accessory': 'none'})
        b = resolve_character(HOST, {'preset': 'elder_man', 'outfit': 'indigo', 'accessory': 'bag'})
        self.assertNotEqual(a['preset'], b['preset'])
        self.assertEqual(HOST, before)
        self.assertNotEqual(Character(a, 300).sprite('idle','neutral',0,False,False).tobytes(), Character(b,300).sprite('idle','neutral',0,False,False).tobytes())

    def test_all_presets_and_poses_render_transparently(self):
        from storyvid.character_catalog import PRESETS, resolve_character
        from storyvid.script import POSES, EXPRESSIONS
        for preset in PRESETS:
            character = Character(resolve_character(HOST, {'preset': preset}), 240)
            for i, pose in enumerate(POSES):
                sprite = character.sprite(pose, EXPRESSIONS[i % len(EXPRESSIONS)], i % 3, False, False)
                self.assertEqual(sprite.mode, 'RGBA')
                self.assertEqual(sprite.getpixel((0,0))[3], 0)
                self.assertIsNotNone(sprite.getbbox())
            closed = character.sprite('talk','neutral',0,False,False)
            blink = character.sprite('talk','neutral',2,True,False)
            self.assertNotEqual(closed.tobytes(), blink.tobytes())

    def test_parts_have_editable_svg_and_joint_metadata(self):
        from storyvid.character_catalog import PRESETS
        extra = ROOT / 'assets' / 'bac-bo-stick' / 'extra'
        extra_ids = {c['id'] for c in json.loads((extra / 'manifest.json').read_text())['characters']}
        for preset in PRESETS:
            pack_root = extra if preset in extra_ids else ROOT / 'assets' / 'bac-bo-stick'
            folder = pack_root / 'characters' / preset
            rig = json.loads((folder / 'rig.json').read_text())
            for part in ('head', 'hair_front', 'torso', 'upper_arm', 'forearm', 'hand', 'thigh', 'shin', 'foot'):
                self.assertIn(part, rig['parts'])
                self.assertIn('pivot', rig['parts'][part])
                self.assertIn('<svg', (folder / rig['parts'][part]['file']).read_text())

    def test_preview_api_and_options(self):
        from storyvid.web.__main__ import app
        client = app.test_client()
        options = client.get('/api/options').get_json()
        pack_root = ROOT / 'assets' / 'bac-bo-stick'
        expected = {p.parent.name for p in (pack_root / 'characters').glob('*/rig.json')}
        extra = json.loads((pack_root / 'extra' / 'manifest.json').read_text())
        expected.update(c['id'] for c in extra['characters'])
        characters = options.get('characters', [])
        self.assertEqual(len(characters), len(expected))
        self.assertEqual({c['id'] for c in characters}, expected)
        response = client.post('/api/character-preview', json={'host': HOST, 'character': {'preset':'girl', 'outfit':'earth', 'accessory':'bag'}})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Image.open(io.BytesIO(response.data)).format, 'PNG')
        response = client.post('/api/character-preview', json={'character': {'preset': 'missing'}})
        self.assertEqual(response.status_code, 400)


class PersistenceTest(unittest.TestCase):
    def test_project_save_and_reload_keeps_variant(self):
        import tempfile
        from unittest.mock import patch
        from storyvid.web import __main__ as web
        with tempfile.TemporaryDirectory() as tmp, patch.object(web, 'OUTPUT', Path(tmp)):
            c = web.app.test_client()
            created = c.post('/api/projects', json={'name':'Character QA'}).get_json()
            pid = created['id']
            choice = {'preset':'middle_woman','outfit':'moss','accessory':'scarf'}
            result = c.put('/api/projects/'+pid,json={'script':{'title':'QA','character':choice,'scenes':[SCENE]}})
            self.assertEqual(result.status_code,200)
            self.assertEqual(c.get('/api/projects/'+pid).get_json()['script']['character'],choice)
            result = c.put('/api/projects/'+pid,json={'script':{'character':{'outfit':'bad'},'scenes':[SCENE]}})
            self.assertEqual(result.status_code,400)
            self.assertEqual(c.get('/api/projects/'+pid).get_json()['script']['character'],choice)

    def test_regenerating_script_keeps_video_character(self):
        import tempfile
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'story.txt').write_text('Bà kể chuyện ở làng. Trời đã tối.')
            choice={'preset':'elder_woman','outfit':'earth','accessory':'bag'}
            (folder/'scenes.json').write_text(json.dumps({'character':choice,'scenes':[SCENE]}))
            subprocess.run([sys.executable,'-m','storyvid.cli',str(folder/'story.txt'),'--provider','offline','--script-only','--out',tmp],cwd=ROOT,check=True,capture_output=True)
            self.assertEqual(json.loads((folder/'scenes.json').read_text())['character'],choice)

    def test_extreme_arm_poses_are_not_clipped(self):
        from storyvid.character_catalog import resolve_character
        from storyvid.script import POSES
        ch=Character(resolve_character(HOST,{'preset':'young_man','accessory':'flashlight'}),640)
        for pose in POSES:
            bounds=ch.sprite(pose,'neutral',0,False,False).getbbox()
            self.assertGreater(bounds[0],0,pose)
            self.assertLess(bounds[2],ch.width,pose)

    def test_export_face_parts_are_editable(self):
        ch=Character(HOST,220)
        for part in ('eyes_neutral','eyes_closed','brows_angry','mouth_open'):
            self.assertIn(part,ch.rig['parts'])

class RenderTest(unittest.TestCase):
    def test_fractional_last_frame_has_no_audio_warning(self):
        import tempfile
        import warnings
        import wave
        import numpy as np
        from storyvid.render import Renderer
        from storyvid.tts import SAMPLE_RATE
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)
            bg=folder/'bg.png'; Image.new('RGB',(400,240),'#758477').save(bg)
            audio=folder/'audio.wav'
            samples=np.zeros(SAMPLE_RATE//5,dtype=np.int16)
            with wave.open(str(audio),'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(samples.tobytes())
            duration=.20000000000000004
            timeline={'audio':audio,'samples':samples,'duration':duration,'scenes':[{'start':0,'end':duration}],'cues':[]}
            channel=json.loads((ROOT/'channel.json').read_text())
            with warnings.catch_warnings():
                warnings.simplefilter('error',RuntimeWarning)
                Renderer(channel,(320,180),10).render({'scenes':[SCENE],'character':{'preset':'girl'}},timeline,{'village_path_day':bg},folder/'test.mp4')
            self.assertGreater((folder/'test.mp4').stat().st_size,0)

class ScriptIdentityTest(unittest.TestCase):
    def test_selected_narrator_replaces_channel_boy_in_prompt(self):
        from storyvid.script import build_prompt
        channel=json.loads((ROOT/'channel.json').read_text())
        system,_=build_prompt('Chuyện làng',channel,'vi',2,{'preset':'elder_woman'})
        self.assertIn('Bà Tư',system)
        self.assertNotIn('village boy',system)

if __name__ == '__main__':
    unittest.main()
