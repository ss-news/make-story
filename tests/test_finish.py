import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from storyvid import finish, visuals
from storyvid.ffmpeg import ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.scenes.json').read_text())


def make_project(d: Path, volume: float, width=1920, height=1080, seconds=3):
    subprocess.run([ffmpeg_exe(), '-v', 'error', '-y', '-f', 'lavfi', '-i', f'color=c=blue:s={width}x{height}:d={seconds}',
                    '-f', 'lavfi', '-i', f'sine=frequency=300:duration={seconds}', '-af', f'volume={volume}',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-shortest', str(d / 'video.mp4')], check=True)
    (d / 'scenes.json').write_text(json.dumps(SAMPLE))
    (d / 'meta.json').write_text(json.dumps({'minutes': 0.01, 'approved_script': visuals.script_digest(SAMPLE)}))
    (d / 'video.srt').write_text('1\n00:00:00,000 --> 00:00:02,900\nXin chào\n')
    (d / 'render.json').write_text(json.dumps({'video': {
        'scenes_digest': visuals.script_digest(SAMPLE), 'visuals': False, 'fallback': False, 'res': '1080',
        'duration': seconds, 'scenes': [{'index': 0, 'start': 0, 'end': seconds}]}}))


class FinishTest(unittest.TestCase):
    def test_checks_pass_and_catch_quiet_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            make_project(d, volume=0.05)
            result = finish.check(d)
            by = {c['id']: c for c in result['checks']}
            for cid in ('approved', 'no_fallback', 'resolution', 'duration', 'subtitles'):
                self.assertTrue(by[cid]['ok'], by[cid])
            self.assertFalse(by['loudness']['ok'])
            finish.loudnorm(d)
            self.assertTrue({c['id']: c for c in finish.check(d)['checks']}['loudness']['ok'])

    def test_edited_script_or_low_resolution_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            make_project(d, volume=0.3, width=1280, height=720)
            (d / 'scenes.json').write_text(json.dumps({**SAMPLE, 'title': 'changed'}))
            by = {c['id']: c for c in finish.check(d)['checks']}
            self.assertFalse(by['approved']['ok'])
            self.assertFalse(by['resolution']['ok'])

    def test_frames_make_numbered_sheets(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            make_project(d, volume=0.3, width=640, height=360)
            sheets = finish.frames(d)
            self.assertEqual(len(sheets), 1)
            self.assertTrue((d / 'publish' / 'frames' / 'scene_000.jpg').exists())

    def test_thumbnail_text_is_youtube_size(self):
        img = finish.thumbnail_text(Image.new('RGB', (2048, 1152), 'teal'), 'Vì sao ta nghiện?')
        self.assertEqual(img.size, (1280, 720))

    def test_srt_and_clock(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'a.srt'
            p.write_text('1\n00:01:02,500 --> 00:01:04,000\nMột câu\n\n2\n00:01:05,000 --> 00:01:06,000\nHai\n')
            self.assertEqual(finish.srt_cues(p)[1], (65.0, 66.0, 'Hai'))
        self.assertEqual(finish.clock(616.5), '10:16')
        self.assertEqual(finish.clock(3725), '1:02:05')


if __name__ == '__main__':
    unittest.main()
