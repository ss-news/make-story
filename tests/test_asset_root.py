"""A custom library must be isolated from the default renderer assets."""
import json
import tempfile
import unittest
from pathlib import Path

from storyvid.character import ASSETS, Character


class AssetRootTest(unittest.TestCase):
    def test_custom_root_is_used_without_mutating_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / 'young_man'
            target.mkdir()
            rig = json.loads((ASSETS / 'young_man' / 'rig.json').read_text())
            for part in rig['parts'].values():
                (target / part['file']).write_text('<svg xmlns="http://www.w3.org/2000/svg"><circle r="7" fill="red"/></svg>')
            (target / 'rig.json').write_text(json.dumps(rig))
            custom = Character({}, 240, asset_root=root)
            self.assertEqual(custom.folder, target)
            self.assertIn('red', custom.parts['head'])
            self.assertEqual(Character({}, 240).folder, ASSETS / 'young_man')
            self.assertNotIn('fill="red"', Character({}, 240).parts['head'])
