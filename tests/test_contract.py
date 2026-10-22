import copy
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from storyvid import check, contract, pack

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.scenes.json').read_text())
PROP_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 360"><rect x="180" y="200" width="120" height="120" fill="#88624a"/></svg>'
BG_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900"><rect width="1600" height="900" fill="#e8eced"/></svg>'


def scenes(**changes):
    script = copy.deepcopy(SAMPLE)
    script['scenes'][0].update(changes)
    return script


class ScriptContractTest(unittest.TestCase):
    def test_sample_follows_the_contract(self):
        self.assertEqual(contract.validate(SAMPLE), ([], []))

    def test_problems_are_reported_with_their_path(self):
        script = scenes(camera='dolly', extra=1)
        script['scenes'][1]['lines'][0]['speaker'] = 'ma_da'  # not on stage in scene 1
        del script['format']
        errors, _ = contract.validate(script)
        self.assertEqual(errors, ['$: missing format'])
        script['format'] = contract.FORMAT
        errors, _ = contract.validate(script)
        self.assertIn('$.scenes[0]: unknown field(s) extra', errors)
        self.assertIn("$.scenes[0].camera: 'dolly' is not one of zoom_in, zoom_out, pan_left, pan_right, static", errors)
        self.assertIn("$.scenes[1].lines[0].speaker: 'ma_da' must be 'narrator' or a cast id on stage", errors)

    def test_background_ids_name_day_or_night(self):
        errors, _ = contract.validate(scenes(bg_id='river'))
        self.assertTrue(errors[0].startswith('$.scenes[0].bg_id'))

    def test_unknown_assets_become_requests(self):
        script = scenes(bg_id='bamboo_forest_night', bg_prompt='dense bamboo forest at night',
                        props=[{'id': 'coffin', 'position': 'far_left'}])
        script['cast'][0]['preset'] = 'monk'
        errors, requests = contract.validate(script)
        self.assertEqual(errors, [])
        self.assertEqual({(r['group'], r['id']) for r in requests},
                         {('backgrounds', 'bamboo_forest_night'), ('props', 'coffin'), ('characters', 'monk')})
        doc = contract.request_file(requests, Path('x/scenes.json'))
        bg = next(r for r in doc['requests'] if r['id'] == 'bamboo_forest_night')
        self.assertEqual(bg['description'], 'dense bamboo forest at night')
        self.assertEqual(bg['spec']['file'], 'assets/bac-bo-stick/extra/backgrounds/bamboo_forest_night.svg')

    def test_check_command_writes_and_clears_requests(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            path = Path(tmp) / 'scenes.json'
            path.write_text(json.dumps(scenes(props=[{'id': 'coffin', 'position': 'left'}])))
            self.assertEqual(check.check_script(path), 2)
            self.assertTrue((Path(tmp) / 'asset_requests.json').exists())
            path.write_text(json.dumps(SAMPLE))
            self.assertEqual(check.check_script(path), 0)
            self.assertFalse((Path(tmp) / 'asset_requests.json').exists())
            path.write_text(json.dumps(scenes(pose='x')))
            self.assertEqual(check.check_script(path), 1)

    def test_review_report(self):
        review = json.loads((ROOT / 'examples' / 'ma_da_bac_bo.review.json').read_text())
        self.assertEqual(contract.validate_review(review, len(SAMPLE['scenes'])), [])
        with redirect_stdout(StringIO()):
            self.assertEqual(check.check_review(ROOT / 'examples' / 'ma_da_bac_bo.review.json'), 0)
        bad = copy.deepcopy(review)
        bad['verdict'] = 'pass'
        bad['issues'][1]['scene'] = 99
        bad['issues'][1]['owner'] = 'gemini'
        errors = contract.validate_review(bad, len(SAMPLE['scenes']))
        self.assertIn("$.verdict: 'pass' is not allowed with blocker or major issues", errors)
        self.assertIn('$.issues[1].scene: must be null or a scene index (0-based)', errors)
        self.assertIn("$.issues[1].owner: 'gemini' is not one of codex, tool", errors)
        self.assertIn("$.verdict: 'fix' needs at least one issue",
                      contract.validate_review({**review, 'issues': []}))

    def test_reference_files_are_up_to_date(self):
        self.assertEqual(json.loads(contract.SCHEMA_PATH.read_text()), json.loads(json.dumps(contract.json_schema())))
        self.assertEqual(json.loads(contract.CATALOG_PATH.read_text()), json.loads(json.dumps(contract.catalog())))
        self.assertEqual(json.loads(contract.REVIEW_SCHEMA_PATH.read_text()),
                         json.loads(json.dumps(contract.review_schema())))


class ExtraAssetsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.extra = Path(self.tmp.name)
        patcher = mock.patch.object(pack, 'EXTRA', self.extra)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.addCleanup(pack.reload)

    def add(self, assets):
        (self.extra / 'manifest.json').write_text(json.dumps({'assets': assets, 'characters': []}))
        pack.reload()

    def test_base_pack_passes(self):
        self.add([])
        self.assertEqual(check.asset_problems(), [])

    def test_delivered_assets_are_checked_and_usable(self):
        (self.extra / 'props').mkdir()
        (self.extra / 'backgrounds').mkdir()
        (self.extra / 'props' / 'coffin.svg').write_text(PROP_SVG)
        (self.extra / 'props' / 'goat.svg').write_text(PROP_SVG.replace('480 360', '400 300'))
        (self.extra / 'backgrounds' / 'bamboo_forest_night.svg').write_text(BG_SVG)
        self.add([
            {'id': 'coffin', 'label': 'Quan tài', 'group': 'props', 'svg': 'props/coffin.svg'},
            {'id': 'goat', 'label': 'Dê', 'group': 'animals', 'svg': 'props/goat.svg'},
            {'id': 'bamboo_forest_night', 'label': 'Rừng tre · đêm', 'group': 'backgrounds',
             'svg': 'backgrounds/bamboo_forest_night.svg'},
        ])
        problems = check.asset_problems()
        self.assertEqual(problems, ["animals/goat: animals need facing -1 (looks left) or 1 (looks right)",
                                    "animals/goat: viewBox must be '0 0 480 360', got '0 0 400 300'"])
        script = scenes(bg_id='bamboo_forest_night', props=[{'id': 'coffin', 'position': 'left'}])
        self.assertEqual(contract.validate(script), ([], []))
        self.assertEqual(pack.raster('coffin', 90).size, (120, 90))
        self.assertIsNone(pack.facing('coffin'))


if __name__ == '__main__':
    unittest.main()
