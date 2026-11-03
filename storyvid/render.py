"""Step 4: compose every frame (background + props + cast + effects + banner + subtitles) and encode with ffmpeg."""
import math
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import pack
from .character import Character
from .character_catalog import resolve_character
from .script import HOST, NARRATOR
from .ffmpeg import ffmpeg_exe
from .tts import SAMPLE_RATE

FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_BRAND = ("/System/Library/Fonts/Supplemental/ChalkboardSE.ttc", 2)  # (file, face index): Chalkboard SE Bold
ROOT = Path(__file__).resolve().parents[1]
INK = (36, 33, 31)
CREAM = (255, 253, 247)
OVERSCAN = 1.15      # background is larger than the frame so the camera can move
MOVE_TIME = 0.9      # seconds to walk to a new position between scenes
ENTER_TIME = 1.3     # seconds to walk in from / out to the edge of the frame
APPROACH_TIME = 1.6  # seconds for "approach"
FADE_TIME = 0.35     # crossfade between different backgrounds
POS_X = {"far_left": 0.13, "left": 0.3, "center": 0.5, "right": 0.7, "far_right": 0.87}
GHOST_TINT = (205, 228, 238)
CHARACTER_HEIGHT = 0.54  # of the frame height
# zoom_in / zoom_out scale the whole stage (cast included) toward the actors: (start, end) magnification
ZOOM = {"zoom_in": (1.12, 1.40), "zoom_out": (1.30, 1.0)}
CLOSE_UP_FILL = 0.6  # at the tightest point of a zoom the tallest actor should fill this much of the frame height
ZOOM_MAX = 1.8       # beyond this the upscaled frame gets visibly soft
# Comic marks drawn around the head for an expression
EXPRESSION_EFFECT = {"surprised": "surprise", "angry": "anger", "scared": "sweat"}


def _font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return ImageFont.load_default(size)


def _brand_font(size):
    path, index = FONT_BRAND
    font = _font(path, size, index)
    return font if isinstance(font, ImageFont.FreeTypeFont) else _font(FONT_BOLD, size)


def _vignette(img: Image.Image, strength: int) -> None:
    """Darken the edges of img in place."""
    W, H = img.size
    vig = Image.new("L", (W, H), 0)
    vd = ImageDraw.Draw(vig)
    steps = 24
    for i in range(steps):
        a = int(strength * (1 - i / steps) ** 2)
        inset = int(i * min(W, H) * 0.012)
        vd.rectangle([inset, inset, W - inset, H - inset], outline=a, width=int(min(W, H) * 0.012) + 1)
    img.paste((0, 0, 0, 255), (0, 0), vig)


