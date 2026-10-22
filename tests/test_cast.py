import json
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from PIL import Image

from storyvid.script import _normalize
from storyvid.tts import SAMPLE_RATE, cast_voices

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = json.loads((ROOT / 'channel.json').read_text())
CAST = [
    {'id': 'tu', 'name': 'Tư', 'preset': 'boy', 'kind': 'human'},
    {'id': 'ba', 'name': 'Bà', 'preset': 'elder_woman', 'kind': 'human'},
    {'id': 'ma_da', 'name': 'Ma da', 'preset': 'middle_woman', 'kind': 'ghost'},
]
SCENE = {'bg_id': 'river', 'bg_prompt': 'river', 'camera': 'static',
         'actors': [{'id': 'ba', 'position': 'left', 'pose': 'point', 'expression': 'angry', 'action': 'enter'},
                    {'id': 'ma_da', 'position': 'right', 'pose': 'reach', 'expression': 'sad', 'action': 'exit'}],
         'lines': [{'speaker': 'ba', 'text': 'Buông ra!'}, {'speaker': 'narrator', 'text': 'Nước lặng.'}]}


class CastScriptTest(unittest.TestCase):
    def test_unknown_actors_and_speakers_are_dropped_or_narrated(self):
        script = _normalize({'cast': CAST, 'scenes': [{**SCENE,
            'actors': SCENE['actors'] + [{'id': 'stranger'}, {'id': 'ba'}],
            'lines': SCENE['lines'] + [{'speaker': 'stranger', 'text': 'Ai đó?'}, {'speaker': 'ba', 'text': ' '}]}]})
        scene = script['scenes'][0]
        self.assertEqual([a['id'] for a in scene['actors']], ['ba', 'ma_da'])
        self.assertEqual([ln['speaker'] for ln in scene['lines']], ['ba', 'narrator', 'narrator'])

    def test_vietnamese_ids_are_slugged_and_unique(self):
        script = _normalize({'cast': [{'id': 'Bà Tư', 'preset': 'nope'}, {'id': 'ba_tu'}, {'id': 'host'}],
                             'scenes': [SCENE]})
        self.assertEqual([c['id'] for c in script['cast']], ['ba_tu'])
        self.assertEqual(script['cast'][0]['preset'], 'young_man')


class CastVoiceTest(unittest.TestCase):
    def test_every_speaker_gets_a_distinct_voice(self):
        voices = cast_voices({'cast': CAST}, 'vi-VN-NamMinhNeural', 'vi')
        self.assertEqual(set(voices), {'narrator', 'tu', 'ba', 'ma_da'})
        self.assertEqual(len(set(voices.values())), 4)
        self.assertEqual(voices['ba'][0], 'vi-VN-HoaiMyNeural')
        self.assertTrue(voices['tu'][2].startswith('+'))  # child: higher pitch

    def test_unknown_language_falls_back_to_narrator_voice(self):
        voices = cast_voices({'cast': CAST}, 'xx-Voice', 'xx')
        self.assertTrue(all(v[0] == 'xx-Voice' for v in voices.values()))


class CastRenderTest(unittest.TestCase):
    def test_multi_actor_scene_renders(self):
        from storyvid.render import Renderer
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bg = folder / 'bg.png'
            Image.new('RGB', (400, 240), '#556677').save(bg)
            samples = (np.sin(np.arange(SAMPLE_RATE) / 8) * 8000).astype(np.int16)
            audio = folder / 'a.wav'
            with wave.open(str(audio), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(samples.tobytes())
            timeline = {'audio': audio, 'samples': samples, 'duration': 1.0,
                        'scenes': [{'start': 0, 'end': 1.0, 'lines': [{'start': 0, 'end': .5, 'speaker': 'ba'},
                                                                     {'start': .5, 'end': 1.0, 'speaker': 'narrator'}]}],
                        'cues': [{'start': 0, 'end': .5, 'text': 'Buông ra!', 'speaker': 'Bà'}]}
            props = [{'id': 'buffalo', 'position': 'far_right'}, {'id': 'oil_lamp', 'position': 'far_left'}]
            script = _normalize({'cast': CAST, 'scenes': [{**SCENE, 'props': props}]})
            self.assertEqual(script['scenes'][0]['props'], props)
            Renderer(CHANNEL, (320, 180), 10).render(script, timeline, {'river': bg}, folder / 'v.mp4')
            self.assertGreater((folder / 'v.mp4').stat().st_size, 0)

    def test_short_renders_vertically(self):
        from storyvid.render import ShortRenderer
        from storyvid.ffmpeg import ffmpeg_exe
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            bg = folder / 'bg.png'
            Image.new('RGB', (400, 240), '#556677').save(bg)
            samples = (np.sin(np.arange(SAMPLE_RATE) / 8) * 8000).astype(np.int16)
            audio = folder / 'a.wav'
            with wave.open(str(audio), 'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(samples.tobytes())
            timeline = {'audio': audio, 'samples': samples, 'duration': 1.0,
                        'scenes': [{'start': 0, 'end': 1.0, 'lines': [{'start': 0, 'end': 1.0, 'speaker': 'ba'}]}],
                        'cues': [{'start': 0, 'end': 1.0, 'text': 'Buông ra!', 'speaker': 'Bà'}]}
            script = _normalize({'cast': CAST, 'scenes': [SCENE]})
            r = ShortRenderer(CHANNEL, 180, 10, 'Tiếng gọi từ sông', 'vi')
            self.assertEqual(r.out_size, (180, 320))
            r.render(script, timeline, {'river': bg}, folder / 's.mp4')
            probe = subprocess.run([ffmpeg_exe(), '-i', str(folder / 's.mp4')], capture_output=True, text=True).stderr
            self.assertIn('180x320', probe)

    def test_short_scenes_default_to_the_opening(self):
        from storyvid.cli import short_scenes
        line = {'speaker': 'narrator', 'text': ' '.join(['word'] * 60)}  # about 23 s each
        script = {'scenes': [{'lines': [line]} for _ in range(5)]}
        self.assertEqual(short_scenes(script), [0, 1])
        self.assertEqual(short_scenes({**script, 'short': {'scenes': [1, 4]}}), [1, 4])

    def test_thumbnail_api(self):
        from storyvid.web import __main__ as web
        c = web.app.test_client()
        r = c.get('/api/character-thumb?preset=girl&outfit=moss&accessory=bag&kind=ghost')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Image.open(__import__('io').BytesIO(r.data)).mode, 'RGBA')
        self.assertEqual(c.get('/api/character-thumb?preset=../../x').status_code, 400)


if __name__ == '__main__':
    unittest.main()
