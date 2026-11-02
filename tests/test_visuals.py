import copy
import json
import tempfile
import unittest
from pathlib import Path

from storyvid import contract, render_clips, vieneu, visuals

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.scenes.json').read_text())
CHANNEL = json.loads((ROOT / 'channel.json').read_text())


class VisualsContractTest(unittest.TestCase):
    def setUp(self):
        self.plan = visuals.write_prompts(SAMPLE, CHANNEL, '16:9', 'offline')

    def test_offline_plan_follows_the_contract(self):
        self.assertEqual(contract.validate_visuals(self.plan, SAMPLE), [])
        self.assertEqual(len(self.plan['scenes']), len(SAMPLE['scenes']))
        self.assertEqual([c['id'] for c in self.plan['cast']], visuals.used_cast(SAMPLE))

    def test_rejects_unknown_fields_wrong_counts_and_paths(self):
        bad = copy.deepcopy(self.plan)
        bad['scenes'][0]['extra'] = 1
        bad['scenes'].pop()
        bad['cast'][0]['id'] = 'nobody'
        bad['scenes'][1]['image'] = '../escape.png'
        bad['ratio'] = '4:3'
        errors = '\n'.join(contract.validate_visuals(bad, SAMPLE))
        for needle in ('unknown field(s) extra', 'scenes.json has', "'nobody' is not in the cast",
                       'inside the project folder', "'4:3' is not one of"):
            self.assertIn(needle, errors)

    def test_generated_files_must_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            plan = copy.deepcopy(self.plan)
            plan['scenes'][0]['clip'] = 'muse/scene_00.mp4'
            self.assertIn('does not exist', '\n'.join(contract.validate_visuals(plan, SAMPLE, Path(tmp))))
            (Path(tmp) / 'muse').mkdir()
            (Path(tmp) / 'muse' / 'scene_00.mp4').write_bytes(b'x')
            self.assertEqual(contract.validate_visuals(plan, SAMPLE, Path(tmp)), [])

    def test_rewriting_prompts_keeps_files_whose_prompt_did_not_change(self):
        old = copy.deepcopy(self.plan)
        old['scenes'][0].update(image='muse/scene_00.png', clip='muse/scene_00.mp4')
        old['scenes'][1].update(image='muse/scene_01.png', clip='muse/scene_01.mp4')
        new = copy.deepcopy(self.plan)
        new['scenes'][1]['video_prompt'] = 'something else'
        merged = visuals.merge_files(new, old)
        self.assertEqual(merged['scenes'][0]['clip'], 'muse/scene_00.mp4')
        self.assertEqual(merged['scenes'][1]['image'], 'muse/scene_01.png')
        self.assertEqual(merged['scenes'][1]['clip'], '')

    def test_scene_prompt_describes_only_the_actors_on_stage(self):
        names = visuals.cast_names(SAMPLE, CHANNEL)
        for i, scene in enumerate(SAMPLE['scenes']):
            prompt = visuals.scene_image_prompt(self.plan, i, SAMPLE, names)
            on_stage = {a['id'] for a in scene['actors']}
            for c in self.plan['cast']:
                self.assertEqual(c['look'] in prompt, c['id'] in on_stage, (i, c['id']))

    def test_schema_matches_the_validator_keys(self):
        schema = contract.visuals_schema()
        self.assertEqual(set(schema['required']), contract.VISUALS_KEYS)
        self.assertEqual(json.loads((ROOT / 'schema' / 'visuals.v1.schema.json').read_text()), schema)


class TimingTest(unittest.TestCase):
    def test_clip_slows_down_only_up_to_the_limit(self):
        self.assertEqual(render_clips.playback_speed(6, 10), 1.0)
        self.assertAlmostEqual(render_clips.playback_speed(12, 10), 1.2)
        self.assertEqual(render_clips.playback_speed(40, 10), render_clips.MAX_SLOW)
        self.assertEqual(render_clips.playback_speed(5, 0), 1.0)

    def test_vieneu_word_timings_cover_the_line(self):
        words = vieneu.word_timings('Xin chào các bạn, hôm nay', 3.0)
        self.assertEqual([w[2] for w in words], ['Xin', 'chào', 'các', 'bạn,', 'hôm', 'nay'])
        self.assertAlmostEqual(words[0][0], 0.0)
        self.assertAlmostEqual(words[-1][1], 3.0)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(words, words[1:])))

    def test_vieneu_gives_each_character_a_different_voice(self):
        voices = vieneu.cast_voices(SAMPLE)
        self.assertEqual(len(set(voices.values())), len(voices))


if __name__ == '__main__':
    unittest.main()
