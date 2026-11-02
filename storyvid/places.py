"""Photos of real places a project shows (a house, a street), attached to the scene images that show them.

Stored in output/<id>/refs/places.json (schema storyvid.places/1), photos in output/<id>/refs/<place id>/:

    {"schema": "storyvid.places/1",
     "places": [{"id": "nha_300", "name": "Nhà 300 Kim Mã", "keywords": ["house", "gate"],
                 "scenes": [3], "skip": [12], "files": ["refs/nha_300/front.jpg"], "sources": ["https://..."]}]}

A scene uses a place when one of its keywords is a word in the scene's background or image prompt, or when the
scene number (1-based) is in "scenes"; never when it is in "skip". The photos only guide the building's shape:
the prompt asks Muse to redraw the place in the project's style, not to copy the photo.
"""
import io
import json
import re
import urllib.request
from pathlib import Path

from PIL import Image

SCHEMA = "storyvid.places/1"
MAX_PHOTOS = 1           # photos of one place attached to a scene image
MAX_DOWNLOAD = 15 * 1024 * 1024
PLACE_NOTE = ("The attached photo of {name} shows the real place. Keep its building shape, layout, materials and "
              "surroundings, but redraw it completely in the visual style above; do not copy the photo's realism, "
              "people, signs or text.")


def path(project: Path) -> Path:
    return project / "refs" / "places.json"


def load(project: Path) -> dict:
    try:
        data = json.loads(path(project).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return {"schema": SCHEMA, "places": [p for p in data.get("places", []) if isinstance(p, dict) and p.get("id")]}


def save(project: Path, data: dict) -> None:
    path(project).parent.mkdir(parents=True, exist_ok=True)
    path(project).write_text(json.dumps({"schema": SCHEMA, "places": data["places"]}, ensure_ascii=False, indent=2)
                             + "\n", encoding="utf-8")


def slug(text: str, taken: set[str]) -> str:
    import unicodedata
    base = unicodedata.normalize("NFKD", text.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")[:40] or "place"
    out, n = base, 2
    while out in taken:
        out, n = f"{base}_{n}", n + 1
    return out


def clean(place: dict) -> dict:
    """Normalise the fields a user can edit."""
    words = place.get("keywords", [])
    if isinstance(words, str):
        words = words.split(",")
    nums = lambda v: sorted({int(x) for x in (re.findall(r"\d+", v) if isinstance(v, str) else v or []) if int(x) > 0})  # noqa: E731
    return {**place, "name": str(place.get("name", "")).strip() or place["id"],
            "keywords": [w.strip().lower() for w in words if w.strip()],
            "scenes": nums(place.get("scenes")), "skip": nums(place.get("skip")),
            "files": [f for f in place.get("files", []) if isinstance(f, str)],
            "sources": [s for s in place.get("sources", []) if isinstance(s, str)]}


def scene_text(script: dict, visuals: dict | None, i: int) -> str:
    text = script["scenes"][i].get("bg_prompt", "")
    if visuals and i < len(visuals.get("scenes", [])):
        text += " " + visuals["scenes"][i].get("image_prompt", "")
    return text.lower()


def uses(place: dict, text: str, number: int) -> bool:
    if number in place.get("skip", []):
        return False
    if number in place.get("scenes", []):
        return True
    return any(re.search(r"\b" + re.escape(w) + r"s?\b", text) for w in place.get("keywords", []))


def scenes_of(place: dict, script: dict, visuals: dict | None = None) -> list[int]:
    """1-based numbers of the scenes that show this place."""
    return [i + 1 for i in range(len(script.get("scenes", []))) if uses(place, scene_text(script, visuals, i), i + 1)]


def for_scene(project: Path, script: dict, visuals: dict | None, i: int) -> list[tuple[str, list[Path]]]:
    """[(place name, photo paths)] for scene i (0-based), photos that exist only."""
    out, text = [], scene_text(script, visuals, i)
    for place in load(project)["places"]:
        photos = [project / f for f in place.get("files", []) if (project / f).is_file()][:MAX_PHOTOS]
        if photos and uses(place, text, i + 1):
            out.append((place.get("name") or place["id"], photos))
    return out


def add_photo(project: Path, place: dict, data: bytes, name: str) -> str:
    """Saves an uploaded or downloaded image as JPEG under refs/<place id>/ and returns its project-relative path."""
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception as e:
        raise ValueError(f"Not an image: {name}") from e
    image = image.convert("RGB")
    image.thumbnail((2048, 2048))
    folder = project / "refs" / place["id"]
    folder.mkdir(parents=True, exist_ok=True)
    stem = re.sub(r"[^a-z0-9]+", "-", Path(name).stem.lower()).strip("-")[:50] or "photo"
    target, n = folder / f"{stem}.jpg", 2
    while target.exists():
        target, n = folder / f"{stem}-{n}.jpg", n + 1
    image.save(target, "JPEG", quality=90)
    return target.relative_to(project).as_posix()


def download(url: str) -> tuple[bytes, str]:
    if not re.match(r"https?://", url):
        raise ValueError("Only http(s) links")
    req = urllib.request.Request(url, headers={"User-Agent": "storyvid/1.0 (reference photo)"})
    with urllib.request.urlopen(req, timeout=30) as res:
        data = res.read(MAX_DOWNLOAD + 1)
    if len(data) > MAX_DOWNLOAD:
        raise ValueError("Image larger than 15 MB")
    return data, url.split("?")[0].rstrip("/").rsplit("/", 1)[-1] or "photo"
