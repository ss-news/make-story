import subprocess
import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np
from PIL import Image

from storyvid.ffmpeg import ffmpeg_exe
from storyvid.render import SAFE_BOTTOM, SAFE_TOP
from storyvid.render_clips import ShortClipRenderer, fit_box, media_size, needs_fit
from storyvid.tts import SAMPLE_RATE

CHANNEL = {'channel_name': 'Test', 'tagline': 'Stories'}


def _timeline(folder: Path, seconds: float = 1.0) -> dict:
    samples = (np.sin(np.arange(int(SAMPLE_RATE * seconds)) / 8) * 8000).astype(np.int16)
    audio = folder / 'a.wav'
    with wave.open(str(audio), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SAMPLE_RATE); w.writeframes(samples.tobytes())
    return {'audio': audio, 'samples': samples, 'duration': seconds,
            'scenes': [{'start': 0, 'end': seconds, 'lines': []}],
            'cues': [{'start': 0, 'end': seconds, 'text': 'Một câu phụ đề khá dài để xuống hai dòng', 'speaker': ''}]}


def _frame(video: Path, size: tuple[int, int], at: float = 0.5) -> Image.Image:
    raw = subprocess.run([ffmpeg_exe(), '-v', 'error', '-ss', str(at), '-i', str(video), '-frames:v', '1',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return Image.frombytes('RGB', size, raw[:size[0] * size[1] * 3])


def _marked(size: tuple[int, int]) -> Image.Image:
    """Grey picture with a red band down the left edge and a green band down the right edge."""
    img = Image.new('RGB', size, (120, 120, 120))
    band = max(2, size[0] // 20)
    img.paste((230, 20, 20), (0, 0, band, size[1]))
    img.paste((20, 200, 20), (size[0] - band, 0, size[0], size[1]))
    return img


class ShortLayoutTest(unittest.TestCase):
    def test_wide_pictures_fit_and_tall_ones_fill(self):
        self.assertTrue(needs_fit((1920, 1080), (1080, 1920)))
        self.assertFalse(needs_fit((1080, 1920), (1080, 1920)))
        self.assertFalse(needs_fit((941, 1672), (1080, 1920)))
        self.assertEqual(fit_box((1920, 1080), (1080, 1000)), (1080, 606))

    def test_short_keeps_the_whole_wide_picture(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            image = folder / 'wide.png'
            _marked((640, 360)).save(image)
            clip = folder / 'wide.mp4'
            subprocess.run([ffmpeg_exe(), '-v', 'error', '-loop', '1', '-i', str(image), '-t', '0.5', '-r', '10',
                            '-pix_fmt', 'yuv420p', str(clip)], check=True)
            self.assertEqual(media_size(clip), (640, 360))
            for media in [(clip, None), (None, image)]:
                r = ShortClipRenderer(CHANNEL, 360, 10, 'A title', 'en')
                out = folder / 's.mp4'
                r.render_clips(_timeline(folder), [media], out)
                frame = np.asarray(_frame(out, r.out_size, 0.9)).astype(int)
                x0, y0, x1, y1 = r.picture_box()
                row = frame[(y0 + y1) // 2]
                red = (row[:, 0] > 150) & (row[:, 1] < 90)
                green = (row[:, 1] > 140) & (row[:, 0] < 90)
                # both edge bands are on screen: nothing was cut off the sides
                self.assertTrue(red[:r.W // 8].any(), media)
                self.assertTrue(green[-r.W // 8:].any(), media)
                # the picture stays between the title and the subtitles
                self.assertGreaterEqual(y0, r.title_bottom)
                self.assertLessEqual(y1, r.H * r.sub_top)

    def test_text_stays_inside_the_app_safe_zone(self):
        for r in [ShortClipRenderer(CHANNEL, 360, 10, 'A rather long title that needs two lines on a phone', 'en')]:
            self.assertGreaterEqual(r.title_bottom, r.H * SAFE_TOP)
            sub = r._subtitle('Một câu phụ đề khá dài để xuống hai dòng trên màn hình', '')
            self.assertLessEqual(r.H * r.sub_top + sub.height, r.H * SAFE_BOTTOM)
            # the badge row starts below the app's top bar
            alpha = np.asarray(r.overlay)[:, :, 3]
            text_rows = np.where((alpha > 250).sum(axis=1) > r.W * 0.02)[0]
            self.assertGreaterEqual(text_rows.min(), r.H * SAFE_TOP - 1)


if __name__ == '__main__':
    unittest.main()
