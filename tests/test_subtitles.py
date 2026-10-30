import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

from storyvid import tts


def words(text):
    return [(i * 0.5, i * 0.5 + 0.4, w) for i, w in enumerate(text.split())]


class SubtitleTests(unittest.TestCase):
    def test_cues_do_not_end_on_a_weak_word(self):
        cues = tts._cues(words('a small shape crawled right up behind Mr. Chan and then it was gone'), 0)
        self.assertEqual(cues[0]['text'], 'a small shape crawled right up behind')
        self.assertTrue(cues[1]['text'].startswith('Mr. Chan'))
        for c in cues:
            self.assertNotIn(c['text'].split()[-1].lower(), tts.WEAK_END)

    def test_cues_still_break_at_punctuation(self):
        cues = tts._cues(words('No legs. No footsteps.'), 2.0)
        self.assertEqual([c['text'] for c in cues], ['No legs.', 'No footsteps.'])
        self.assertEqual(cues[1]['start'], 3.0)

    def test_srt_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = tts.write_srt([{'start': 0, 'end': 1.25, 'text': 'Run!', 'speaker': 'Tung'},
                                  {'start': 3661.5, 'end': 3662, 'text': 'She did not come.', 'speaker': ''}],
                                 Path(tmp) / 'v.srt')
            self.assertEqual(path.read_text(encoding='utf-8'),
                             '1\n00:00:00,000 --> 00:00:01,250\nTung: Run!\n\n'
                             '2\n01:01:01,500 --> 01:01:02,000\nShe did not come.\n')


class EdgeRetryTests(unittest.TestCase):
    def test_a_stalled_request_is_retried_and_the_result_cached(self):
        calls = []

        def fake_request(text, voice, mp3_path, rate, pitch):
            calls.append(mp3_path)
            if len(calls) == 1:
                raise ConnectionError('dropped')
            Path(mp3_path).write_bytes(b'mp3')
            return [(0.0, 0.3, 'Hello')]

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(tts, 'EDGE_CACHE', Path(tmp) / 'cache'), \
                mock.patch.object(tts, '_edge_request', fake_request), \
                mock.patch.object(tts.time, 'sleep'):
            out = Path(tmp) / 'line.mp3'
            self.assertEqual(tts._synthesize('Hello', 'v', out), [(0.0, 0.3, 'Hello')])
            self.assertEqual(out.read_bytes(), b'mp3')
            self.assertEqual(len(calls), 2)
            tts._synthesize('Hello', 'v', out)  # second time: from the cache, no request
            self.assertEqual(len(calls), 2)

    def test_gives_up_after_the_last_try(self):
        def always_fails(*args):
            raise ConnectionError('dropped')

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(tts, 'EDGE_CACHE', Path(tmp)), \
                mock.patch.object(tts, '_edge_request', always_fails), \
                mock.patch.object(tts.time, 'sleep'):
            with self.assertRaises(RuntimeError):
                tts._synthesize('Hello', 'v', Path(tmp) / 'line.mp3')


class ZoomTests(unittest.TestCase):
    def test_zoom_in_magnifies_the_stage_around_the_focus(self):
        from storyvid.render import Renderer
        r = Renderer({'host': {}, 'channel_name': 'C'}, (200, 100), 10)
        frame = Image.new('RGB', (200, 100), 'black')
        frame.paste((255, 255, 255), (150, 40, 170, 60))  # a white square on the right
        still = r._zoom(frame, 'static', 0.5, (160, 50))
        self.assertIs(still, frame)
        close = r._zoom(frame, 'zoom_in', 1.0, (160, 50))
        white = sum(1 for px in close.getdata() if px == (255, 255, 255))
        self.assertGreater(white, 400 * 1.2 ** 2)  # the square grew with the camera


if __name__ == '__main__':
    unittest.main()
