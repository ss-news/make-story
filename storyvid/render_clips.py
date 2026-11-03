"""Render a script with Muse clips (visuals.json) instead of the stick-figure stage.

Each scene plays its clip under the scene's narration: the clip is slowed down a little when the narration is
longer (up to MAX_SLOW), then its last frame holds with a slow push-in. A scene with an image but no clip gets a
slow push-in on the image. Subtitles, channel badge and the Short chrome come from the normal renderers.

A clip that already has the frame's shape (or close to it) fills the frame. In a 9:16 Short a wider clip is never
cropped to fill the frame: the whole picture sits between the title and the subtitles, over a blurred, darkened copy
of itself that fills the rest of the frame (no black bars), and its push-in grows the picture instead of cutting it.
"""
import math
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

from .ffmpeg import ffmpeg_exe
from .render import Renderer, SafeShortRenderer

MAX_SLOW = 1.35   # play a clip at most this much slower to cover a long narration
HOLD_ZOOM = 0.06  # push-in while a clip's last frame holds, over the held time
STILL_ZOOM = 0.12 # push-in over a scene that only has an image
COVER_SLACK = 1.15  # a picture at most this much wider or taller than the frame fills it (cuts at most ~7% a side)
BACKDROP_DIM = 0.42 # brightness of the blurred copy behind a fitted picture


def clip_duration(path: Path) -> float:
    out = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def media_size(path: Path) -> tuple[int, int]:
    """Width and height of a video or image."""
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        with Image.open(path) as img:
            return img.size
    out = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Video: .*?, (\d{2,5})x(\d{2,5})", out)
    return (int(m[1]), int(m[2])) if m else (0, 0)


def needs_fit(media: tuple[int, int], frame: tuple[int, int]) -> bool:
    """True when filling the frame would cut too much of the picture (a 16:9 clip in a 9:16 Short)."""
    if not media[0] or not media[1]:
        return False
    ratio = (media[0] / media[1]) / (frame[0] / frame[1])
    return ratio > COVER_SLACK or ratio < 1 / COVER_SLACK


def fit_box(media: tuple[int, int], box: tuple[int, int]) -> tuple[int, int]:
    """The largest size with the media's shape inside box (even numbers, for the encoder)."""
    scale = min(box[0] / media[0], box[1] / media[1])
    return max(2, int(media[0] * scale) // 2 * 2), max(2, int(media[1] * scale) // 2 * 2)


def playback_speed(scene_seconds: float, clip_seconds: float) -> float:
    """How much slower to play the clip: 1 (normal) up to MAX_SLOW."""
    if clip_seconds <= 0:
        return 1.0
    return max(1.0, min(MAX_SLOW, scene_seconds / clip_seconds))


class _ClipFrames:
    """Frames of one clip at the given size and fps, optionally slowed down. cover=True fills size and crops the
    overflow; cover=False scales to size as is (size already has the clip's shape)."""

    def __init__(self, path: Path, size: tuple[int, int], fps: int, slow: float, cover: bool = True):
        w, h = size
        vf = f"setpts={slow:.4f}*PTS,fps={fps},scale={w}:{h}"
        if cover:
            vf += f":force_original_aspect_ratio=increase,crop={w}:{h}"
        self.size = size
        self.proc = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-i", str(path), "-an", "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                     stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)  # closed early on purpose

    def next(self) -> Image.Image | None:
        n = self.size[0] * self.size[1] * 3
        data = self.proc.stdout.read(n) if self.proc.stdout else b""
        if len(data) < n:
            self.close()
            return None
        return Image.frombytes("RGB", self.size, data)

    def close(self) -> None:
        if self.proc.poll() is None:
            self.proc.stdout.close()
            self.proc.terminate()
        self.proc.wait()


def _cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    w, h = size
    scale = max(w / img.width, h / img.height)
    img = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)), Image.LANCZOS)
    left, top = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def _push_in(img: Image.Image, amount: float) -> Image.Image:
    """Zoom into the centre by `amount` (0.1 = 10 %)."""
    if amount <= 0:
        return img
    w, h = img.size
    cw, ch = w / (1 + amount), h / (1 + amount)
    box = ((w - cw) / 2, (h - ch) / 2, (w + cw) / 2, (h + ch) / 2)
    return img.resize((w, h), Image.BICUBIC, box=box)


