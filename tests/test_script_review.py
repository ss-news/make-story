import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from storyvid import script as script_mod, script_review, visuals

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.scenes.json').read_text())


class ScriptReviewTest(unittest.TestCase):
    def test_long_texts_are_written_in_parts_with_the_same_cast(self):
        story = ('Đoạn văn dài. ' * 300 + '\n\n') * 3
        part = {'title': 'T', 'cast': [{'id': 'lan', 'name': 'Lan', 'preset': 'young_woman', 'outfit': 'indigo',
                                        'accessory': 'none', 'kind': 'human'}],
                'scenes': [{'bg_id': 'river_night', 'bg_prompt': 'x', 'camera': 'static', 'actors': [], 'props': [],
                            'lines': [{'speaker': 'narrator', 'text': 'Một câu.'}]}]}
        with mock.patch.object(script_mod, '_ask', return_value=part) as ask:
            out = script_mod.write_script(story, {'channel_name': 'C', 'host': {}}, 'vi', 10, 'muse',
                                          genre='explainer', keep_text=True)
        self.assertGreater(ask.call_count, 1)
        self.assertEqual(len(out['scenes']), ask.call_count)
        self.assertEqual(len(out['cast']), 1)
        self.assertIn('Keep its wording', ask.call_args_list[0][0][1])
        self.assertIn('Reuse these cast ids', ask.call_args_list[1][0][1])

    def test_genre_decides_how_a_story_is_written(self):
        channel = json.loads((ROOT / 'channel.json').read_text())
        part = {'title': 'T', 'cast': [], 'scenes': [{'bg_id': 'interior_day', 'bg_prompt': 'x', 'camera': 'static',
                                                      'actors': [], 'props': [],
                                                      'lines': [{'speaker': 'narrator', 'text': 'Một câu.'}]}]}
        from storyvid import storyboard
        treatment = {'title': 'T', 'cast': [], 'beats': []}
        shots = {'scenes': [{'slug': 'NỘI. NHÀ - NGÀY', 'bg_id': 'interior_day', 'bg_prompt': 'x', 'beat': 'setup',
                             'shots': [{'size': 'WS', 'movement': 'static',
                                        'lines': [{'speaker': 'narrator', 'text': 'Một câu.'}]}]}]}
        prompts = {}
        for genre in ('story', 'drama'):
            reply = lambda provider, system, user, schema: (  # noqa: E731
                treatment if schema is storyboard.TREATMENT_SCHEMA else shots)
            with mock.patch.object(script_mod, '_ask', side_effect=reply) as ask:
                out = script_mod.write_script('Một truyện ngắn.', channel, 'vi', 2, 'muse', genre=genre)
            self.assertEqual(len(out['scenes']), 1)
            prompts[genre] = ' '.join(c[0][1] for c in ask.call_args_list)
        self.assertIn('ghost and folklore story', prompts['story'])
        self.assertIn(channel['host']['personality'], prompts['story'])
        self.assertIn('real-life drama story', prompts['drama'])
        for ghost_only in ('ghost stories', 'folklore', 'ma da', 'chilling'):
            self.assertNotIn(ghost_only, prompts['drama'])
        days = {s['bg_id'] for s in script_mod._offline_script('Một. Hai. Ba. Bốn. Năm. Sáu. Bảy.', 'drama')['scenes']}
        self.assertTrue(all(b.endswith('_day') for b in days))

    def test_local_checks_flag_short_videos_and_long_scenes(self):
        script = copy.deepcopy(SAMPLE)
        script['scenes'][0]['lines'][0]['text'] = 'chữ ' * 60
        length, issues = script_review.local_checks(script, 10)
        self.assertLess(length['score'], 5)
        self.assertTrue(any(i['scene'] is None and i['severity'] == 'major' for i in issues))
        self.assertTrue(any(i['scene'] == 0 for i in issues))

    def test_review_scores_and_verdict(self):
        reply = {'criteria': [{'id': k, 'score': 9, 'comment': 'ok'} for k in script_review.CRITERIA],
                 'issues': [{'scene': 99, 'severity': 'weird', 'problem': 'p', 'fix': 'f'}], 'summary': 's'}
        with mock.patch.object(script_review, '_ask', return_value=reply):
            out = script_review.review(SAMPLE, 'source', 1, 'muse', 'story')
        self.assertEqual(out['issues'][0]['scene'], None)        # out-of-range scene index becomes whole-video
        self.assertEqual(out['issues'][0]['severity'], 'minor')  # unknown severity becomes minor
        self.assertEqual(out['criteria'][-1]['id'], 'length')

    def test_revise_replaces_and_splits_scenes_then_clears_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'scenes.json').write_text(json.dumps(SAMPLE))
            (d / 'meta.json').write_text(json.dumps({'approved_script': visuals.script_digest(SAMPLE), 'lang': 'vi'}))
            (d / 'script_reviews.json').write_text(json.dumps({'format': script_review.FORMAT, 'rounds': [
                {'round': 1, 'kind': 'review', 'issues': [{'scene': 1, 'severity': 'major', 'problem': 'p', 'fix': 'f'}]}]}))
            new = copy.deepcopy(SAMPLE['scenes'][0])
            with mock.patch.object(script_review, '_ask', return_value={'replacements': [{'index': 1, 'scenes': [new, new]}]}):
                entry = script_review.do_revise(d, 'muse')
            revised = json.loads((d / 'scenes.json').read_text())
            self.assertEqual(len(revised['scenes']), len(SAMPLE['scenes']) + 1)
            self.assertEqual(entry['changed_scenes'], [1])
            self.assertTrue((d / entry['backup']).exists())
            self.assertFalse(visuals.is_approved(d))


