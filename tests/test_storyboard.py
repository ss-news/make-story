import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from storyvid import contract, script as script_mod, script_review, storyboard, visuals

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = json.loads((ROOT / 'channel.json').read_text())
CAST = [{'id': 'lan', 'name': 'Lan', 'preset': 'young_woman', 'outfit': 'indigo', 'accessory': 'none',
         'kind': 'human'}]
TREATMENT = {'title': 'Bến sông', 'logline': 'Lan phải qua sông trước nửa đêm.', 'protagonist': 'lan',
             'want': 'qua sông', 'obstacle': 'con ma da', 'stakes': 'mất mạng', 'theme': 'can đảm',
             'cold_open': {'moment': 'bàn tay dưới nước', 'question': 'Ai đang kéo Lan?'},
             'cast': CAST, 'beats': [{'beat': 'cold_open', 'summary': 'Bàn tay', 'source': '', 'seconds': 10}],
             'setups': []}


def shot(text, size='CU', movement='push_in', actors=None, speaker='narrator', link='cut_on_action'):
    return {'link': link, 'size': size, 'angle': 'low', 'movement': movement, 'subject': 'Lan',
            'description': 'Mặt sông tối, Lan đứng ở mép nước.', 'start_frame': 'Lan at the water edge',
            'action': 'Lan steps back', 'performance': 'Lan stares at the water, breath held',
            'end_frame': 'Lan turns her head to the left', 'composition': 'Lan left third', 'actors': actors or [],
            'props': [], 'sound': 'nước', 'transition': 'smash_cut',
            'transition_note': 'Lan quay sang trái → cắt theo hướng nhìn',
            'lines': [{'speaker': speaker, 'text': text}] if text else []}


SHOTS = {'scenes': [
    {'slug': 'NGOẠI. BẾN SÔNG - ĐÊM', 'bg_id': 'river_night', 'bg_prompt': 'river at night', 'beat': 'cold_open',
     'setting': 'Bến sông lúc nửa đêm, sương mù, trăng mờ.', 'bridge': '',
     'purpose': 'móc câu', 'conflict': 'Lan với dòng nước', 'turn': 'bàn tay túm lấy chân',
     'shots': [shot('Đêm ấy, mặt sông đứng im.', 'EWS', 'crane_up', link='continuous'),
               shot(''),  # a silent shot cannot become a scenes.json scene
               shot('Buông tôi ra!', 'ECU', 'handheld',
                    [{'id': 'lan', 'position': 'center', 'pose': 'scared', 'expression': 'scared',
                      'action': 'shake'}], 'lan', link='continuous')]}]}


