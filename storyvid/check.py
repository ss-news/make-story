"""Check scripts and assets against the shared contract (docs/pipeline.md).

  python -m storyvid.check output/<id>/scenes.json   script: exit 0 ok, 1 errors, 2 assets missing
                                                      (writes asset_requests.json next to the script)
  python -m storyvid.check --assets                   asset pack, base + extra: exit 0 ok, 1 errors
  python -m storyvid.check --review output/<id>/review.json   QA report: exit 0 ok, 1 errors
  python -m storyvid.check --visuals output/<id>/visuals.json Muse image/clip plan: exit 0 ok, 1 errors
  python -m storyvid.check --write-schema             regenerate schema/*.json after changing the pack
"""
import argparse
import json
import re
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

from . import contract, pack

VIEWBOX = {"backgrounds": "0 0 1600 900", "animals": "0 0 480 360", "props": "0 0 480 360",
           "effects": "0 0 480 360"}
PNG_SIZE = {"backgrounds": ((1920, 1080), "RGB"), "animals": ((960, 720), "RGBA"), "props": ((960, 720), "RGBA"),
            "effects": ((960, 720), "RGBA")}
CHARACTER_FIELDS = {"id": str, "label": str, "female": bool, "age": str, "scale": (int, float), "skin": str,
                    "hair": str}
AGES = ("child", "young", "middle", "elder")


def check_script(path: Path) -> int:
    script = json.loads(path.read_text(encoding="utf-8"))
    errors, requests = contract.validate(script)
    requests_path = path.parent / "asset_requests.json"
    for e in errors:
        print(f"ERROR {e}")
    if requests:
        doc = contract.request_file(requests, path)
        requests_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        for r in requests:
            print(f"MISSING {r['group']}/{r['id']} (scenes {r['scenes']}) -> {requests_path}")
    elif requests_path.exists():
        requests_path.unlink()  # everything it asked for exists now
    if errors:
        return 1
    if requests:
        return 2
    print(f"OK {path}")
    return 0


def asset_problems() -> list[str]:
    """Every problem in the merged manifests: missing files, wrong canvas, duplicate ids, bad characters."""
    pack.reload()
    problems, seen = [], set()
    for item in pack.manifest()["assets"]:
        where = f"{item.get('group')}/{item.get('id')}"
        if item.get("group") not in pack.GROUPS:
            problems.append(f"{where}: group must be one of {', '.join(pack.GROUPS)}")
            continue
        pattern = contract.BG_SLUG if item["group"] == "backgrounds" else contract.SLUG
        if not re.fullmatch(pattern, str(item.get("id"))):
            problems.append(f"{where}: id does not match {pattern}")
        if item["id"] in seen:
            problems.append(f"{where}: id used twice")
        seen.add(item["id"])
        if not item.get("label"):
            problems.append(f"{where}: missing label")
        if item["group"] == "animals" and pack.facing(item["id"]) not in (-1, 1):
            problems.append(f"{where}: animals need facing -1 (looks left) or 1 (looks right)")
        if item["group"] in ("animals", "props") and Path(item["root"]) == pack.EXTRA:
            low, high = pack.HEIGHT_RANGE
            h = item.get("height")
            if not isinstance(h, (int, float)) or isinstance(h, bool) or not low <= h <= high:
                problems.append(f"{where}: needs height between {low} and {high} (share of the frame height; "
                                "a character is 0.54)")
        if ("svg" in item) == ("png" in item):
            problems.append(f"{where}: give exactly one of svg or png")
            continue
        path = pack.file_of(item)
        if not path.exists():
            problems.append(f"{where}: file not found {path}")
            continue
        if "svg" in item:
            try:
                root = ET.fromstring(path.read_text())
            except ET.ParseError as e:
                problems.append(f"{where}: invalid SVG ({e})")
                continue
            if root.get("viewBox") != VIEWBOX[item["group"]]:
                problems.append(f"{where}: viewBox must be {VIEWBOX[item['group']]!r}, got {root.get('viewBox')!r}")
        else:
            (size, mode) = PNG_SIZE[item["group"]]
            with Image.open(path) as img:
                if img.size != size or img.mode != mode:
                    problems.append(f"{where}: PNG must be {size[0]}x{size[1]} {mode}, got "
                                    f"{img.size[0]}x{img.size[1]} {img.mode}")
    problems += _character_problems(seen)
    return problems


def audio_problems() -> list[str]:
    """Every sound needs a file that decodes, a kind, a known licence and its source; CC-BY needs a credit."""
    from . import audio
    audio.reload()
    problems, seen = [], set()
    for item in audio.sounds():
        where = f"audio/{item.get('id')}"
        if not re.fullmatch(contract.SLUG, str(item.get("id"))):
            problems.append(f"{where}: id does not match {contract.SLUG}")
        if item.get("id") in seen:
            problems.append(f"{where}: id used twice")
        seen.add(item.get("id"))
        if item.get("kind") not in audio.KINDS:
            problems.append(f"{where}: kind must be one of {', '.join(audio.KINDS)}")
        if item.get("license") not in audio.LICENSES:
            problems.append(f"{where}: license must be one of {', '.join(audio.LICENSES)}")
        if item.get("license") == "CC-BY-4.0" and not item.get("attribution"):
            problems.append(f"{where}: CC-BY-4.0 needs an attribution line")
        for field in ("label", "source", "file"):
            if not item.get(field):
                problems.append(f"{where}: missing {field}")
        path = audio.AUDIO / str(item.get("file", ""))
        if item.get("file") and not path.is_file():
            problems.append(f"{where}: file not found {path}")
        elif item.get("file") and item.get("kind") in audio.KINDS:
            try:
                if not len(audio._decoded(item["id"])):
                    problems.append(f"{where}: file has no audio")
            except Exception as e:  # ffmpeg could not read it
                problems.append(f"{where}: cannot decode ({e})")
    return problems


