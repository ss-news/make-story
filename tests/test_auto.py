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


class FlowTest(unittest.TestCase):
    def test_flow_marks_waiting_running_and_done_steps(self):
        from storyvid import flow
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            project(d, sheets=True)
            (d / 'story.txt').write_text('Once upon a time')
            states = {s['key']: s['state'] for s in flow.steps(d)}
            self.assertEqual([states[k] for k in ('story', 'approve', 'prompts', 'cast', 'approve_cast', 'images')],
                             ['done', 'done', 'done', 'done', 'wait', 'todo'])
            running = {s['key']: s['state'] for s in flow.steps(d, {'state': 'running', 'kind': 'auto'})}
            self.assertEqual(running['style'], 'running')  # first unfinished step that is not waiting for a person
            running = {s['key']: s['state'] for s in flow.steps(d, {'state': 'running', 'kind': 'render'})}
            self.assertEqual(running['video'], 'running')


class DuplicateResultTest(unittest.TestCase):
    def test_a_clip_identical_to_another_scene_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / 'a.mp4').write_bytes(b'clip one')
            (d / 'b.mp4').write_bytes(b'clip one')
            (d / 'c.mp4').write_bytes(b'clip two')
            plan = {'scenes': [{'clip': 'a.mp4'}, {'clip': ''}, {'clip': ''}]}
            self.assertEqual(visuals.same_as(d, plan, 1, 'clip', d / 'b.mp4'), 1)
            self.assertIsNone(visuals.same_as(d, plan, 2, 'clip', d / 'c.mp4'))
            with self.assertRaisesRegex(RuntimeError, "scene 1's clip"):
                visuals.checked(d, plan, 1, 'clip', d / 'b.mp4')
            self.assertFalse((d / 'b.mp4').exists())


class StopTest(unittest.TestCase):
    def test_stop_ends_the_job_and_the_step_it_started(self):
        import os
        import subprocess
        import sys
        import time
        from storyvid.web.__main__ import kill_group
        # a job that, like storyvid.auto, starts a child step and ignores SIGTERM in itself
        code = ("import signal, subprocess, sys, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                "c = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
                "print(c.pid, flush=True); time.sleep(60)")
        job = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, text=True, start_new_session=True)
        child = int(job.stdout.readline())
        kill_group(job)
        job.wait(timeout=10)
        for _ in range(50):
            try:
                os.kill(child, 0)
            except ProcessLookupError:
                break
            time.sleep(0.2)
        else:
            self.fail('the child step is still running')


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
