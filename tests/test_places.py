import io
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from storyvid import places
from storyvid.web.__main__ import OUTPUT, app

SCRIPT = {'scenes': [{'bg_prompt': 'large pale house behind iron gates'},
                     {'bg_prompt': 'Hoan Kiem Lake at dawn'},
                     {'bg_prompt': 'narrow tube houses in the rain'},
                     {'bg_prompt': 'a quiet street'}]}


def jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new('RGB', (40, 30), 'grey').save(buf, 'PNG')
    return buf.getvalue()


class PlacesTest(unittest.TestCase):
    def test_keywords_match_words_and_plurals_scene_lists_win(self):
        place = places.clean({'id': 'h', 'keywords': 'House, gate', 'scenes': '4', 'skip': [3]})
        self.assertEqual(place['keywords'], ['house', 'gate'])
        self.assertEqual(places.scenes_of(place, SCRIPT), [1, 4])
        self.assertFalse(places.uses(place, 'a warehouse', 9))  # whole words only

    def test_scene_gets_first_photo_and_slug_avoids_clashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            place = places.clean({'id': places.slug('Nhà 300 Kim Mã', set()), 'keywords': ['house']})
            self.assertEqual(place['id'], 'nha_300_kim_ma')
            self.assertEqual(places.slug('Nhà 300 Kim Mã', {'nha_300_kim_ma'}), 'nha_300_kim_ma_2')
            place['files'] += [places.add_photo(project, place, jpeg(), 'Front View.png'),
                               places.add_photo(project, place, jpeg(), 'Front View.png')]
            self.assertEqual(place['files'], ['refs/nha_300_kim_ma/front-view.jpg', 'refs/nha_300_kim_ma/front-view-2.jpg'])
            places.save(project, {'places': [place]})
            got = places.for_scene(project, SCRIPT, None, 0)
            self.assertEqual(got, [('nha_300_kim_ma', [project / 'refs/nha_300_kim_ma/front-view.jpg'])])
            self.assertEqual(places.for_scene(project, SCRIPT, None, 1), [])
            with self.assertRaises(ValueError):
                places.add_photo(project, place, b'not an image', 'x.jpg')


class PlacesApiTest(unittest.TestCase):
    def setUp(self):
        self.pid = '_test_places'
        self.dir = OUTPUT / self.pid
        self.dir.mkdir(parents=True, exist_ok=True)
        import json
        (self.dir / 'scenes.json').write_text(json.dumps(SCRIPT))
        self.client = app.test_client()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_add_upload_edit_and_delete(self):
        base = f'/api/projects/{self.pid}/places'
        r = self.client.post(base, json={'name': 'Nhà 300'})
        self.assertEqual(r.status_code, 200)
        pid = r.get_json()['places'][0]['id']
        r = self.client.post(f'{base}/{pid}/photos', data={'photos': (io.BytesIO(jpeg()), 'a.png')},
                             content_type='multipart/form-data')
        self.assertEqual(r.get_json()['places'][0]['files'], [f'refs/{pid}/a.jpg'])
        self.assertEqual(self.client.get(f'/files/{self.pid}/refs/{pid}/a.jpg').status_code, 200)
        self.assertEqual(self.client.get(f'/files/{self.pid}/refs/../scenes.json').status_code, 404)
        r = self.client.put(f'{base}/{pid}', json={'keywords': 'house', 'skip': ''})
        self.assertEqual(r.get_json()['places'][0]['used_in'], [1, 3])
        r = self.client.post(f'{base}/{pid}/photos', json={'url': 'file:///etc/passwd'})
        self.assertEqual(r.status_code, 400)
        r = self.client.delete(f'{base}/{pid}/photos/a.jpg')
        self.assertEqual(r.get_json()['places'][0]['files'], [])
        r = self.client.delete(f'{base}/{pid}')
        self.assertEqual(r.get_json()['places'], [])
        self.assertFalse((self.dir / 'refs' / pid).exists())


if __name__ == '__main__':
    unittest.main()
