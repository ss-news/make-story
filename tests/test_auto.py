import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from storyvid import auto, visuals
from storyvid.web.__main__ import OUTPUT, app

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.scenes.json').read_text())
CHANNEL = json.loads((ROOT / 'channel.json').read_text())


def project(d: Path, sheets: bool) -> dict:
    """An approved script with an offline picture plan, optionally with every character sheet made."""
    (d / 'scenes.json').write_text(json.dumps(SAMPLE))
    (d / 'meta.json').write_text(json.dumps({'approved_script': visuals.script_digest(SAMPLE)}))
    plan = visuals.write_prompts(SAMPLE, CHANNEL, '16:9', 'offline')
    if sheets:
        (d / 'muse' / 'cast').mkdir(parents=True)
        for c in plan['cast']:
            (d / 'muse' / 'cast' / f"{c['id']}.png").write_bytes(b'png')
            c['sheet'] = f"muse/cast/{c['id']}.png"
    visuals.save(d, plan)
    return plan


class CastGateTest(unittest.TestCase):
    def test_cast_approval_is_lost_when_a_sheet_or_look_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            plan = project(d, sheets=True)
            self.assertFalse(visuals.is_cast_approved(d))
            meta = json.loads((d / 'meta.json').read_text())
            meta['approved_cast'] = visuals.cast_digest(d, plan)
            (d / 'meta.json').write_text(json.dumps(meta))
            self.assertTrue(visuals.is_cast_approved(d))
            (d / plan['cast'][0]['sheet']).write_bytes(b'a remade sheet')
            self.assertFalse(visuals.is_cast_approved(d))

    def test_auto_stops_for_the_character_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            project(d, sheets=True)
            with mock.patch.object(auto, 'step', return_value=0) as step:
                self.assertEqual(auto.run(d, '1080', 'offline'), 0)
            step.assert_not_called()  # prompts and sheets exist, the scenes wait for a person

    def test_auto_runs_every_step_after_the_approvals(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            plan = project(d, sheets=True)
            meta = json.loads((d / 'meta.json').read_text())
            meta['approved_cast'] = visuals.cast_digest(d, plan)
            (d / 'meta.json').write_text(json.dumps(meta))
            with mock.patch.object(auto, 'step', return_value=0) as step, \
                    mock.patch.object(auto, 'scenes_left', side_effect=[3, 0]):
                self.assertEqual(auto.run(d, '1080', 'offline'), 0)
            modules = [(c.args[1], c.args[2]) for c in step.call_args_list]
            self.assertEqual(modules, [('storyvid.visuals', 'scenes'), ('storyvid.cli', '--script'),
                                       ('storyvid.finish', 'loudnorm'), ('storyvid.finish', 'check')])

    def test_auto_needs_an_approved_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'scenes.json').write_text(json.dumps(SAMPLE))
            with mock.patch.object(auto, 'step') as step:
                self.assertEqual(auto.run(d, '1080', 'offline'), 1)
            step.assert_not_called()


class CastApiTest(unittest.TestCase):
    def setUp(self):
        self.pid = '_test_auto'
        self.dir = OUTPUT / self.pid
        self.dir.mkdir(parents=True, exist_ok=True)
        self.client = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_scenes_wait_for_the_approved_cast(self):
        project(self.dir, sheets=True)
        base = f'/api/projects/{self.pid}'
        self.assertFalse(self.client.get(base).get_json()['cast_approved'])
        self.assertEqual(self.client.post(f'{base}/visuals/scenes', json={}).status_code, 409)
        r = self.client.post(f'{base}/approve-cast')
        self.assertTrue(r.get_json()['cast_approved'])

    def test_cannot_approve_missing_sheets(self):
        project(self.dir, sheets=False)
        self.assertEqual(self.client.post(f'/api/projects/{self.pid}/approve-cast').status_code, 400)


if __name__ == '__main__':
    unittest.main()
