import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


class FlowTest(unittest.TestCase):
    """Style choice, the human review gate and Muse as a script writer."""

    def test_style_presets_resolve(self):
        from storyvid import styles
        stick = styles.resolve({'preset': 'stick'})
        self.assertTrue(stick['refs'] and all(p.is_file() for p in stick['refs']))
        self.assertEqual(styles.resolve({'preset': 'custom', 'text': 'watercolor'})['text'], 'watercolor')
        self.assertEqual(styles.resolve({'preset': 'custom', 'text': ' '}), {})
        self.assertEqual(styles.resolve({'preset': 'nope'}), {})

    def test_looks_are_written_from_the_source_story(self):
        long = dict(SAMPLE, scenes=SAMPLE['scenes'] * 3)  # more than one prompt batch
        cid = visuals.used_cast(long)[0]
        payloads = []

        def ask(_provider, _system, user):
            payloads.append(json.loads(user))
            return {'cast': [{'id': cid, 'look': 'a toddler with porcelain-white skin'}], 'scenes': []}

        with mock.patch.object(visuals, '_ask', side_effect=ask):
            plan = visuals.write_prompts(long, CHANNEL, '16:9', 'muse', 'my style', source='Câu chuyện gốc.')
        self.assertGreater(len(payloads), 1)
        self.assertEqual(payloads[0]['source_story'], 'Câu chuyện gốc.')
        self.assertTrue(all('source_story' not in p for p in payloads[1:]))
        self.assertEqual(next(c['look'] for c in plan['cast'] if c['id'] == cid), 'a toddler with porcelain-white skin')

    def test_a_fixed_style_is_kept(self):
        plan = visuals.write_prompts(SAMPLE, CHANNEL, '9:16', 'offline', 'my style')
        self.assertEqual(plan['style'], 'my style')

    def test_style_refs_must_be_project_files(self):
        plan = visuals.write_prompts(SAMPLE, CHANNEL, '9:16', 'offline')
        with tempfile.TemporaryDirectory() as tmp:
            plan['style_refs'] = ['muse/style/ref_0.png']
            self.assertIn('does not exist', '\n'.join(contract.validate_visuals(plan, SAMPLE, Path(tmp))))
            (Path(tmp) / 'muse' / 'style').mkdir(parents=True)
            (Path(tmp) / 'muse' / 'style' / 'ref_0.png').write_bytes(b'x')
            self.assertEqual(contract.validate_visuals(plan, SAMPLE, Path(tmp)), [])

    def test_approval_is_lost_when_the_script_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            script = copy.deepcopy(SAMPLE)
            (d / 'scenes.json').write_text(json.dumps(script))
            self.assertFalse(visuals.is_approved(d))
            (d / 'meta.json').write_text(json.dumps({'approved_script': visuals.script_digest(script)}))
            self.assertTrue(visuals.is_approved(d))
            script['title'] = 'changed'
            (d / 'scenes.json').write_text(json.dumps(script))
            self.assertFalse(visuals.is_approved(d))

    def test_muse_writes_the_script_through_museflow(self):
        from unittest import mock
        from storyvid import script as script_mod
        treatment = {'title': 'T', 'logline': 'L', 'cast': [], 'beats': []}
        shots = {'scenes': [{'slug': 'EXT. RIVER - NIGHT', 'bg_id': 'river_night', 'bg_prompt': 'river',
                             'beat': 'cold_open', 'shots': [{'size': 'CU', 'movement': 'push_in', 'actors': [],
                                                             'lines': [{'speaker': 'narrator', 'text': 'Hi.'}]}]}]}
        replies = [{'ok': True, 'text': 'Here it is:\n```json\n' + json.dumps(r) + '\n```'} for r in (treatment, shots)]
        with mock.patch.object(visuals, 'muse', side_effect=replies) as call:
            out = script_mod.write_script('story', CHANNEL, 'en', 1, 'muse')
        self.assertEqual(call.call_args[0][0], '/api/chat')
        self.assertEqual(contract.validate(out)[0], [])


class ContinuityTest(unittest.TestCase):
    def test_auto_links_scenes_in_the_same_place(self):
        script = {'scenes': [{'bg_id': 'river_night'}, {'bg_id': 'river_night'}, {'bg_id': 'pond_day'},
                             {'bg_id': 'pond_day'}]}
        self.assertEqual(visuals.linked(script, {'continuity': 'auto'}), [False, True, False, True])
        self.assertEqual(visuals.linked(script, {}), [False, True, False, True])  # auto is the default
        self.assertEqual(visuals.linked(script, {'continuity': 'all'}), [False, True, True, True])
        self.assertEqual(visuals.linked(script, {'continuity': 'off'}), [False] * 4)

    def test_linked_scenes_form_ordered_chains(self):
        links = [False, True, True, False, True, False]
        self.assertEqual(visuals.chains(links, range(6)), [[0, 1, 2], [3, 4], [5]])
        self.assertEqual(visuals.chains(links, [1, 2, 4]), [[1, 2], [4]])  # scene 0 and 3 already have clips

    def test_contract_accepts_only_known_modes(self):
        plan = visuals.write_prompts(SAMPLE, CHANNEL, '9:16', 'offline')
        plan['continuity'] = 'all'
        self.assertEqual(contract.validate_visuals(plan, SAMPLE), [])
        plan['continuity'] = 'sometimes'
        self.assertIn("'sometimes' is not one of", '\n'.join(contract.validate_visuals(plan, SAMPLE)))
