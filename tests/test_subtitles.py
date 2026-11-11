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

    def test_cues_carry_word_starts_for_karaoke(self):
        cues = tts._cues(words('No legs. No footsteps.'), 2.0)
        self.assertEqual(cues[0]['words'], [2.0, 2.5])
        self.assertEqual(cues[1]['words'], [3.0, 3.5])
        joined = tts._cues([(0.0, 0.4, 'twenty one'), (0.5, 0.9, 'days.')], 0)  # one token, two printed words
        self.assertEqual(len(joined[0]['words']), len(joined[0]['text'].split()))

    def test_karaoke_lights_spoken_words_only(self):
        from storyvid import render
        r = render.Renderer({'channel_name': 'Test'}, (640, 360), 24)
        cue = {'start': 0, 'end': 2, 'text': 'one two three', 'speaker': 'Tung', 'words': [0.0, 0.5, 1.0]}

        same = lambda a, b: a.tobytes() == b.tobytes()  # noqa: E731
        full = r._subtitle('one two three', 'Tung', None)
        self.assertTrue(same(r._cue_subtitle(cue, 1.5), full))          # every word spoken: fully lit
        self.assertTrue(same(r._cue_subtitle(cue, 0.2), r._subtitle('one two three', 'Tung', 1)))
        self.assertFalse(same(r._cue_subtitle(cue, 0.2), full))         # "two three" still waiting
        self.assertFalse(same(r._cue_subtitle(cue, 0.2), r._cue_subtitle(cue, 0.7)))
        self.assertTrue(same(r._subtitle('one two three', 'Tung', 0), r._cue_subtitle(cue, -1)))
        # the name keeps its colour whatever is lit; captions without timings are shown fully lit
        self.assertIn(render.SUB_SPEAKER + (255,), list(r._subtitle('one', 'Tung', 0).getdata()))
        self.assertTrue(same(r._cue_subtitle({'text': 'Day 1', 'speaker': ''}, 0), r._subtitle('Day 1', '', None)))

    def test_no_channel_badge_unless_asked(self):
        from storyvid import render
        img = Image.new('RGBA', (400, 200), (0, 0, 0, 0))
        render._badge(img, {'channel_name': 'Chamlore', 'tagline': 'Stories'}, 10, 10, 60)
        self.assertIsNone(img.getbbox())
        render._badge(img, {'channel_name': 'Chamlore', 'tagline': 'Stories', 'show_logo': True}, 10, 10, 60)
        self.assertIsNotNone(img.getbbox())

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


class GhostAndFocusTests(unittest.TestCase):
    def test_ghost_fade_follows_the_drawn_figure(self):
        from storyvid.render import Renderer
        r = Renderer({'host': {}, 'channel_name': 'C'}, (200, 100), 10)
        r._ghost_cache = {}
        low = Image.new('RGBA', (40, 100), (0, 0, 0, 0))
        low.paste((0, 0, 0, 255), (10, 60, 30, 100))  # a short figure in the lower part of its canvas
        top_row = r._ghostly('child', low, 1).getpixel((20, 60))
        self.assertGreater(top_row[3], 200)  # its head is as solid as a tall ghost's head

    def test_focus_aims_at_drawn_actors_then_props(self):
        from storyvid.render import Renderer
        r = Renderer({'host': {}, 'channel_name': 'C'}, (200, 100), 10)
        self.assertEqual(r._focus([(80, 60, 120, 100)], [(0, 0, 10, 10)]), (100, 76.0))
        self.assertEqual(r._focus([], [(80, 80, 120, 100)]), (100, 90.0))
        self.assertEqual(r._focus([], []), (100, 50))


if __name__ == '__main__':
    unittest.main()
