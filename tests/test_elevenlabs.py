import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from storyvid import elevenlabs, tts

VOICES = [
    {'id': 'm_mid', 'name': 'Narr', 'gender': 'male', 'age': 'middle_aged'},
    {'id': 'm_old', 'name': 'Grandpa', 'gender': 'male', 'age': 'old'},
    {'id': 'f_young', 'name': 'Girl', 'gender': 'female', 'age': 'young'},
    {'id': 'f_old', 'name': 'Granny', 'gender': 'female', 'age': 'old'},
    {'id': 'f_mid', 'name': 'Woman', 'gender': 'female', 'age': 'middle_aged'},
]
CAST = [
    {'id': 'ba', 'name': 'Bà', 'preset': 'elder_woman', 'kind': 'human'},
    {'id': 'ma_da', 'name': 'Ma da', 'preset': 'middle_woman', 'kind': 'ghost'},
    {'id': 'chi', 'name': 'Chị', 'preset': 'young_woman', 'kind': 'human'},
]
ALIGNMENT = {'characters': list('Hi, you.'),
             'character_start_times_seconds': [0, .1, .2, .3, .4, .5, .6, .7],
             'character_end_times_seconds': [.1, .2, .3, .4, .5, .6, .7, .8]}


class ElevenLabsTest(unittest.TestCase):
    def test_words_from_character_alignment(self):
        self.assertEqual(elevenlabs._words(ALIGNMENT), [(0, .3, 'Hi,'), (.4, .8, 'you.')])

    def test_speed_is_clamped(self):
        self.assertEqual(elevenlabs.speed_from_rate('+0%'), 1.0)
        self.assertEqual(elevenlabs.speed_from_rate('-16%'), 0.84)
        self.assertEqual(elevenlabs.speed_from_rate('-40%'), 0.7)

    def test_cast_gets_distinct_voices_by_gender_and_age(self):
        with mock.patch.object(elevenlabs, 'list_voices', return_value=VOICES), \
                mock.patch.dict(os.environ, {'ELEVENLABS_NARRATOR_VOICE': ''}):
            voices = tts.cast_voices_elevenlabs({'cast': CAST})
        self.assertEqual(voices['narrator'][0], 'm_mid')
        self.assertEqual(voices['ba'][0], 'f_old')
        self.assertEqual(voices['ma_da'][0], 'f_mid')
        self.assertEqual(voices['chi'][0], 'f_young')
        self.assertEqual(voices['ma_da'][1], '-16%')

    def test_narrator_by_name(self):
        with mock.patch.dict(os.environ, {'ELEVENLABS_NARRATOR_VOICE': 'Grandpa'}):
            self.assertEqual(elevenlabs.resolve_narrator(VOICES, set()), 'm_old')

    def test_vietnamese_uses_a_model_that_supports_it(self):
        with mock.patch.dict(os.environ, {'ELEVENLABS_MODEL': ''}):
            self.assertEqual(elevenlabs.model_for('en'), 'eleven_multilingual_v2')
            self.assertEqual(elevenlabs.model_for('vi'), 'eleven_flash_v2_5')

    def test_synthesis_is_cached(self):
        response = {'audio_base64': base64.b64encode(b'mp3bytes').decode(), 'alignment': ALIGNMENT}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(elevenlabs, 'CACHE_DIR', Path(tmp) / 'cache'), \
                mock.patch.object(elevenlabs, '_request', return_value=response) as req:
            out = Path(tmp) / 'a.mp3'
            first = elevenlabs.synthesize('Hi, you.', 'v1', out, 1.0, 'm')
            second = elevenlabs.synthesize('Hi, you.', 'v1', out, 1.0, 'm')
            self.assertEqual(req.call_count, 1)
            self.assertEqual(first, second)
            self.assertEqual(out.read_bytes(), b'mp3bytes')
            body = req.call_args.args[1]
            self.assertEqual((body['model_id'], body['voice_settings']['speed']), ('m', 1.0))

    def test_unknown_provider_is_rejected(self):
        with mock.patch.dict(os.environ, {'TTS_PROVIDER': 'azure'}):
            with self.assertRaises(RuntimeError):
                tts.tts_provider()
        with mock.patch.dict(os.environ, {'TTS_PROVIDER': ''}):
            self.assertEqual(tts.tts_provider(), 'edge')


if __name__ == '__main__':
    unittest.main()
