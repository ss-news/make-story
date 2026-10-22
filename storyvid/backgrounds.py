"""Step 3: one background image per bg_id (AI image if FAL_KEY is set, else a procedural misty scene)."""
import hashlib
import json
import math
import os
import random
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

PROCEDURAL_VERSION = 2  # bump when the procedural drawing changes, so cached images are redrawn

PALETTES = {
    # sky top, sky bottom, far hills, near ground, fog
    "night": ((14, 20, 38), (48, 62, 84), (36, 46, 62), (16, 20, 26), (170, 185, 200)),
    "dusk": ((52, 40, 66), (176, 128, 112), (88, 70, 84), (34, 28, 34), (220, 196, 186)),
    "river": ((40, 58, 66), (128, 150, 150), (70, 88, 90), (28, 38, 40), (200, 212, 210)),
    "forest": ((34, 48, 40), (120, 140, 118), (58, 76, 60), (22, 30, 24), (196, 208, 196)),
    "day": ((120, 136, 140), (206, 210, 200), (126, 136, 128), (70, 72, 64), (232, 232, 226)),
}
KEYWORDS = [
    ("night", ("night", "midnight", "moon", "dark", "đêm")),
    ("dusk", ("dusk", "sunset", "evening", "chiều", "hoàng hôn")),
    ("river", ("river", "water", "lake", "pond", "sông", "ao", "hồ")),
    ("forest", ("forest", "bamboo", "jungle", "tree", "rừng", "tre")),
]


