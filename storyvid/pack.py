"""The Bắc Bộ stick-figure asset pack: backgrounds, animals, props, effects and characters.

Two manifests are merged: the generated base pack (assets/bac-bo-stick/manifest.json, rewritten by
tools/build_bac_bo_assets.py) and hand-added assets (assets/bac-bo-stick/extra/manifest.json, never
touched by the builder). Each entry points at an SVG ("svg") or a PNG ("png") relative to its manifest.
"""
import io
import json
import re
from functools import lru_cache
from pathlib import Path

import resvg_py
from PIL import Image

PACK = Path(__file__).resolve().parents[1] / "assets" / "bac-bo-stick"
EXTRA = PACK / "extra"
GROUPS = ("backgrounds", "animals", "props", "effects")
# Words in a bg_id / bg_prompt that point at one of the pack's places, checked in order
PLACE_WORDS = [
    ("river", ("river", "song", "sông", "bến", "ben", "boat", "ferry", "ma_da")),
    ("pond", ("pond", "ao", "lake", "banyan", "đa", "well")),
    ("rice_fields", ("rice", "field", "paddy", "đồng", "dong", "ruộng")),
    ("market", ("market", "chợ", "cho", "stall", "shop")),
    ("communal_house", ("communal", "đình", "dinh", "temple", "pagoda", "chùa", "shrine")),
    ("interior", ("interior", "inside", "room", "house", "home", "kitchen", "bed", "nhà", "trong")),
    ("courtyard", ("courtyard", "yard", "sân", "san", "garden")),
    ("village_path", ("path", "road", "village", "đường", "lane", "gate")),
]
NIGHT_WORDS = ("night", "dark", "moon", "midnight", "dusk", "evening", "đêm", "dem", "tối", "khuya")
# Which way the base pack's animals look (-1 left, 1 right); extra entries carry their own "facing"
BASE_FACING = {"buffalo": -1, "cow": -1, "pig": -1, "dog": -1, "cat": -1,
               "rooster": 1, "hen": 1, "duck": 1, "stork": 1}

# On-screen height of the base pack's props and animals, as a share of the frame height (drawn part only,
# next to characters 0.54 tall); extra entries carry their own "height"
BASE_HEIGHT = {"buffalo": 0.26, "cow": 0.25, "pig": 0.18, "dog": 0.16, "cat": 0.13, "rooster": 0.16, "hen": 0.13,
               "duck": 0.12, "stork": 0.24, "bamboo_fence": 0.22, "water_jar": 0.17, "carrying_pole": 0.2,
               "bamboo_stool": 0.1, "basket": 0.11, "winnowing_tray": 0.12, "rice_bundle": 0.16, "broom": 0.24,
               "hoe": 0.26, "fish_trap": 0.16, "oil_lamp": 0.12, "lotus": 0.12}
DEFAULT_HEIGHT = 0.13
HEIGHT_RANGE = (0.03, 0.9)


@lru_cache(maxsize=1)
def manifest() -> dict:
    """Base and extra manifests merged; every asset gets "root", the folder its paths are relative to."""
    base = json.loads((PACK / "manifest.json").read_text())
    assets = [{**a, "root": str(PACK)} for a in base["assets"]]
    characters = []
    extra_path = EXTRA / "manifest.json"
    if extra_path.exists():
        extra = json.loads(extra_path.read_text())
        assets += [{**a, "root": str(EXTRA)} for a in extra.get("assets", [])]
        characters = extra.get("characters", [])
    return {**base, "assets": assets, "extra_characters": characters}


def reload() -> None:
    """Forget cached manifests and images, after an agent added assets."""
    manifest.cache_clear()
    _raster.cache_clear()


def entry(asset_id: str) -> dict:
    item = next((a for a in manifest()["assets"] if a["id"] == asset_id), None)
    if item is None:
        raise KeyError(f"Unknown pack asset '{asset_id}'")
    return item


def ids(*groups: str) -> list[str]:
    return [a["id"] for a in manifest()["assets"] if a["group"] in groups]


def labels(*groups: str) -> list[list[str]]:
    return [[a["id"], a["label"]] for a in manifest()["assets"] if a["group"] in groups]


def facing(asset_id: str) -> int | None:
    """-1 / 1 for animals (which way they look), None for objects that are never mirrored."""
    item = entry(asset_id)
    if "facing" in item:
        return item["facing"]
    return BASE_FACING.get(asset_id)


def height(asset_id: str) -> float:
    """On-screen height of a prop or animal as a share of the frame height."""
    item = entry(asset_id)
    return item.get("height") or BASE_HEIGHT.get(asset_id, DEFAULT_HEIGHT)


def character_dir(preset: str) -> Path:
    extra = EXTRA / "characters" / preset
    return extra if extra.exists() else PACK / "characters" / preset


def file_of(item: dict) -> Path:
    return Path(item["root"]) / (item.get("svg") or item["png"])


def match_background(bg_id: str, bg_prompt: str = "") -> str:
    """Pack background for a scene: the bg_id itself if it is one, else the closest place by keywords."""
    if bg_id in ids("backgrounds"):
        return bg_id
    text = f"{bg_id} {bg_prompt}".lower()
    words = set(re.split(r"[^\wÀ-ỹ]+", text))
    place = next((p for p, keys in PLACE_WORDS if any(k in words or (len(k) > 3 and k in text) for k in keys)),
                 "village_path")
    night = any(w in text for w in NIGHT_WORDS)
    return f"{place}_{'night' if night else 'day'}"


def raster(asset_id: str, height: int) -> Image.Image:
    """RGBA image of an asset, `height` pixels tall, keeping its aspect ratio."""
    return _raster(asset_id, height).copy()


@lru_cache(maxsize=256)
def _raster(asset_id: str, height: int) -> Image.Image:
    item = entry(asset_id)
    path = file_of(item)
    if "png" in item:
        img = Image.open(path).convert("RGBA")
        return img.resize((round(img.width * height / img.height), height), Image.Resampling.LANCZOS)
    svg = path.read_text()
    x0, y0, w, h = map(float, re.search(r'viewBox="([^"]+)"', svg).group(1).split())
    width = round(height * w / h)
    data = resvg_py.svg_to_bytes(svg_string=svg, width=width * 2, height=height * 2)
    return Image.open(io.BytesIO(data)).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)


def trimmed(asset_id: str, height: int) -> Image.Image:
    """Like raster() but cropped to the drawn pixels, so the bottom edge sits on the ground."""
    img = _raster(asset_id, height)
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img.copy()
