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
FONT_BANNER = "/System/Library/Fonts/Supplemental/Impact.ttf"
OVERSCAN = 1.15      # background is larger than the frame so the camera can move
MOVE_TIME = 0.9      # seconds to walk to a new position between scenes
ENTER_TIME = 1.3     # seconds to walk in from / out to the edge of the frame
APPROACH_TIME = 1.6  # seconds for "approach"
FADE_TIME = 0.35     # crossfade between different backgrounds
POS_X = {"far_left": 0.13, "left": 0.3, "center": 0.5, "right": 0.7, "far_right": 0.87}
GHOST_TINT = (205, 228, 238)
CHARACTER_HEIGHT = 0.54  # of the frame height
# Prop height as a share of the frame height (drawn part only); anything not listed uses the default
PROP_HEIGHT = {"buffalo": 0.26, "cow": 0.25, "pig": 0.18, "dog": 0.16, "cat": 0.13, "rooster": 0.16, "hen": 0.13,
               "duck": 0.12, "stork": 0.24, "bamboo_fence": 0.22, "water_jar": 0.17, "carrying_pole": 0.2,
               "bamboo_stool": 0.1, "basket": 0.11, "winnowing_tray": 0.12, "rice_bundle": 0.16, "broom": 0.24,
               "hoe": 0.26, "fish_trap": 0.16, "oil_lamp": 0.12, "lotus": 0.12}
PROP_DEFAULT = 0.13
# Which way each pack animal looks in its SVG; objects are never mirrored
ANIMAL_FACING = {"buffalo": -1, "cow": -1, "pig": -1, "dog": -1, "cat": -1,
                 "rooster": 1, "hen": 1, "duck": 1, "stork": 1}
# Comic marks drawn around the head for an expression
EXPRESSION_EFFECT = {"surprised": "surprise", "angry": "anger", "scared": "sweat"}


def _font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size)


def _ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