def _character_problems(asset_ids: set) -> list[str]:
    from .character import Character
    reference = json.loads((pack.PACK / "characters" / "young_man" / "rig.json").read_text())["parts"]
    problems = []
    for c in pack.manifest()["extra_characters"]:
        where = f"characters/{c.get('id')}"
        bad = [k for k, t in CHARACTER_FIELDS.items() if not isinstance(c.get(k), t)]
        if bad:
            problems.append(f"{where}: missing or wrong type for {', '.join(bad)}")
            continue
        if c["age"] not in AGES:
            problems.append(f"{where}: age must be one of {', '.join(AGES)}")
        if (pack.PACK / "characters" / c["id"]).exists():
            problems.append(f"{where}: id clashes with a base preset")
        folder = pack.EXTRA / "characters" / c["id"]
        rig_path = folder / "rig.json"
        if not rig_path.exists():
            problems.append(f"{where}: {rig_path} not found")
            continue
        parts = json.loads(rig_path.read_text()).get("parts", {})
        missing = sorted(set(reference) - set(parts))
        if missing:
            problems.append(f"{where}: rig.json lacks parts {', '.join(missing)}")
        absent = [p["file"] for p in parts.values() if not (folder / p["file"]).exists()]
        if absent:
            problems.append(f"{where}: part files not found: {', '.join(absent)}")
        if missing or absent:
            continue
        try:
            Character({"preset": c["id"]}, 120).sprite("talk", "surprised", 2, False, True, 1)
        except Exception as e:  # any failure to compose is a broken rig
            problems.append(f"{where}: does not render ({e})")
    return problems


def check_assets() -> int:
    problems = asset_problems() + audio_problems()
    for p in problems:
        print(f"ERROR {p}")
    if problems:
        return 1
    stale = (not contract.CATALOG_PATH.exists()
             or json.loads(contract.CATALOG_PATH.read_text()) != json.loads(json.dumps(contract.catalog())))
    if stale:
        contract.write_reference_files()
        print(f"updated {contract.CATALOG_PATH.relative_to(contract.ROOT)}")
    print(f"OK {len(pack.manifest()['assets'])} assets, {len(pack.manifest()['extra_characters'])} extra characters")
    return 0


def check_review(path: Path) -> int:
    review = json.loads(path.read_text(encoding="utf-8"))
    scenes_path = contract.ROOT / str(review.get("scenes_file", "")) if isinstance(review, dict) else None
    count = None
    if scenes_path and scenes_path.is_file():
        count = len(json.loads(scenes_path.read_text(encoding="utf-8")).get("scenes", []))
    errors = contract.validate_review(review, count)
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        return 1
    print(f"OK {path}: {review['verdict']}, {len(review['issues'])} issue(s)")
    return 0


def check_visuals(path: Path) -> int:
    visuals = json.loads(path.read_text(encoding="utf-8"))
    scenes_path = path.parent / "scenes.json"
    script = json.loads(scenes_path.read_text(encoding="utf-8")) if scenes_path.is_file() else None
    errors = contract.validate_visuals(visuals, script, path.parent)
    for e in errors:
        print(f"ERROR {e}")
    if errors:
        return 1
    clips = sum(1 for s in visuals["scenes"] if s["clip"])
    print(f"OK {path}: {clips}/{len(visuals['scenes'])} clip(s)")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scenes", nargs="?", help="scenes.json to check")
    ap.add_argument("--assets", action="store_true", help="check the asset pack")
    ap.add_argument("--review", help="review.json (QA report) to check")
    ap.add_argument("--visuals", help="visuals.json (Muse images and clips) to check")
    ap.add_argument("--write-schema", action="store_true", help="regenerate schema/*.json")
    args = ap.parse_args()
    if args.write_schema:
        contract.write_reference_files()
        print(f"wrote {contract.SCHEMA_PATH.relative_to(contract.ROOT)}, {contract.CATALOG_PATH.relative_to(contract.ROOT)}")
    code = 0
    if args.assets:
        code = max(code, check_assets())
    if args.scenes:
        code = max(code, check_script(Path(args.scenes)))
    if args.review:
        code = max(code, check_review(Path(args.review)))
    if args.visuals:
        code = max(code, check_visuals(Path(args.visuals)))
    if not (args.scenes or args.assets or args.review or args.visuals or args.write_schema):
        ap.error("give a scenes.json, --assets, --review, --visuals or --write-schema")
    sys.exit(code)


if __name__ == "__main__":
    main()
