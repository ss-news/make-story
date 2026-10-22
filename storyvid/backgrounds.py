"""Step 3: one background image per bg_id, taken from the asset pack's 16 scenes."""
import hashlib
from pathlib import Path

from . import pack


def make_backgrounds(script: dict, size: tuple[int, int], cache_dir: Path) -> dict:
    """Returns {bg_id: path}: the pack scene matching each bg_id (see pack.match_background), rasterized once."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for scene in script["scenes"]:
        bg_id = scene["bg_id"]
        if bg_id in paths:
            continue
        name = pack.match_background(bg_id, scene.get("bg_prompt", ""))
        digest = hashlib.sha1((pack.PACK / "backgrounds" / f"{name}.svg").read_bytes()).hexdigest()[:12]
        path = cache_dir / f"pack_{name}_{size[1]}_{digest}.png"
        if not path.exists():
            pack.raster(name, size[1]).convert("RGB").save(path)
        if name != bg_id:
            print(f"  background {bg_id}: pack {name}")
        paths[bg_id] = path
    return paths
