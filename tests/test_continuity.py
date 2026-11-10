import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image
from storyvid import visuals, auto
from storyvid.web.__main__ import app, OUTPUT
from tests.test_auto import project


class ContinuityTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name).resolve()
        self.plan = project(self.d, sheets=True)
        self.plan["continuity"] = "off"
        visuals.save(self.d, self.plan)
        from storyvid import continuity
        self.c = continuity
        meta = visuals.meta(self.d)
        meta['approved_cast'] = visuals.cast_digest(self.d, self.plan)
        (self.d / 'meta.json').write_text(json.dumps(meta))

    def approve(self):
        data = self.c.load(self.d)
        data['approved'] = self.c.digest(self.d)
        self.c.save(self.d, data)

    def asset(self):
        (self.d / 'refs').mkdir(exist_ok=True)
        (self.d / 'refs/house.png').write_bytes(b'house')
        self.c.save(self.d, {'assets': [{'id': 'house', 'kind': 'place', 'name': 'Nhà',
            'description': 'One door, two windows', 'scenes': [1], 'image': 'refs/house.png'}]})

    def test_new_project_waits_and_auto_does_not_generate_scenes(self):
        self.assertFalse(self.c.status(self.d)['approved'])
        with mock.patch.object(auto, 'step') as step:
            self.assertEqual(auto.run(self.d, '1080', 'offline'), 0)
        step.assert_not_called()

    def test_same_size_reference_edit_revokes_both_approvals(self):
        self.asset()
        self.approve()
        self.assertTrue(self.c.status(self.d)['approved'])
        (self.d / 'refs/house.png').write_bytes(b'HOUSE')
        self.assertFalse(self.c.status(self.d)['approved'])
        meta = visuals.meta(self.d)
        meta['approved_cast'] = visuals.cast_digest(self.d, self.plan)
        (self.d / 'meta.json').write_text(json.dumps(meta))
        sheet = self.d / self.plan['cast'][0]['sheet']
        sheet.write_bytes(b'PNG')  # same length
        self.assertFalse(visuals.is_cast_approved(self.d))

    def test_asset_references_only_go_to_assigned_scene(self):
        self.asset()
        note, refs = self.c.references(self.d, 0)
        self.assertIn('One door, two windows', note)
        self.assertEqual(refs, [self.d / 'refs/house.png'])
        self.assertEqual(self.c.references(self.d, 1), ('', []))

    def test_invalid_paths_missing_photos_and_bad_scene_numbers_block_approval(self):
        self.asset()
        data = self.c.load(self.d)
        for path in ('../escape.png', '/etc/passwd', 'refs/missing.png'):
            data['assets'][0]['image'] = path
            self.c.save(self.d, data)
            self.assertTrue(self.c.status(self.d)['errors'])
        data['assets'][0].update(image='refs/house.png', scenes=[9999])
        self.c.save(self.d, data)
        self.assertTrue(self.c.status(self.d)['errors'])

    def test_prompt_edits_revoke_approval_but_output_files_do_not(self):
        self.approve()
        self.plan['scenes'][0]['image'] = 'muse/new.png'
        visuals.save(self.d, self.plan)
        self.assertTrue(self.c.status(self.d)['approved'])
        self.plan['scenes'][0]['image_prompt'] += ' changed layout'
        visuals.save(self.d, self.plan)
        self.assertFalse(self.c.status(self.d)['approved'])

    def test_over_budget_fails_instead_of_dropping_references(self):
        self.asset()
        self.c.save(self.d, {'assets': [dict(self.c.load(self.d)['assets'][0], id=f'h{i}') for i in range(5)]})
        self.assertTrue(any('4' in e for e in self.c.status(self.d)['errors']))

    def test_generating_requires_approval_and_passes_reference_to_image_and_clip(self):
        self.asset()
        with mock.patch.object(visuals, '_generate') as gen:
            with self.assertRaisesRegex(RuntimeError, 'Duyệt bộ mẫu'):
                visuals.make_scenes(self.d, [0], False, False)
            gen.assert_not_called()
        self.approve()
        seen = []
        def generate(media, prompt, size, target, references, negative=''):
            seen.append((media, prompt, references))
            target.parent.mkdir(exist_ok=True, parents=True)
            target.write_bytes(media.encode())
            return target
        with mock.patch.object(visuals, '_generate', side_effect=generate), mock.patch.object(visuals, 'ready_accounts', return_value=1):
            self.assertEqual(visuals.make_scenes(self.d, [0], False, False), 0)
        self.assertEqual([x[0] for x in seen], ['image', 'video'])
        for _, prompt, refs in seen:
            self.assertIn('One door, two windows', prompt)
            self.assertIn(self.d / 'refs/house.png', refs)
        self.assertNotIn(1, self.c.status(self.d)['stale'])
        (self.d / 'refs/house.png').write_bytes(b'OTHER')
        self.assertIn(1, self.c.status(self.d)['stale'])

    def test_legacy_place_reference_is_also_sent_to_clip(self):
        from storyvid import places
        self.asset()
        places.save(self.d, {'places': [{'id':'legacy', 'name':'Old house panel', 'keywords':[],
            'scenes':[1], 'skip':[], 'files':['refs/house.png'], 'sources':[]}]})
        self.c.save(self.d, {'assets':[]})
        self.approve()
        seen=[]
        def generate(media,prompt,size,target,references,negative=''):
            seen.append((media,references));target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(media.encode());return target
        with mock.patch.object(visuals,'_generate',side_effect=generate), mock.patch.object(visuals,'ready_accounts',return_value=1):
            self.assertEqual(visuals.make_scenes(self.d,[0],False,False),0)
        for _,refs in seen:
            self.assertIn(self.d/'refs/house.png',refs)

    def test_trial_clips_report_missing_opening_images(self):
        self.approve()
        with mock.patch.object(visuals,'_generate') as gen, mock.patch.object(visuals,'ready_accounts',return_value=1):
            self.assertEqual(visuals.make_scenes(self.d,[0],False,False,clips_only=True),1)
            gen.assert_not_called()
        self.assertIn('ảnh',visuals.load(self.d)[1]['scenes'][0]['error'])

    def test_reference_changed_during_generation_cannot_receive_a_current_receipt(self):
        self.asset()
        self.approve()
        def generate(media, prompt, size, target, references, negative=''):
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'old-result')
            (self.d / 'refs/house.png').write_bytes(b'NEW-HOUSE')
            return target
        with mock.patch.object(visuals, '_generate', side_effect=generate), mock.patch.object(visuals, 'ready_accounts', return_value=1):
            self.assertEqual(visuals.make_scenes(self.d, [0], False, True), 1)
        self.assertFalse(self.c.current(self.d, 0, 'image'))

    def test_replacing_opening_image_invalidates_existing_clip(self):
        self.asset()
        self.approve()
        self.plan['scenes'][0].update(image='muse/frame.png', clip='muse/clip.mp4')
        visuals.save(self.d, self.plan)
        (self.d / 'muse/frame.png').write_bytes(b'frame')
        (self.d / 'muse/clip.mp4').write_bytes(b'clip')
        self.c.record(self.d, 0, 'image')
        self.c.record(self.d, 0, 'clip')
        self.assertTrue(self.c.current(self.d, 0, 'clip'))
        (self.d / 'muse/frame.png').write_bytes(b'FRAME')
        self.assertFalse(self.c.current(self.d, 0, 'clip'))


