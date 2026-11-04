import copy
import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest import mock

import numpy as np

from storyvid import audio, check, contract
from storyvid.tts import SAMPLE_RATE

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.scenes.json').read_text())


def tone(path, seconds, freq):
    t = np.arange(int(SAMPLE_RATE * seconds)) / SAMPLE_RATE
    data = (np.sin(2 * np.pi * freq * t) * 12000).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(data.tobytes())


class AudioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        for name, secs, freq in [('can.wav', 0.3, 900), ('night.wav', 1.0, 200), ('bed.wav', 2.0, 300)]:
            tone(self.dir / name, secs, freq)
        self.sounds = [
            {'id': 'can_clack', 'label': 'Can clack', 'kind': 'sfx', 'file': 'can.wav', 'license': 'CC0',
             'source': 'https://example.org/1'},
            {'id': 'night_frogs', 'label': 'Night frogs', 'kind': 'ambience', 'file': 'night.wav', 'license': 'CC0',
             'source': 'https://example.org/2'},
            {'id': 'dark_bed', 'label': 'Dark bed', 'kind': 'music', 'file': 'bed.wav', 'license': 'CC-BY-4.0',
             'source': 'https://example.org/3', 'attribution': 'Dark bed by Someone (CC BY 4.0)'},
        ]
        self.write()
        patcher = mock.patch.object(audio, 'AUDIO', self.dir)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(audio.reload)
        audio.reload()

    def write(self):
        (self.dir / 'manifest.json').write_text(json.dumps({'format': 'storyvid.audio/1', 'sounds': self.sounds}))
        audio.reload()

    def script(self):
        s = copy.deepcopy(SAMPLE)
        s['music'] = {'id': 'dark_bed'}
        s['scenes'][0]['ambience'] = 'night_frogs'
        s['scenes'][1]['sfx'] = [{'id': 'can_clack', 'line': 1}]
        return s

    def test_audio_cues_follow_the_contract(self):
        self.assertEqual(contract.validate(self.script()), ([], []))
        bad = self.script()
        bad['scenes'][1]['sfx'] = [{'id': 'night_frogs', 'line': 9}]
        bad['music'] = {'id': 'nope'}
        errors, _ = contract.validate(bad)
        self.assertIn("$.music.id: 'nope' is not a music in assets/audio/manifest.json "
                      "(choose from schema/assets.catalog.json)", errors)
        self.assertTrue(any(e.startswith('$.scenes[1].sfx[0].id') for e in errors))
        self.assertIn('$.scenes[1].sfx[0].line: must be the index of a line in this scene (0-2)', errors)

    def test_manifest_is_checked(self):
        self.assertEqual(check.audio_problems(), [])
        self.sounds[2] = {**self.sounds[2], 'attribution': ''}
        self.sounds[1] = {**self.sounds[1], 'license': 'CC-BY-NC'}
        self.write()
        problems = check.audio_problems()
        self.assertIn('audio/dark_bed: CC-BY-4.0 needs an attribution line', problems)
        self.assertIn('audio/night_frogs: license must be one of CC0, CC-BY-4.0, YouTube Audio Library, Mixkit Free License', problems)

    def test_mix_adds_sound_and_ducks_music(self):
        script = self.script()
        voice = np.zeros(SAMPLE_RATE * 4, dtype=np.int16)
        voice[SAMPLE_RATE * 2:SAMPLE_RATE * 3] = 8000  # someone speaks in second 2-3
        spans = [{'start': i * 0.5, 'end': (i + 1) * 0.5,
                  'lines': [{'start': i * 0.5, 'end': i * 0.5 + 0.2}, {'start': i * 0.5 + 0.2, 'end': i * 0.5 + 0.4},
                            {'start': i * 0.5 + 0.4, 'end': (i + 1) * 0.5}]} for i in range(len(script['scenes']))]
        timeline = {'samples': voice, 'scenes': spans}
        out = audio.mix(script, timeline, self.dir / 'mix.wav')
        with wave.open(str(out)) as w:
            mixed = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
        self.assertEqual(len(mixed), len(voice))
        quiet = np.abs(mixed[int(SAMPLE_RATE * 1.4):int(SAMPLE_RATE * 1.9)]).mean()  # music alone
        self.assertGreater(quiet, 0)
        self.assertEqual(audio.attributions(script), ['Dark bed by Someone (CC BY 4.0)'])
        self.assertTrue(audio.has_sound(script))
        self.assertFalse(audio.has_sound(SAMPLE))


if __name__ == '__main__':
    unittest.main()


class AmbientTimelineTest(unittest.TestCase):
    def test_silent_genre_follows_the_clips_and_keeps_their_sound(self):
        from storyvid import cli, tts
        from storyvid.ffmpeg import ffmpeg_exe
        import subprocess
        script = {'scenes': [{'lines': [{'speaker': 'narrator', 'text': 'Ngày 1'}]},
                             {'lines': [{'speaker': 'narrator', 'text': 'Dựng cột'}]}]}
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            clip = d / 'a.mp4'
            subprocess.run([ffmpeg_exe(), '-v', 'error', '-f', 'lavfi', '-i', 'color=c=black:s=64x36:d=2',
                            '-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', '-shortest', str(clip)], check=True)
            timeline = tts.ambient_timeline(script, [(clip, None), (None, None)], d / 'work', still_seconds=3)
            self.assertAlmostEqual(timeline['duration'], 5, delta=0.2)
            self.assertEqual([c['text'] for c in timeline['cues']], ['Ngày 1', 'Dựng cột'])
            self.assertGreater(np.abs(timeline['samples'][:SAMPLE_RATE]).max(), 1000)  # the clip's tone is kept
            quiet = np.abs(timeline['samples'][-SAMPLE_RATE:]).max()
            self.assertTrue(0 < quiet < 2000)  # an image scene has only the quiet bed that runs through the video
            (d / 'meta.json').write_text(json.dumps({'genre': 'build'}))
            self.assertTrue(cli.is_silent(d))
            (d / 'meta.json').write_text(json.dumps({'genre': 'drama'}))
            self.assertFalse(cli.is_silent(d))
        place = lambda bg: {'bg_id': bg, 'lines': []}  # noqa: E731
        story = {'scenes': [place('river_day'), place('river_day'), place('river_night')]}
        self.assertEqual(cli.dissolves(story, False), [0.0, 0.0, cli.DISSOLVE])  # only where time or place changes
        self.assertEqual(cli.dissolves(story, True), [0.0, cli.DISSOLVE, cli.DISSOLVE])
