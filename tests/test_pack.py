import tempfile
import unittest
from pathlib import Path

from storyvid import pack
from storyvid.backgrounds import make_backgrounds
from storyvid.script import _normalize


class PackTest(unittest.TestCase):
    def test_backgrounds_match_by_id_or_keywords(self):
        self.assertEqual(pack.match_background('river_night'), 'river_night')
        self.assertEqual(pack.match_background('bg0', 'dark river at night under the moon'), 'river_night')
        self.assertEqual(pack.match_background('cho', 'busy village market'), 'market_day')
        self.assertEqual(pack.match_background('x', 'somewhere'), 'village_path_day')

    def test_backgrounds_are_rasterized_from_the_pack(self):
        script = {'scenes': [{'bg_id': 'river_night', 'bg_prompt': ''}, {'bg_id': 'yard', 'bg_prompt': 'courtyard'}]}
        with tempfile.TemporaryDirectory() as tmp:
            paths = make_backgrounds(script, (320, 180), Path(tmp))
            self.assertEqual(set(paths), {'river_night', 'yard'})
            self.assertIn('courtyard_day', paths['yard'].name)
            self.assertTrue(all(p.exists() for p in paths.values()))

    def test_unknown_props_are_kept_for_asset_requests(self):
        scene = {'bg_id': 'pond_day', 'bg_prompt': '', 'camera': 'static', 'actors': [],
                 'lines': [{'speaker': 'narrator', 'text': 'Ao làng.'}],
                 'props': [{'id': 'buffalo', 'position': 'far_right'}, {'id': 'dragon', 'position': 'left'},
                           {'id': 'duck', 'position': 'nowhere'}]}
        props = _normalize({'scenes': [scene]})['scenes'][0]['props']
        self.assertEqual(props, [{'id': 'buffalo', 'position': 'far_right'}, {'id': 'dragon', 'position': 'left'},
                                 {'id': 'duck', 'position': 'center'}])

    def test_trimmed_asset_has_no_empty_border(self):
        img = pack.trimmed('buffalo', 300)
        self.assertEqual(img.getchannel('A').getbbox(), (0, 0, img.width, img.height))


if __name__ == '__main__':
    unittest.main()