def _backdrop(picture: Image.Image, size: tuple[int, int]) -> Image.Image:
    """The picture blurred, darkened and stretched to fill size, for behind a fitted picture."""
    w, h = size
    small = _cover(picture.resize((max(1, picture.width // 10), max(1, picture.height // 10)), Image.BILINEAR),
                   (max(1, w // 10), max(1, h // 10)))
    small = ImageEnhance.Brightness(small.filter(ImageFilter.GaussianBlur(3))).enhance(BACKDROP_DIM)
    return small.resize(size, Image.BILINEAR)


class _Fitted:
    """Composes one frame of a fitted scene: the whole picture inside the renderer's picture box, grown by `grow`
    (0.1 = 10 % larger, never past the box), over its own blurred backdrop."""

    def __init__(self, box: tuple[int, int, int, int], frame: tuple[int, int], media: tuple[int, int], grow: float):
        self.box, self.frame = box, frame
        self.full = fit_box(media, (box[2] - box[0], box[3] - box[1]))
        self.base = fit_box(media, (int(self.full[0] / (1 + grow)), int(self.full[1] / (1 + grow))))

    def compose(self, picture: Image.Image, grow: float) -> Image.Image:
        """picture is at self.base size; grow from 0 (base size) to the box's full size."""
        out = _backdrop(picture, self.frame)
        w = min(self.full[0], int(self.base[0] * (1 + grow)) // 2 * 2)
        h = min(self.full[1], int(self.base[1] * (1 + grow)) // 2 * 2)
        if (w, h) != picture.size:
            picture = picture.resize((w, h), Image.BICUBIC)
        x0, y0, x1, y1 = self.box
        out.paste(picture, ((x0 + x1 - w) // 2, (y0 + y1 - h) // 2))
        return out


class ClipMixin:
    def picture_box(self) -> tuple[int, int, int, int] | None:
        """Where a picture that does not fill the frame goes; None = always fill the frame."""
        return None

    def render_clips(self, timeline: dict, media: list[tuple[Path | None, Path | None]], out_path: Path) -> None:
        """media: (clip, image) per scene of the timeline; either may be None."""
        W, H, fps = self.W, self.H, self.fps
        spans, cues, total = timeline["scenes"], timeline["cues"], timeline["duration"]
        cmd = [ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{self.out_size[0]}x{self.out_size[1]}",
               "-r", str(fps), "-i", "-", "-i", str(timeline["audio"]),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out_path)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        n_frames = int(math.ceil(total * fps))
        f, ci = 0, 0
        try:
            for i, span in enumerate(spans):
                end_frame = n_frames if i == len(spans) - 1 else int(round(span["end"] * fps))
                count = max(0, end_frame - f)
                clip, image = media[i]
                slow = playback_speed(count / fps, clip_duration(clip)) if clip else 1.0
                source = clip or image
                box = self.picture_box()
                fitted = None
                if source and box and needs_fit(media_size(source), (W, H)):
                    fitted = _Fitted(box, (W, H), media_size(source), HOLD_ZOOM if clip else STILL_ZOOM)
                size = fitted.base if fitted else (W, H)
                frames = _ClipFrames(clip, size, fps, slow, cover=not fitted) if clip else None
                still = None
                if image and not clip:
                    still = Image.open(image).convert("RGB")
                    still = still.resize(size, Image.LANCZOS) if fitted else _cover(still, (W, H))
                last, held_from = None, None
                for k in range(count):
                    frame = frames.next() if frames else None
                    zoom = 0.0
                    if frame is not None:
                        last = frame
                    elif last is not None:      # clip ran out: hold its last frame with a slow push-in
                        held_from = k if held_from is None else held_from
                        frame, zoom = last, HOLD_ZOOM * (k - held_from) / max(1, count - held_from)
                    elif still is not None:
                        frame, zoom = still, STILL_ZOOM * k / max(1, count)
                    if frame is None:
                        frame = Image.new("RGB", (W, H), (0, 0, 0))
                    elif fitted:
                        frame = fitted.compose(frame, zoom)
                    else:
                        frame = _push_in(frame, zoom)
                    frame = frame.copy()
                    frame.paste(self.overlay, (0, 0), self.overlay)
                    t = f / fps
                    while ci < len(cues) and t > cues[ci]["end"]:
                        ci += 1
                    cue = cues[ci] if ci < len(cues) and cues[ci]["start"] <= t else None
                    frame = self._finish(frame, cue, t, total)
                    ff.stdin.write(frame.tobytes())
                    f += 1
                    if f % (fps * 10) == 0:
                        print(f"  render {t:5.1f}s / {total:.1f}s")
                if frames:
                    frames.close()
                if clip and slow >= MAX_SLOW and count / fps > clip_duration(clip) * MAX_SLOW + 1:
                    print(f"  note: scene {i + 1} narration is {count / fps:.0f}s; its clip covers "
                          f"{clip_duration(clip) * MAX_SLOW:.0f}s, the rest holds the last frame")
        finally:
            ff.stdin.close()
            ff.wait()
        if ff.returncode != 0:
            raise RuntimeError("ffmpeg failed")


class ClipRenderer(ClipMixin, Renderer):
    """Landscape (or, for 9:16 visuals, portrait) video with the normal badge and subtitle band."""


class ShortClipRenderer(ClipMixin, SafeShortRenderer):
    """9:16 Short with title, big subtitles and end card over the clips. A 16:9 clip is shown whole between the
    title and the subtitles (see the module docstring), never cropped to fill the frame."""
    sub_top = 0.585  # just under a full-width 16:9 picture

    def picture_box(self) -> tuple[int, int, int, int]:
        gap = int(self.H * 0.012)
        return 0, int(self.title_bottom) + gap, self.W, int(self.H * self.sub_top) - gap


def scene_media(project: Path, visuals: dict, indices: list[int]) -> list[tuple[Path | None, Path | None]]:
    out = []
    for i in indices:
        s = visuals["scenes"][i]
        clip = project / s["clip"] if s["clip"] and (project / s["clip"]).is_file() else None
        image = project / s["image"] if s["image"] and (project / s["image"]).is_file() else None
        out.append((clip, image))
    return out
