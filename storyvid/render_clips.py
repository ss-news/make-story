"""Render a script with Muse clips (visuals.json) instead of the stick-figure stage.

Each scene plays its clip under the scene's narration: the clip is slowed down a little when the narration is
longer (up to MAX_SLOW), then its last frame holds with a slow push-in. A scene with an image but no clip gets a
slow push-in on the image. Subtitles, channel badge and the Short chrome come from the normal renderers.
"""
import math
import re
import subprocess
from pathlib import Path

from PIL import Image

from .ffmpeg import ffmpeg_exe
from .render import Renderer, ShortRenderer

MAX_SLOW = 1.35   # play a clip at most this much slower to cover a long narration
HOLD_ZOOM = 0.06  # push-in while a clip's last frame holds, over the held time
STILL_ZOOM = 0.12 # push-in over a scene that only has an image


def clip_duration(path: Path) -> float:
    out = subprocess.run([ffmpeg_exe(), "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", out)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def playback_speed(scene_seconds: float, clip_seconds: float) -> float:
    """How much slower to play the clip: 1 (normal) up to MAX_SLOW."""
    if clip_seconds <= 0:
        return 1.0
    return max(1.0, min(MAX_SLOW, scene_seconds / clip_seconds))


class _ClipFrames:
    """Frames of one clip at the output size and fps, cover-cropped, optionally slowed down."""

    def __init__(self, path: Path, size: tuple[int, int], fps: int, slow: float):
        w, h = size
        vf = (f"setpts={slow:.4f}*PTS,fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase,"
              f"crop={w}:{h}")
        self.size = size
        self.proc = subprocess.Popen([ffmpeg_exe(), "-v", "error", "-i", str(path), "-an", "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)

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


class ClipMixin:
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
                frames = _ClipFrames(clip, (W, H), fps, slow) if clip else None
                still = _cover(Image.open(image).convert("RGB"), (W, H)) if image and not clip else None
                last, held_from = None, None
                for k in range(count):
                    frame = frames.next() if frames else None
                    if frame is not None:
                        last = frame
                    elif last is not None:      # clip ran out: hold its last frame with a slow push-in
                        held_from = k if held_from is None else held_from
                        frame = _push_in(last, HOLD_ZOOM * (k - held_from) / max(1, count - held_from))
                    elif still is not None:
                        frame = _push_in(still, STILL_ZOOM * k / max(1, count))
                    else:
                        frame = Image.new("RGB", (W, H), (0, 0, 0))
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


class ShortClipRenderer(ClipMixin, ShortRenderer):
    """9:16 Short with title, big subtitles and end card over the clips."""


def scene_media(project: Path, visuals: dict, indices: list[int]) -> list[tuple[Path | None, Path | None]]:
    out = []
    for i in indices:
        s = visuals["scenes"][i]
        clip = project / s["clip"] if s["clip"] and (project / s["clip"]).is_file() else None
        image = project / s["image"] if s["image"] and (project / s["image"]).is_file() else None
        out.append((clip, image))
    return out