def _badge(img: Image.Image, channel: dict, x: float, y: float, size: int, center: bool = False) -> None:
    """Channel badge drawn in place: round logo, then the channel name and tagline in hand lettering.
    (x, y) is the top-left corner, or the top-centre when center is True; size is the logo diameter."""
    d = ImageDraw.Draw(img)
    name_font, tag_font = _brand_font(int(size * 0.48)), _brand_font(int(size * 0.23))
    name, tagline = channel.get("channel_name", ""), channel.get("tagline", "")
    gap = size * 0.15
    width = size + gap + max(name_font.getlength(name), tag_font.getlength(tagline) if tagline else 0)
    left = x - width / 2 if center else x
    logo_path = ROOT / channel["logo"] if channel.get("logo") else None
    if logo_path and logo_path.exists():
        logo = Image.open(logo_path).convert("RGBA").resize((size, size), Image.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, size - 1, size - 1], fill=255)
        img.paste(logo, (int(left), int(y)), mask)
    else:
        gap, left = 0, left + size / 2  # no logo: text only, roughly centred where the logo would be
    tx = left + size + gap
    style = dict(fill=CREAM, stroke_fill=INK, anchor="lm")
    if tagline:
        d.text((tx, y + size * 0.36), name, font=name_font, stroke_width=max(2, size // 24), **style)
        d.text((tx + size * 0.03, y + size * 0.78), tagline, font=tag_font, stroke_width=max(1, size // 40), **style)
    else:
        d.text((tx, y + size / 2), name, font=name_font, stroke_width=max(2, size // 24), **style)


def _wrap(text: str, font, max_w: float) -> list[str]:
    lines, cur = [], ""
    for w in text.split():
        trial = f"{cur} {w}".strip()
        if font.getlength(trial) > max_w and cur:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    return lines + [cur] if cur else lines


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Renderer:
    """16:9 video: the stage fills the frame, with the channel badge top left and subtitles in a bottom band."""
    char_height = CHARACTER_HEIGHT  # of the stage height
    spread = 1.0                    # 1 = positions use the whole stage width, less pulls them to the middle
    sub_width = 0.86                # subtitle lines wrap at this much of the frame width

    def __init__(self, channel: dict, size: tuple[int, int], fps: int):
        self.channel = channel
        self.W, self.H = size  # the stage, where the scene is drawn
        self.out_size = size   # the encoded frame
        self.fps = fps
        self.band_h = int(self.H * 0.11)
        self.overlay = self._chrome()
        self.sub_font = _font(FONT_BOLD, int(self.H * 0.045))
        self._sub_cache = {}
        self._bg_cache = {}

    # ---------- static layers ----------
    def _chrome(self) -> Image.Image:
        """Vignette, channel badge and bottom subtitle band, drawn once."""
        W, H = self.W, self.H
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        _vignette(img, 110)
        _badge(img, self.channel, H * 0.035, H * 0.033, int(H * 0.11))
        d.rectangle([0, H - self.band_h, W, H], fill=(10, 10, 12, 235))
        return img

    def _subtitle(self, text: str, speaker: str = "") -> Image.Image:
        key = (speaker, text)
        if key in self._sub_cache:
            return self._sub_cache[key]
        prefix = f"{speaker}: " if speaker else ""
        lines = _wrap(prefix + text, self.sub_font, self.W * self.sub_width) or [""]
        lh = int(self.sub_font.size * 1.2)
        img = Image.new("RGBA", (self.W, lh * len(lines) + 8), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        style = dict(font=self.sub_font, anchor="lm", stroke_width=2, stroke_fill=(0, 0, 0))
        for i, ln in enumerate(lines):
            x0 = (self.W - self.sub_font.getlength(ln)) / 2
            y = 4 + i * lh + lh / 2
            d.text((x0, y), ln, fill=(245, 245, 245), **style)
            if i == 0 and prefix:  # speaker name in yellow over the start of the first line
                d.text((x0, y), prefix.strip(), fill=(255, 204, 72), **style)
        self._sub_cache[key] = img
        return img

    def _bg(self, path: Path) -> Image.Image:
        if path not in self._bg_cache:
            bw, bh = int(self.W * OVERSCAN), int(self.H * OVERSCAN)
            img = Image.open(path).convert("RGB")
            # cover-fit to the overscan size
            scale = max(bw / img.width, bh / img.height)
            img = img.resize((math.ceil(img.width * scale), math.ceil(img.height * scale)), Image.LANCZOS)
            left, top = (img.width - bw) // 2, (img.height - bh) // 2
            self._bg_cache[path] = img.crop((left, top, left + bw, top + bh))
        return self._bg_cache[path]

    def _x(self, position: str) -> float:
        return 0.5 + (POS_X.get(position, 0.5) - 0.5) * self.spread

    def _finish(self, frame: Image.Image, cue: dict | None, t: float, total: float) -> Image.Image:
        """Last step of a frame: the subtitle in the bottom band."""
        if cue:
            sub = self._subtitle(cue["text"], cue.get("speaker", ""))
            frame.paste(sub, (0, self.H - self.band_h + (self.band_h - sub.height) // 2), sub)
        return frame

    # ---------- per frame ----------
    def _camera(self, bg: Image.Image, camera: str, p: float) -> Image.Image:
        """The background for this moment: pans move across the overscan; zooms happen later, on the whole stage."""
        bw, bh = bg.size
        p = _ease(p)
        zoom = 1.04
        cw, ch = bw / OVERSCAN / zoom, bh / OVERSCAN / zoom  # zoom 1 = exactly one frame of the overscan
        free_x, free_y = bw - cw, bh - ch
        fx = {"pan_left": 1 - p, "pan_right": p}.get(camera, 0.5)
        x0, y0 = free_x * fx, free_y * 0.5
        return bg.resize((self.W, self.H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

    def _drawn_box(self, sprite: Image.Image) -> tuple[int, int, int, int]:
        """Where the figure is actually drawn inside a sprite canvas (cached per sprite object)."""
        key = id(sprite)
        if key not in self._box_cache:
            self._box_cache[key] = (sprite, sprite.getchannel("A").getbbox() or (0, 0, *sprite.size))
        return self._box_cache[key][1]

    def _focus(self, actor_boxes: list, prop_boxes: list) -> tuple[float, float]:
        """Close-ups aim at the upper part of the actors as drawn (so short ghosts are not left at the bottom),
        else at the props, else at the middle of the stage."""
        boxes = actor_boxes or prop_boxes
        if not boxes:
            return self.W / 2, self.H / 2
        x0, y0 = min(b[0] for b in boxes), min(b[1] for b in boxes)
        x1, y1 = max(b[2] for b in boxes), max(b[3] for b in boxes)
        return (x0 + x1) / 2, y0 + (y1 - y0) * (0.4 if actor_boxes else 0.5)

    def _zoom(self, frame: Image.Image, camera: str, p: float, focus: tuple[float, float],
              actor_boxes: list = ()) -> Image.Image:
        """Magnify the composed stage around focus (pixels), so a zoom_in becomes a close-up of the actors.
        Small figures (a child, a kneeling ghost) get a stronger close-up, up to ZOOM_MAX."""
        if camera not in ZOOM:
            return frame
        start, end = ZOOM[camera]
        if actor_boxes:
            tallest = max(b[3] - b[1] for b in actor_boxes)
            boost = min(ZOOM_MAX / max(start, end), max(1.0, CLOSE_UP_FILL * self.H / max(1, tallest) / max(start, end)))
            start, end = start * boost, end * boost
        z = start + (end - start) * _ease(p)
        cw, ch = self.W / z, self.H / z
        x0 = min(max(0.0, focus[0] - cw / 2), self.W - cw)
        y0 = min(max(0.0, focus[1] - ch / 2), self.H - ch)
        return frame.resize((self.W, self.H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

    # ---------- cast ----------
    def _setup_cast(self, script: dict) -> None:
        host = self.channel["host"]
        height = int(self.H * self.char_height)
        self.cast = {HOST: {"character": Character(resolve_character(host, script.get("character")), height),
                            "kind": "human", "name": host.get("name", "")}}
        for c in script.get("cast", []):
            choice = {k: c[k] for k in ("preset", "outfit", "accessory") if c.get(k)}
            self.cast[c["id"]] = {"character": Character(resolve_character(host, choice), height),
                                  "kind": c.get("kind", "human"), "name": c.get("name", c["id"])}
        self._ghost_cache = {}
        self._prop_cache = {}
        self._box_cache = {}

    def _ghostly(self, aid: str, sprite: Image.Image, key) -> Image.Image:
        """Pale, see-through version that fades out toward the feet; face and outline stay readable."""
        if (aid, key) not in self._ghost_cache:
            arr = np.asarray(sprite).astype(np.float32)
            tint = np.array(GHOST_TINT, dtype=np.float32)
            arr[..., :3] = arr[..., :3] * 0.6 + tint * 0.4
            # fade over the drawn figure, not the canvas: kneeling and child figures only fill its lower part
            rows = np.nonzero(arr[..., 3].max(axis=1) > 0)[0]
            top, bottom = (rows[0], rows[-1] + 1) if len(rows) else (0, arr.shape[0])
            fade = np.clip((1.0 - (np.arange(arr.shape[0]) - top) / max(1, bottom - top)) * 2.2, 0, 1) ** 0.8
            arr[..., 3] *= 0.85 * fade[:, None]
            self._ghost_cache[(aid, key)] = Image.fromarray(arr.astype(np.uint8), "RGBA")
        return self._ghost_cache[(aid, key)]

    def _prop(self, prop_id: str, flip: bool) -> Image.Image:
        key = (prop_id, flip)
        if key not in self._prop_cache:
            img = pack.trimmed(prop_id, 900)
            h = int(self.H * pack.height(prop_id) * self.char_height / CHARACTER_HEIGHT)
            img = img.resize((max(1, round(img.width * h / img.height)), h), Image.LANCZOS)
            self._prop_cache[key] = img.transpose(Image.FLIP_LEFT_RIGHT) if flip else img
        return self._prop_cache[key]

    def _effect(self, effect_id: str, height: int) -> Image.Image:
        key = (effect_id, height)
        if key not in self._prop_cache:
            self._prop_cache[key] = pack.raster(effect_id, height)
        return self._prop_cache[key]

    def _draw_effects(self, frame, a, info, sprite_pos, facing_left, since, walking, direction):
        """Surprise lines, sweat or anger marks at the head; dust behind walking feet."""
        name = "surprise" if a["action"] == "jump" and since < 1.2 else EXPRESSION_EFFECT.get(a["expression"])
        if info["kind"] == "ghost":
            name = None
        cx, cy = sprite_pos
        hx, hy, r = info["character"].head(facing_left)
        if name:
            pulse = 1 + 0.06 * math.sin(since * 2 * math.pi * 1.6)
            h = int(r * (3.2 if name == "surprise" else 1.5) * pulse)
            img = self._effect(name, h)
            if name == "surprise":  # lines spread on both sides of the head
                x, y = cx + hx - img.width / 2, cy + hy - img.height * 0.55
            else:  # a small mark beside the head, on the side away from where they look
                side = -1 if not facing_left else 1
                x, y = cx + hx - side * r * 1.15 - img.width / 2, cy + hy - r * 1.3 - img.height / 2
                if name == "sweat":
                    y += math.sin(since * math.pi) * r * 0.1
            frame.paste(img, (int(x), int(y)), img)
        if walking and info["kind"] != "ghost" and a["action"] in ("enter", "exit", "approach"):
            h = int(self.H * 0.06)
            img = self._effect("dust", h)
            sprite = info["character"]
            x = cx + sprite.width / 2 - direction * sprite.width * 0.35 - img.width / 2
            y = cy + sprite.height - img.height * 0.75
            frame.paste(img, (int(x), int(y)), img)

    def _actor_x(self, a: dict, prev_x: dict, since: float, dur: float, others: list) -> tuple[float, bool, int]:
        """Horizontal position at this moment, whether the actor is walking, and walk direction."""
        target = self._x(a["position"])
        edge = -0.12 if target < 0.5 else 1.12
        start = prev_x.get(a["id"], edge if a["action"] == "enter" else target)
        move = ENTER_TIME if a["action"] == "enter" and a["id"] not in prev_x else MOVE_TIME
        x = start + (target - start) * _ease(since / move)
        walking = start != target and since < move
        direction = 1 if target > start else -1
        if a["action"] == "approach" and others:
            near = min(others, key=lambda o: abs(o - target))
            shift = max(-0.12, min(0.12, (near - target) / 2.4))
            x += shift * _ease(since / APPROACH_TIME)
            if since < APPROACH_TIME and shift:
                walking, direction = True, 1 if shift > 0 else -1
        if a["action"] == "exit" and since > dur - ENTER_TIME:
            p = (since - (dur - ENTER_TIME)) / ENTER_TIME
            x += (edge - x) * _ease(p)
            walking, direction = True, 1 if edge > x else -1
        return x, walking, direction

    def render(self, script: dict, timeline: dict, bg_paths: dict, out_path: Path) -> None:
        W, H, fps = self.W, self.H, self.fps
        self._setup_cast(script)
        scenes = script["scenes"]
        prop_ids = set(pack.ids("animals", "props"))
        spans, cues = timeline["scenes"], timeline["cues"]
        total = timeline["duration"]
        n_frames = int(math.ceil(total * fps))

        # mouth openness from voice loudness, one value per frame
        samples = timeline["samples"].astype(np.float32)
        hop = SAMPLE_RATE / fps
        rms = np.array([
            np.sqrt(np.mean(chunk ** 2) + 1e-9) if len(chunk) else 0.0
            for i in range(n_frames)
            for chunk in [samples[int(i * hop):int((i + 1) * hop)]]
        ])
        ref = np.percentile(rms, 95) or 1.0
        level = rms / ref

        cmd = [ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{self.out_size[0]}x{self.out_size[1]}",
               "-r", str(fps), "-i", "-", "-i", str(timeline["audio"]),
               "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out_path)]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

        si, ci = 0, 0
        prev_x: dict = {}   # where each actor stood at the end of the previous scene
        last_x: dict = {}
        char_bottom = H - self.band_h + int(H * 0.01)
        try:
            for f in range(n_frames):
                t = f / fps
                while si < len(spans) - 1 and t >= spans[si]["end"]:
                    si += 1
                    prev_x = {k: v for k, v in last_x.items()
                              if not any(a["id"] == k and a["action"] == "exit" for a in scenes[si - 1]["actors"])}
                    last_x = {}
                scene, span = scenes[si], spans[si]
                dur = max(0.01, span["end"] - span["start"])
                since = t - span["start"]

                frame = self._camera(self._bg(bg_paths[scene["bg_id"]]), scene["camera"], since / dur)
                if si > 0 and scenes[si - 1]["bg_id"] != scene["bg_id"] and since < FADE_TIME:
                    prev = scenes[si - 1]
                    old = self._camera(self._bg(bg_paths[prev["bg_id"]]), prev["camera"], 1.0)
                    frame = Image.blend(old, frame, _ease(since / FADE_TIME))

                # who is talking right now (narration moves the host's mouth when the host is on stage)
                lines = span.get("lines") or [{"start": span["start"], "end": span["end"], "speaker": NARRATOR}]
                speaker = next((ln["speaker"] for ln in lines if ln["start"] <= t < ln["end"]), None)
                talking = HOST if speaker == NARRATOR else speaker

                prop_boxes, actor_boxes = [], []  # drawn areas, for aiming close-ups
                for pr in scene.get("props", []):
                    if pr["id"] not in prop_ids:
                        continue  # a requested asset that does not exist yet (only with --fallback)
                    px = self._x(pr["position"])
                    toward_middle = 1 if px < 0.5 else -1  # animals look toward the middle of the frame
                    looks = pack.facing(pr["id"])  # objects (None) are never mirrored
                    img = self._prop(pr["id"], flip=looks is not None and looks != toward_middle)
                    left = min(max(0, int(px * W - img.width / 2)), W - img.width)  # keep it inside the frame
                    top = int(char_bottom - img.height - H * 0.01)
                    frame.paste(img, (left, top), img)
                    prop_boxes.append((left, top, left + img.width, top + img.height))

                actors = [a for a in scene["actors"] if a["id"] in self.cast]
                targets = {a["id"]: self._x(a["position"]) for a in actors}
                placed = []
                for idx, a in enumerate(actors):
                    others = [v for k, v in targets.items() if k != a["id"]]
                    x, walking, direction = self._actor_x(a, prev_x, since, dur, others)
                    last_x[a["id"]] = x
                    placed.append((a, x, walking, direction))
                xs = {a["id"]: x for a, x, *_ in placed}

                # the speaker is drawn last so they are never hidden behind a listener
                for a, x, walking, direction in sorted(placed, key=lambda p: p[0]["id"] == talking):
                    info = self.cast[a["id"]]
                    ghost = info["kind"] == "ghost"
                    if walking:
                        facing_left = direction < 0
                    else:
                        if talking in xs and talking != a["id"]:
                            look_at = xs[talking]
                        else:
                            others = [v for k, v in xs.items() if k != a["id"]]
                            look_at = min(others, key=lambda o: abs(o - x)) if others else x
                        facing_left = look_at < x - 0.01
                    phase = t + sum(map(ord, a["id"])) % 7  # desync blinking and bobbing between actors
                    blink = (phase % 3.7) < 0.12
                    lv = level[f] if a["id"] == talking else 0
                    mouth = 2 if lv > 0.55 else 1 if lv > 0.18 else 0
                    step = int(t * 8) % 4 if walking and not ghost else None
                    key = (a["pose"], a["expression"], mouth, blink, facing_left, step)
                    sprite = info["character"].sprite(*key)
                    if ghost:
                        sprite = self._ghostly(a["id"], sprite, key)
                    bob = math.sin(phase * 2 * math.pi * 0.9) * H * 0.004
                    if walking and not ghost:
                        bob = -abs(math.sin(t * math.pi * 4)) * H * 0.012
                    if ghost:
                        bob = -H * 0.05 + math.sin(phase * 2 * math.pi * 0.5) * H * 0.015
                    if a["action"] == "jump" and since < 0.5:
                        bob -= math.sin(math.pi * since / 0.5) * H * 0.07
                    dx = math.sin(t * 45) * H * 0.004 if a["action"] == "shake" else 0
                    cx = int(x * W - sprite.width / 2 + dx)
                    cy = int(char_bottom - sprite.height + bob)
                    frame.paste(sprite, (cx, cy), sprite)
                    self._draw_effects(frame, a, info, (cx - dx, cy), facing_left, since, walking, direction)
                    box = self._drawn_box(sprite)
                    rest = int(char_bottom - sprite.height)  # without the bob, so the camera does not bounce
                    actor_boxes.append((cx + box[0], rest + box[1], cx + box[2], rest + box[3]))
                frame = self._zoom(frame, scene["camera"], since / dur, self._focus(actor_boxes, prop_boxes),
                                   actor_boxes)
                frame.paste(self.overlay, (0, 0), self.overlay)

                while ci < len(cues) and t > cues[ci]["end"]:
                    ci += 1
                cue = cues[ci] if ci < len(cues) and cues[ci]["start"] <= t else None
                frame = self._finish(frame, cue, t, total)

                ff.stdin.write(frame.tobytes())
                if f % (fps * 10) == 0:
                    print(f"  render {t:5.1f}s / {total:.1f}s")
        finally:
            ff.stdin.close()
            ff.wait()
        if ff.returncode != 0:
            raise RuntimeError("ffmpeg failed")


# Call to action shown at the end of a Short, by narration language
FULL_STORY = {"en": "Full story on the channel", "vi": "Xem bản đầy đủ trên kênh",
              "de": "Ganze Geschichte auf dem Kanal", "fr": "Histoire complète sur la chaîne",
              "es": "Historia completa en el canal"}
END_CARD_TIME = 3.0  # seconds


class ShortRenderer(Renderer):
    """9:16 Short: the stage fills the whole vertical frame; channel badge, title and big subtitles are drawn
    over it on dark gradients (no black bars)."""
    char_height = 0.42
    spread = 0.8

    def __init__(self, channel: dict, width: int, fps: int, title: str, lang: str):
        self.title = title
        super().__init__(channel, (width, round(width * 16 / 9) // 2 * 2), fps)
        self.band_h = int(self.H * 0.23)  # feet stand above the subtitle zone at the bottom of the picture
        self.sub_font = _font(FONT_BOLD, int(width * 0.06))
        self.end_text = FULL_STORY.get(lang, FULL_STORY["en"])

    def _chrome(self) -> Image.Image:
        """Vignette, top and bottom gradients, channel badge and title, drawn once over the stage."""
        W, H = self.W, self.H
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _vignette(img, 70)
        shade = Image.new("L", (1, H), 0)
        for y in range(H):
            top, bottom = 1 - y / (H * 0.2), (y - H * 0.7) / (H * 0.3)
            shade.putpixel((0, y), int(215 * max(0.0, min(1.0, max(top, bottom))) ** 1.2))
        img.paste((8, 8, 10, 255), (0, 0), shade.resize((W, H)))
        logo = int(W * 0.1)
        _badge(img, self.channel, W / 2, H * 0.02, logo, center=True)
        size = int(W * 0.065)  # shrink the title until it fits in two lines
        while True:
            font = _font(FONT_BOLD, size)
            lines = _wrap(self.title, font, W * 0.88)
            if len(lines) <= 2 or size <= W * 0.035:
                break
            size -= 2
        lh = int(font.size * 1.2)
        for i, ln in enumerate(lines[:2]):
            ImageDraw.Draw(img).text((W / 2, H * 0.03 + logo + lh * (i + 0.9)), ln, font=font, fill=(245, 240, 230),
                                     anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        return img

    def _finish(self, frame: Image.Image, cue: dict | None, t: float, total: float) -> Image.Image:
        zone_top = self.H - self.band_h
        if cue:
            sub = self._subtitle(cue["text"], cue.get("speaker", ""))
            frame.paste(sub, (0, zone_top + int(self.band_h * 0.2)), sub)
        if t > total - END_CARD_TIME:
            d = ImageDraw.Draw(frame)
            font = _font(FONT_BOLD, int(self.W * 0.05))
            tri = font.size * 0.7  # play triangle after the text (the font has no ▶ glyph)
            text_w = font.getlength(self.end_text)
            w = text_w + tri * 1.6 + self.W * 0.08
            cx, cy = self.W / 2, zone_top + self.band_h * 0.78
            h = font.size * 1.6
            d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h / 2, fill=(178, 22, 30))
            x0 = cx - (text_w + tri * 1.6) / 2
            d.text((x0, cy), self.end_text, font=font, fill=(255, 255, 255), anchor="lm")
            tx = x0 + text_w + tri * 0.6
            d.polygon([(tx, cy - tri / 2), (tx + tri * 0.9, cy), (tx, cy + tri / 2)], fill=(255, 255, 255))
        return frame


# Where TikTok, Reels and Shorts draw their own buttons and captions over a 9:16 video, as fractions of the frame.
# Badge, title, subtitles and the end card stay out of these; the picture may run under them.
SAFE_TOP = 0.07     # tabs and search at the top
SAFE_BOTTOM = 0.80  # caption, sound and progress bar below this line
SAFE_SIDE = 0.12    # like/comment/share column on the right (text is centred, so both sides keep this margin)


class SafeShortRenderer(ShortRenderer):
    """ShortRenderer with its text inside the apps' safe zone (SAFE_*): badge and title under the top bar,
    subtitles at sub_top, end card just above the caption zone. Used for Shorts made from Muse clips."""
    sub_width = 1 - 2 * SAFE_SIDE
    sub_top = 0.655  # subtitles start here

    def _chrome(self) -> Image.Image:
        """Vignette, top and bottom gradients, channel badge and title, drawn once over the picture."""
        W, H = self.W, self.H
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        _vignette(img, 70)
        logo = int(W * 0.1)
        size = int(W * 0.065)  # shrink the title until it fits in two lines
        while True:
            font = _font(FONT_BOLD, size)
            lines = _wrap(self.title, font, W * 0.88)
            if len(lines) <= 2 or size <= W * 0.035:
                break
            size -= 2
        lh = int(font.size * 1.2)
        top = H * SAFE_TOP
        self.title_bottom = top + logo + lh * (len(lines[:2]) + 0.3)
        shade = Image.new("L", (1, H), 0)
        fade_top, fade_bottom = self.title_bottom + H * 0.04, H * (self.sub_top - 0.05)
        for y in range(H):
            a = max(1 - y / fade_top, (y - fade_bottom) / (H - fade_bottom))
            shade.putpixel((0, y), int(215 * max(0.0, min(1.0, a)) ** 1.2))
        img.paste((8, 8, 10, 255), (0, 0), shade.resize((W, H)))
        _badge(img, self.channel, W / 2, top, logo, center=True)
        for i, ln in enumerate(lines[:2]):
            ImageDraw.Draw(img).text((W / 2, top + logo + lh * (i + 0.7)), ln, font=font, fill=(245, 240, 230),
                                     anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0))
        return img

    def _finish(self, frame: Image.Image, cue: dict | None, t: float, total: float) -> Image.Image:
        if cue:
            sub = self._subtitle(cue["text"], cue.get("speaker", ""))
            frame.paste(sub, (0, int(self.H * self.sub_top)), sub)
        if t > total - END_CARD_TIME:
            d = ImageDraw.Draw(frame)
            font = _font(FONT_BOLD, int(self.W * 0.05))
            tri = font.size * 0.7  # play triangle after the text (the font has no ▶ glyph)
            text_w = font.getlength(self.end_text)
            w = text_w + tri * 1.6 + self.W * 0.08
            h = font.size * 1.6
            cx, cy = self.W / 2, self.H * SAFE_BOTTOM - h / 2 - self.H * 0.012
            d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], radius=h / 2, fill=(178, 22, 30))
            x0 = cx - (text_w + tri * 1.6) / 2
            d.text((x0, cy), self.end_text, font=font, fill=(255, 255, 255), anchor="lm")
            tx = x0 + text_w + tri * 0.6
            d.polygon([(tx, cy - tri / 2), (tx + tri * 0.9, cy), (tx, cy + tri / 2)], fill=(255, 255, 255))
        return frame