class StoryboardTest(unittest.TestCase):
    def write(self):
        reply = lambda provider, system, user, schema: (  # noqa: E731
            TREATMENT if schema is storyboard.TREATMENT_SCHEMA else SHOTS)
        board = {}
        with mock.patch.object(script_mod, '_ask', side_effect=reply) as ask:
            script = script_mod.write_script('Lan đi qua bến sông.', CHANNEL, 'vi', 1, 'muse', storyboard=board)
        return board, script, ask

    def test_each_shot_with_words_becomes_one_valid_scene(self):
        board, script, ask = self.write()
        self.assertEqual(ask.call_count, 2)
        self.assertIn('Open with the cold open', ask.call_args_list[1][0][1])
        self.assertIn('180-degree rule', ask.call_args_list[1][0][1])
        self.assertIn('Every shot starts where the previous one ended', ask.call_args_list[1][0][1])
        self.assertEqual(contract.validate(script)[0], [])
        self.assertEqual(len(script['scenes']), 2)
        self.assertEqual([s['camera'] for s in script['scenes']], ['zoom_out', 'static'])
        self.assertEqual(script['scenes'][1]['lines'][0]['speaker'], 'lan')
        self.assertEqual(board['format'], storyboard.FORMAT)
        self.assertEqual(board['logline'], TREATMENT['logline'])
        self.assertEqual([sh['scene'] for sh in board['scenes'][0]['shots']], [0, 1])
        first, second = board['scenes'][0]['shots']
        self.assertEqual(first['link'], 'new_scene')  # a scene's first shot always opens it
        self.assertEqual(second['link'], 'continuous')
        self.assertEqual(second['transition_note'], 'Lan quay sang trái → cắt theo hướng nhìn')
        self.assertEqual(board['scenes'][0]['setting'], 'Bến sông lúc nửa đêm, sương mù, trăng mờ.')

    def test_shots_follow_their_scenes_by_spoken_text(self):
        board, script, _ = self.write()
        edited = copy.deepcopy(script)
        edited['scenes'].reverse()
        edited['scenes'][0]['lines'][0]['text'] = 'Một câu khác.'
        shots = storyboard.aligned(board, edited)
        self.assertIsNone(shots[0])
        self.assertEqual(shots[1]['size'], 'EWS')
        self.assertEqual(shots[1]['slug'], 'NGOẠI. BẾN SÔNG - ĐÊM')

    def test_prompts_are_framed_by_the_shot(self):
        board, script, _ = self.write()
        out = visuals.write_prompts(script, CHANNEL, '16:9', 'offline', storyboard=board)
        self.assertTrue(out['scenes'][0]['image_prompt'].startswith('extreme wide shot, low angle'))
        self.assertIn('Crane up', out['scenes'][0]['video_prompt'])
        self.assertIn('Lan steps back', out['scenes'][1]['video_prompt'])
        self.assertIn('breath held', out['scenes'][1]['video_prompt'])
        self.assertIn('Ends on: Lan turns her head', out['scenes'][1]['video_prompt'])
        sent = {}

        def ask(provider, system, user):
            sent['payload'] = json.loads(user)
            return {}
        with mock.patch.object(visuals, '_ask', side_effect=ask):
            visuals.write_prompts(script, CHANNEL, '16:9', 'muse', storyboard=board)
        second = sent['payload']['scenes'][1]['shot']
        self.assertEqual(second['framing'], 'extreme close-up, low angle')
        self.assertIn('keeps rolling', second['joins_previous'])
        self.assertEqual(second['previous_end'], 'Lan turns her head to the left')

    def test_storyboard_decides_which_clips_continue(self):
        board, script, _ = self.write()
        script['scenes'].append(copy.deepcopy(script['scenes'][1]))
        script['scenes'][2]['lines'] = [{'speaker': 'narrator', 'text': 'Cảnh không có shot.'}]
        shots = storyboard.aligned(board, script)
        auto = {'continuity': 'auto'}
        # shot 2 keeps rolling from shot 1; scene 3 has no shot and stays in the same place
        self.assertEqual(visuals.linked(script, auto, shots), [False, True, True])
        shots[1] = {**shots[1], 'link': 'eyeline'}
        self.assertEqual(visuals.linked(script, auto, shots), [False, False, True])
        self.assertEqual(visuals.linked(script, {'continuity': 'off'}, shots), [False] * 3)

    def test_storyboard_file_and_web_summary(self):
        board, script, _ = self.write()
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertIsNone(storyboard.summary(d, script))
            (d / 'storyboard.json').write_text(json.dumps(board, ensure_ascii=False))
            info = storyboard.summary(d, script)
            self.assertEqual(info['logline'], TREATMENT['logline'])
            self.assertEqual([s['key'] for s in info['shots']], [storyboard.shot_key(s['lines'])
                                                                 for s in script['scenes']])
            self.assertTrue(info['shots'][0]['first'])

    def test_kept_text_and_explainers_skip_the_storyboard(self):
        part = {'title': 'T', 'cast': [], 'scenes': [{'bg_id': 'river_night', 'bg_prompt': 'x', 'camera': 'static',
                                                      'actors': [], 'props': [],
                                                      'lines': [{'speaker': 'narrator', 'text': 'Một câu.'}]}]}
        for kwargs in ({'keep_text': True}, {'genre': 'explainer'}):
            board = {}
            with mock.patch.object(script_mod, '_ask', return_value=part) as ask:
                script_mod.write_script('Một câu.', CHANNEL, 'vi', 1, 'muse', storyboard=board, **kwargs)
            self.assertEqual(ask.call_count, 1)
            self.assertEqual(board, {})


class OnScreenTest(unittest.TestCase):
    def test_speakers_are_put_on_screen(self):
        sh = {'actors': [{'id': 'lan', 'position': 'center'}],
              'lines': [{'speaker': 'ba', 'text': 'Về đi!'}, {'speaker': 'narrator', 'text': 'Gió nổi.'}]}
        actors, lines = storyboard.on_screen(sh, {'lan', 'ba'})
        self.assertEqual([a['id'] for a in actors], ['lan', 'ba'])
        self.assertNotEqual(actors[1]['position'], 'center')
        self.assertEqual(lines[0]['speaker'], 'ba')
        full = {'actors': [{'id': x, 'position': p} for x, p in (('a', 'left'), ('b', 'center'), ('c', 'right'))],
                'lines': [{'speaker': 'ba', 'text': 'Về đi!'}]}
        self.assertEqual(storyboard.on_screen(full, {'a', 'b', 'c', 'ba'})[1][0]['speaker'], 'narrator')


class TellingTest(unittest.TestCase):
    def test_long_narration_over_empty_places_is_flagged(self):
        scene = {'bg_id': 'river_night', 'bg_prompt': 'x', 'camera': 'static', 'actors': [], 'props': [],
                 'lines': [{'speaker': 'narrator', 'text': 'Lời kể dài về khung cảnh.'}]}
        script = {'lang': 'vi', 'scenes': [copy.deepcopy(scene) for _ in range(4)]}
        issues = script_review.telling_issues(script)
        self.assertTrue(any(i['scene'] is None for i in issues))
        self.assertTrue(any(i['scene'] == 0 and '4 cảnh' in i['problem'] for i in issues))
        script['scenes'][1]['actors'] = [{'id': 'lan'}]
        script['scenes'][1]['lines'] = [{'speaker': 'lan', 'text': 'Có ai đó dưới nước, nhìn kìa, nhìn kìa!'}] * 3
        self.assertEqual(script_review.telling_issues(script), [])


if __name__ == '__main__':
    unittest.main()