class Renderer:
    def __init__(self, channel: dict, size: tuple[int, int], fps: int):
        self.channel = channel
        self.W, self.H = size
        self.fps = fps
        self.band_h = int(self.H * 0.11)
        self.top_h = int(self.H * 0.085)
        self.overlay = self._chrome()
        self.sub_font = _font(FONT_BOLD, int(self.H * 0.045))
        self._sub_cache = {}
        self._bg_cache = {}

    # ---------- static layers ----------
    def _chrome(self) -> Image.Image:
        """Top banner, bottom subtitle band, logo and a vignette, drawn once."""
        W, H = self.W, self.H
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        # vignette
        vig = Image.new("L", (W, H), 0)
        vd = ImageDraw.Draw(vig)
        steps = 24
        for i in range(steps):
            a = int(110 * (1 - i / steps) ** 2)
            inset = int(i * min(W, H) * 0.012)
            vd.rectangle([inset, inset, W - inset, H - inset], outline=a, width=int(min(W, H) * 0.012) + 1)
        img.paste((0, 0, 0, 255), (0, 0), vig)
        # top banner: red slanted block + dark block
        d.rectangle([0, 0, W, self.top_h], fill=(18, 18, 20, 255))
        split = int(W * 0.52)
        d.polygon([(0, 0), (split, 0), (split - self.top_h, self.top_h), (0, self.top_h)], fill=(178, 22, 30, 255))
        f = _font(FONT_BANNER, int(self.top_h * 0.78))
        y = self.top_h // 2
        d.text((split - self.top_h * 1.4, y), self.channel["banner_left"], font=f, fill=(20, 20, 20), anchor="rm")
        d.text((split + self.top_h * 0.4, y), self.channel["banner_right"], font=f, fill=(205, 30, 40), anchor="lm")
        # bottom subtitle band
        d.rectangle([0, H - self.band_h, W, H], fill=(10, 10, 12, 235))
        # round logo, top right
        r = int(H * 0.065)
        cx, cy = W - r - int(W * 0.02), self.top_h + r + int(H * 0.02)
        d.ellipse([cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4], fill=(20, 20, 20, 255))
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(160, 18, 26, 255))
        lf = _font(FONT_BANNER, int(r * 0.42))
        d.text((cx, cy - r * 0.22), self.channel["banner_left"], font=lf, fill=(240, 230, 220), anchor="mm")
        d.text((cx, cy + r * 0.26), self.channel["banner_right"], font=lf, fill=(240, 230, 220), anchor="mm")
        return img

    def _subtitle(self, text: str, speaker: str = "") -> Image.Image:
        key = (speaker, text)
        if key in self._sub_cache:
            return self._sub_cache[key]
        prefix = f"{speaker}: " if speaker else ""
        max_w = self.W * 0.86
        words, lines, cur = (prefix + text).split(), [], ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if self.sub_font.getlength(trial) > max_w and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        lines.append(cur)
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

    # ---------- per frame ----------
    def _camera(self, bg: Image.Image, camera: str, p: float) -> Image.Image:
        bw, bh = bg.size
        p = _ease(p)
        zoom = {"zoom_in": 1 + 0.10 * p, "zoom_out": 1.10 - 0.10 * p}.get(camera, 1.04)
        cw, ch = bw / OVERSCAN / zoom, bh / OVERSCAN / zoom  # zoom 1 = exactly one frame of the overscan
        free_x, free_y = bw - cw, bh - ch
        fx = {"pan_left": 1 - p, "pan_right": p}.get(camera, 0.5)
        x0, y0 = free_x * fx, free_y * 0.5
        return bg.resize((self.W, self.H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))

    # ---------- cast ----------
    def _setup_cast(self, script: dict) -> None:
        host = self.channel["host"]
        height = int(self.H * CHARACTER_HEIGHT)
        self.cast = {HOST: {"character": Character(resolve_character(host, script.get("character")), height),
                            "kind": "human", "name": host.get("name", "")}}
        for c in script.get("cast", []):
            choice = {k: c[k] for k in ("preset", "outfit", "accessory") if c.get(k)}
            self.cast[c["id"]] = {"character": Character(resolve_character(host, choice), height),
                                  "kind": c.get("kind", "human"), "name": c.get("name", c["id"])}
        self._ghost_cache = {}
        self._prop_cache = {}

    def _ghostly(self, aid: str, sprite: Image.Image, key) -> Image.Image:
        """Pale, see-through version that fades out toward the feet."""
        if (aid, key) not in self._ghost_cache:
            arr = np.asarray(sprite).astype(np.float32)
            tint = np.array(GHOST_TINT, dtype=np.float32)
            arr[..., :3] = arr[..., :3] * 0.4 + tint * 0.6
            fade = np.clip((1.0 - np.linspace(0, 1, arr.shape[0])) * 2.2, 0, 1) ** 0.8
            arr[..., 3] *= 0.62 * fade[:, None]
            self._ghost_cache[(aid, key)] = Image.fromarray(arr.astype(np.uint8), "RGBA")
        return self._ghost_cache[(aid, key)]

    def _prop(self, prop_id: str, flip: bool) -> Image.Image:
        key = (prop_id, flip)
        if key not in self._prop_cache:
            img = pack.trimmed(prop_id, 900)
            h = int(self.H * PROP_HEIGHT.get(prop_id, PROP_DEFAULT))
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
        target = POS_X[a["position"]]
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

        cmd = [ffmpeg_exe(), "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
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

                for pr in scene.get("props", []):
                    px = POS_X.get(pr["position"], 0.5)
                    toward_middle = 1 if px < 0.5 else -1  # animals look toward the middle of the frame
                    img = self._prop(pr["id"], flip=ANIMAL_FACING.get(pr["id"], toward_middle) != toward_middle)
                    left = min(max(0, int(px * W - img.width / 2)), W - img.width)  # keep it inside the frame
                    frame.paste(img, (left, int(char_bottom - img.height - H * 0.01)), img)

                actors = [a for a in scene["actors"] if a["id"] in self.cast]
                targets = {a["id"]: POS_X[a["position"]] for a in actors}
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
                frame.paste(self.overlay, (0, 0), self.overlay)

                while ci < len(cues) and t > cues[ci]["end"]:
                    ci += 1
                if ci < len(cues) and cues[ci]["start"] <= t:
                    sub = self._subtitle(cues[ci]["text"], cues[ci].get("speaker", ""))
                    frame.paste(sub, (0, H - self.band_h + (self.band_h - sub.height) // 2), sub)

                ff.stdin.write(frame.tobytes())
                if f % (fps * 10) == 0:
                    print(f"  render {t:5.1f}s / {total:.1f}s")
        finally:
            ff.stdin.close()
            ff.wait()
        if ff.returncode != 0:
            raise RuntimeError("ffmpeg failed")