class ContinuityApiTest(unittest.TestCase):
    def setUp(self):
        self.pid = '_test_continuity'
        self.d = OUTPUT / self.pid
        self.d.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: shutil.rmtree(self.d, ignore_errors=True))
        plan = project(self.d, sheets=True)
        plan["continuity"] = "off"
        visuals.save(self.d, plan)
        meta = visuals.meta(self.d)
        meta['approved_cast'] = visuals.cast_digest(self.d, plan)
        (self.d / 'meta.json').write_text(json.dumps(meta))
        self.client = app.test_client()
        self.base = f'/api/projects/{self.pid}/continuity'

    def test_upload_save_approve_and_mutation_gate(self):
        self.assertEqual(self.client.get(self.base).status_code, 200)
        buf = io.BytesIO()
        Image.new('RGB', (8, 8), 'grey').save(buf, 'PNG');buf.seek(0)
        r = self.client.post(self.base + '/photo', data={'photo': (buf, 'house.png')})
        self.assertEqual(r.status_code, 200)
        asset = {'id': 'house', 'kind': 'place', 'name': 'Nhà', 'description': 'Low roof',
                 'scenes': [1], 'image': r.get_json()['image']}
        self.assertEqual(self.client.put(self.base, json={'assets': [asset], 'approved': 'forged'}).status_code, 200)
        self.assertFalse(self.client.get(self.base).get_json()['approved'])
        r = self.client.post(self.base + '/approve', json={'reviewed': True})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()['approved'])
        asset['description'] = 'Different roof'
        self.client.put(self.base, json={'assets': [asset]})
        with mock.patch('storyvid.web.__main__.start_job') as start:
            self.assertEqual(self.client.post(f'/api/projects/{self.pid}/visuals/scenes', json={}).status_code, 409)
            start.assert_not_called()

    def test_approval_requires_human_action_and_valid_assets(self):
        self.assertEqual(self.client.post(self.base + '/approve', json={}).status_code, 400)
        self.client.put(self.base, json={'assets': [{'id':'x', 'kind':'prop', 'name':'x',
            'description':'x', 'scenes':[1], 'image':'refs/missing.png'}]})
        self.assertEqual(self.client.post(self.base + '/approve', json={'reviewed':True}).status_code, 409)
