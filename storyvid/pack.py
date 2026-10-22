"""The Bắc Bộ stick-figure asset pack: backgrounds, animals, props and effects as SVG."""
import io
import json
import re
from functools import lru_cache
from pathlib import Path

import resvg_py
from PIL import Image

PACK = Path(__file__).resolve().parents[1] / "assets" / "bac-bo-stick"
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


@lru_cache(maxsize=1)
def manifest() -> dict:
    return json.loads((PACK / "manifest.json").read_text())


def ids(*groups: str) -> list[str]:
    return [a["id"] for a in manifest()["assets"] if a["group"] in groups]


def labels(*groups: str) -> list[list[str]]:
    return [[a["id"], a["label"]] for a in manifest()["assets"] if a["group"] in groups]


def _svg(asset_id: str) -> str:
    item = next((a for a in manifest()["assets"] if a["id"] == asset_id), None)
    if item is None:
        raise KeyError(f"Unknown pack asset '{asset_id}'")
    return (PACK / item["svg"]).read_text()


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
    """RGBA image of an asset, `height` pixels tall, keeping its viewBox aspect ratio."""
    return _raster(asset_id, height).copy()


@lru_cache(maxsize=256)
def _raster(asset_id: str, height: int) -> Image.Image:
    svg = _svg(asset_id)
    x0, y0, w, h = map(float, re.search(r'viewBox="([^"]+)"', svg).group(1).split())
    width = round(height * w / h)
    data = resvg_py.svg_to_bytes(svg_string=svg, width=width * 2, height=height * 2)
    return Image.open(io.BytesIO(data)).convert("RGBA").resize((width, height), Image.Resampling.LANCZOS)


def trimmed(asset_id: str, height: int) -> Image.Image:
    """Like raster() but cropped to the drawn pixels, so the bottom edge sits on the ground."""
    img = _raster(asset_id, height)
    box = img.getchannel("A").getbbox()
    return img.crop(box) if box else img.copy()