def _palette(prompt: str):
    low = prompt.lower()
    for name, keys in KEYWORDS:
        if any(k in low for k in keys):
            return name, PALETTES[name]
    return "day", PALETTES["day"]


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _procedural(prompt: str, seed: str, size: tuple[int, int]) -> Image.Image:
    w, h = size
    rnd = random.Random(seed)
    name, (sky_top, sky_bot, hills, ground, fog) = _palette(prompt)
    img = Image.new("RGB", size)
    d = ImageDraw.Draw(img)
    for y in range(h):
        d.line([(0, y), (w, y)], fill=_lerp(sky_top, sky_bot, min(1, y / (h * 0.75))))
    if name == "night":
        mx, my, r = int(w * rnd.uniform(0.6, 0.85)), int(h * 0.18), int(h * 0.06)
        d.ellipse([mx - r, my - r, mx + r, my + r], fill=(226, 226, 210))

    def ridge(base, amp, color, freq):
        phase = rnd.uniform(0, 6.28)
        pts = [(x, base + amp * math.sin(x / w * freq * 6.28 + phase) + amp * 0.4 * math.sin(x / w * freq * 17 + phase))
               for x in range(0, w + 8, 8)]
        d.polygon(pts + [(w, h), (0, h)], fill=color)

    ridge(h * 0.55, h * 0.05, _lerp(hills, sky_bot, 0.45), 1.3)
    ridge(h * 0.63, h * 0.04, hills, 2.1)
    # tree / bamboo silhouettes
    for _ in range(rnd.randint(10, 18)):
        x = rnd.uniform(0, w)
        base = h * rnd.uniform(0.62, 0.72)
        th = h * rnd.uniform(0.12, 0.35)
        if "bamboo" in prompt.lower() or name == "forest":
            for k in range(3):
                bx = x + k * 6
                d.line([(bx, base), (bx + rnd.uniform(-20, 20), base - th)], fill=ground, width=max(2, w // 400))
        else:
            d.polygon([(x - th * 0.25, base), (x, base - th), (x + th * 0.25, base)], fill=_lerp(ground, hills, 0.3))
    if any(k in prompt.lower() for k in dict(KEYWORDS)["river"]):
        d.rectangle([0, h * 0.74, w, h], fill=_lerp(sky_bot, hills, 0.5))
        for _ in range(40):
            y = rnd.uniform(h * 0.76, h)
            x = rnd.uniform(0, w)
            d.line([(x, y), (x + rnd.uniform(20, 80), y)], fill=_lerp(sky_bot, (255, 255, 255), 0.3), width=2)
    else:
        ridge(h * 0.78, h * 0.02, ground, 3.0)
    # fog: soft blurred blobs
    fog_layer = Image.new("RGBA", size, (0, 0, 0, 0))
    fd = ImageDraw.Draw(fog_layer)
    for _ in range(26):
        cx, cy = rnd.uniform(-0.1, 1.1) * w, rnd.uniform(0.45, 0.9) * h
        rx, ry = rnd.uniform(0.15, 0.4) * w, rnd.uniform(0.03, 0.08) * h
        fd.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=fog + (rnd.randint(40, 90),))
    fog_layer = fog_layer.filter(ImageFilter.GaussianBlur(h * 0.04))
    img = Image.alpha_composite(img.convert("RGBA"), fog_layer).convert("RGB")
    return img.filter(ImageFilter.GaussianBlur(1.2))


def _fal_flux(prompt: str, key: str, path: Path) -> None:
    body = json.dumps({"prompt": prompt, "image_size": "landscape_16_9", "num_inference_steps": 4}).encode()
    req = urllib.request.Request(
        "https://fal.run/fal-ai/flux/schnell",
        data=body,
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        url = json.load(r)["images"][0]["url"]
    with urllib.request.urlopen(url, timeout=120) as r:
        path.write_bytes(r.read())


def _codex(prompt: str, path: Path) -> None:
    """Generate with the Codex CLI's built-in $imagegen skill (billed to the ChatGPT plan).

    Codex saves images under $CODEX_HOME/generated_images; we pick up the newest new file.
    """
    gen_dir = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "generated_images"
    exts = {".png", ".jpg", ".jpeg", ".webp"}
    listing = lambda: {p for p in gen_dir.rglob("*") if p.suffix.lower() in exts} if gen_dir.exists() else set()  # noqa: E731
    before = listing()
    request = (f"$imagegen Generate exactly one wide landscape image (16:9, no text, no people). "
               f"Do not edit any files. Image description: {prompt}")
    result = subprocess.run([os.environ.get("CODEX_BIN", "codex"), "exec", "--skip-git-repo-check", request],
                            capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"codex exec failed: {result.stderr[-800:]}")
    new = sorted(listing() - before, key=lambda p: p.stat().st_mtime)
    if not new:
        raise RuntimeError(f"codex produced no image in {gen_dir}")
    Image.open(new[-1]).convert("RGB").save(path)


def _image_provider() -> str:
    provider = os.environ.get("IMAGE_PROVIDER", "").strip().lower()
    if provider:
        return provider
    return "fal" if os.environ.get("FAL_KEY") else "procedural"


def make_backgrounds(script: dict, style_prompt: str, size: tuple[int, int], cache_dir: Path) -> dict:
    """Returns {bg_id: path}. Images are cached by prompt hash so reruns cost nothing."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    provider = _image_provider()
    tag = provider if provider != "procedural" else f"proc{PROCEDURAL_VERSION}"
    paths = {}
    for scene in script["scenes"]:
        bg_id = scene["bg_id"]
        if bg_id in paths:
            continue
        prompt = f"{scene['bg_prompt']}, {style_prompt}"
        digest = hashlib.sha1(f"{prompt}|{tag}".encode()).hexdigest()[:12]
        path = cache_dir / f"{bg_id}_{digest}.png"
        if not path.exists():
            try:
                if provider == "fal":
                    _fal_flux(prompt, os.environ["FAL_KEY"], path)
                elif provider == "codex":
                    _codex(prompt, path)
                else:
                    _procedural(prompt, digest, size).save(path)
                print(f"  background {bg_id}: {provider}")
            except Exception as e:  # network/quota problems should not kill the render
                print(f"  background {bg_id}: {provider} failed ({e}), using procedural for this run")
                path = cache_dir / f"{bg_id}_{digest}_fallback.png"
                _procedural(prompt, digest, size).save(path)
        paths[bg_id] = path
    return paths