if __name__ == '__main__':
    unittest.main()


class KeepTextTest(unittest.TestCase):
    def scene(self, text):
        return {'bg_id': 'river_night', 'bg_prompt': 'x', 'camera': 'static', 'actors': [], 'props': [],
                'lines': [{'speaker': 'narrator', 'text': text}]}

    def test_dedupe_drops_repeats_but_keeps_short_refrains(self):
        long = 'Tám chữ trở lên thì coi là một câu lặp thật sự.'
        script = {'scenes': [self.scene(long), self.scene('Đó là hành vi.'), self.scene('Đó là hành vi.'),
                             self.scene('Khác hẳn.'), self.scene('Khác hẳn nữa.'), self.scene(long)]}
        out, changed = script_review.dedupe(script)
        self.assertEqual(changed, [2, 5])
        self.assertEqual(len(out['scenes']), 4)

    def test_ai_cannot_change_fixed_narration(self):
        script = {'title': 'T', 'lang': 'vi', 'cast': [], 'scenes': [self.scene('Câu một của cảnh.'), self.scene('Câu hai.')]}
        source = 'Câu một của cảnh. Câu hai.'
        changed_text = {'replacements': [{'index': 0, 'scenes': [self.scene('Câu một của cảnh, thêm bịa.')]}]}
        restaged = {'replacements': [{'index': 1, 'scenes': [{**self.scene('Câu hai.'), 'bg_prompt': 'new place'}]}]}
        issue = lambda i: {'scene': i, 'severity': 'minor', 'problem': 'p', 'fix': 'f'}  # noqa: E731
        with mock.patch.object(script_review, '_ask', return_value=changed_text):
            out, _ = script_review.revise(script, source, [issue(0)], 'muse', 'explainer', 'vi', keep_text=True)
        self.assertEqual(out['scenes'][0]['lines'][0]['text'], 'Câu một của cảnh.')
        with mock.patch.object(script_review, '_ask', return_value=restaged):
            out, changed = script_review.revise(script, source, [issue(1)], 'muse', 'explainer', 'vi', keep_text=True)
        self.assertEqual(out['scenes'][1]['bg_prompt'], 'new place')
        self.assertEqual(changed, [1])


class PolishTest(unittest.TestCase):
    def test_rewrite_that_drops_a_fact_keeps_the_original(self):
        text = 'In 1982 two countries signed a deal.\n\nFive people said ninety-one souls were trapped, said Hoang Nam.'
        critique = {'criteria': [{'id': 'voice', 'score': 6, 'comment': 'ok'}], 'notes': ['vivid'], 'summary': 's'}
        rewrites = iter([critique,
                         {'text': 'Back in 1982 two nations signed a deal.'},
                         {'text': 'Some people said many souls were trapped there, said Hoang Nam.'}])
        with mock.patch.object(script_review, '_ask', side_effect=lambda *a, **k: next(rewrites)), \
                mock.patch.object(script_mod, 'split_text', side_effect=lambda t, size=0: t.split('\n\n')):
            out = script_review.polish(text, 'muse', 'en')
        self.assertIn('Back in 1982', out['text'])           # kept: same facts
        self.assertIn('ninety-one souls', out['text'])       # dropped number -> original part kept
        self.assertEqual(len(out['kept_parts']), 1)


class SourceOrderTest(unittest.TestCase):
    def test_a_line_said_twice_stays_where_its_scene_belongs(self):
        scene = lambda t: {'lines': [{'speaker': 'narrator', 'text': t}]}  # noqa: E731
        source = 'I am Cu Rua, the old turtle. The house is empty. I am Cu Rua. Thank you for walking with me.'
        script = {'scenes': [scene('I am Cu Rua, the old turtle.'), scene('I am Cu Rua. Thank you for walking with me.'),
                             scene('The house is empty.')]}
        out, moved = script_review.source_order(script, source)
        self.assertEqual([s['lines'][0]['text'][:12] for s in out['scenes']],
                         ['I am Cu Rua,', 'The house is', 'I am Cu Rua.'])
