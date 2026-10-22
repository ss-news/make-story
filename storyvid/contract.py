"""The scenes.json contract every model and agent writes to: format "storyvid.scenes/1".

validate() is strict and fixes nothing: it returns the problems with their JSON path. Ids of backgrounds,
props or character presets that are well-formed but missing from the asset pack are not errors; they come
back as asset requests (format "storyvid.asset-requests/1") for the asset agent to draw.
See docs/pipeline.md for the whole flow.
"""
import json
import re
from pathlib import Path

from . import pack
from .character_catalog import ACCESSORIES, OUTFITS, PRESETS, validate_selection
from .script import ACTIONS, CAMERAS, EXPRESSIONS, HOST, KINDS, LANG_NAMES, NARRATOR, POSES, POSITIONS

FORMAT = "storyvid.scenes/1"
REQUESTS_FORMAT = "storyvid.asset-requests/1"
REVIEW_FORMAT = "storyvid.review/1"
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "scenes.v1.schema.json"
CATALOG_PATH = ROOT / "schema" / "assets.catalog.json"
REVIEW_SCHEMA_PATH = ROOT / "schema" / "review.v1.schema.json"
SLUG = r"^[a-z][a-z0-9_]*$"
BG_SLUG = r"^[a-z][a-z0-9_]*_(day|night)$"
MAX_ACTORS = 3
MAX_PROPS = 3
MAX_LINES = 6
# What the asset agent must deliver for each kind of request (paths relative to the project root)
ASSET_SPECS = {
    "backgrounds": {"file": "assets/bac-bo-stick/extra/backgrounds/{id}.svg", "viewBox": "0 0 1600 900",
                    "png_alternative": "assets/bac-bo-stick/extra/backgrounds/{id}.png, 1920x1080 RGB",
                    "rules": "No people, no text. Ground line between y=500 and y=560 so actors stand on the "
                             "lower third. Night versions use the same layout as the day version."},
    "props": {"file": "assets/bac-bo-stick/extra/props/{id}.svg", "viewBox": "0 0 480 360",
              "png_alternative": "assets/bac-bo-stick/extra/props/{id}.png, 960x720 RGBA, transparent",
              "rules": "Transparent background, object standing on its base, centred. If it is an animal, "
                       "use group 'animals', file assets/bac-bo-stick/extra/animals/{id}.svg, and set "
                       "'facing' (-1 looks left, 1 looks right)."},
    "characters": {"file": "assets/bac-bo-stick/extra/characters/{id}/rig.json + one SVG per part",
                   "rules": "Copy the folder of the closest existing preset, keep every part file name and the "
                            "rig anchors, then restyle. Register it under 'characters' in the extra manifest "
                            "with label, female, age (child|young|middle|elder), scale, skin, hair."},
}
TOP_KEYS = {"format", "title", "lang", "cast", "scenes"}
OPTIONAL_TOP_KEYS = {"character", "short"}
CAST_KEYS = {"id", "name", "preset", "outfit", "accessory", "kind"}
SCENE_KEYS = {"bg_id", "bg_prompt", "camera", "actors", "props", "lines"}
ACTOR_KEYS = {"id", "position", "pose", "expression", "action"}
PROP_KEYS = {"id", "position"}
LINE_KEYS = {"speaker", "text"}


def _keys(obj, wanted: set, where: str, errors: list, optional: set = frozenset()) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{where}: must be an object")
        return False
    missing = wanted - obj.keys()
    extra = obj.keys() - wanted - optional
    if missing:
        errors.append(f"{where}: missing {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"{where}: unknown field(s) {', '.join(sorted(extra))}")
    return not missing


def _enum(value, values, where: str, errors: list) -> None:
    if value not in values:
        errors.append(f"{where}: {value!r} is not one of {', '.join(values)}")


def _text(value, where: str, errors: list) -> None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: must be a non-empty string")


def _slug(value, pattern: str, where: str, errors: list) -> bool:
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        errors.append(f"{where}: {value!r} does not match {pattern}")
        return False
    return True


def validate(script) -> tuple[list[str], list[dict]]:
    """(errors, asset_requests). The script is renderable when both are empty."""
    errors: list[str] = []
    requests: dict[tuple, dict] = {}

    def request(group, asset_id, scene, description):
        key = (group, asset_id)
        if key not in requests:
            requests[key] = {"group": group, "id": asset_id, "description": description, "scenes": []}
        if scene is not None and scene not in requests[key]["scenes"]:
            requests[key]["scenes"].append(scene)

    if not _keys(script, TOP_KEYS, "$", errors, OPTIONAL_TOP_KEYS):
        return errors, []
    if script["format"] != FORMAT:
        errors.append(f"$.format: must be {FORMAT!r}")
    _text(script["title"], "$.title", errors)
    _enum(script["lang"], list(LANG_NAMES), "$.lang", errors)
    if "character" in script:
        try:
            validate_selection(script["character"])
        except ValueError as e:
            errors.append(f"$.character: {e}")

    if "short" in script:
        _validate_short(script["short"], script["scenes"], errors)

    cast_ids = set()
    if not isinstance(script["cast"], list):
        errors.append("$.cast: must be a list")
    else:
        for i, c in enumerate(script["cast"]):
            where = f"$.cast[{i}]"
            if not _keys(c, CAST_KEYS, where, errors):
                continue
            if _slug(c["id"], SLUG, f"{where}.id", errors):
                if c["id"] in cast_ids or c["id"] in (HOST, NARRATOR):
                    errors.append(f"{where}.id: {c['id']!r} is used twice or reserved")
                cast_ids.add(c["id"])
            _text(c["name"], f"{where}.name", errors)
            if _slug(c["preset"], SLUG, f"{where}.preset", errors) and c["preset"] not in PRESETS:
                request("characters", c["preset"], None, f"character preset for {c['name']}")
            _enum(c["outfit"], list(OUTFITS), f"{where}.outfit", errors)
            _enum(c["accessory"], list(ACCESSORIES), f"{where}.accessory", errors)
            _enum(c["kind"], KINDS, f"{where}.kind", errors)

    backgrounds = set(pack.ids("backgrounds"))
    props = set(pack.ids("animals", "props"))
    scenes = script["scenes"]
    if not isinstance(scenes, list) or not scenes:
        errors.append("$.scenes: must be a non-empty list")
        scenes = []
    for i, s in enumerate(scenes):
        where = f"$.scenes[{i}]"
        if not _keys(s, SCENE_KEYS, where, errors):
            continue
        if _slug(s["bg_id"], BG_SLUG, f"{where}.bg_id", errors) and s["bg_id"] not in backgrounds:
            request("backgrounds", s["bg_id"], i, s["bg_prompt"] if isinstance(s["bg_prompt"], str) else "")
        if not isinstance(s["bg_prompt"], str):
            errors.append(f"{where}.bg_prompt: must be a string")
        _enum(s["camera"], CAMERAS, f"{where}.camera", errors)

        on_stage = set()
        actors = s["actors"] if isinstance(s["actors"], list) else []
        if not isinstance(s["actors"], list) or len(actors) > MAX_ACTORS:
            errors.append(f"{where}.actors: must be a list of at most {MAX_ACTORS}")
        for j, a in enumerate(actors):
            aw = f"{where}.actors[{j}]"
            if not _keys(a, ACTOR_KEYS, aw, errors):
                continue
            if a["id"] not in cast_ids | {HOST}:
                errors.append(f"{aw}.id: {a['id']!r} is not in cast (or {HOST!r})")
            elif a["id"] in on_stage:
                errors.append(f"{aw}.id: {a['id']!r} is on stage twice")
            on_stage.add(a["id"])
            _enum(a["position"], POSITIONS, f"{aw}.position", errors)
            _enum(a["pose"], POSES, f"{aw}.pose", errors)
            _enum(a["expression"], EXPRESSIONS, f"{aw}.expression", errors)
            _enum(a["action"], ACTIONS, f"{aw}.action", errors)

        items = s["props"] if isinstance(s["props"], list) else []
        if not isinstance(s["props"], list) or len(items) > MAX_PROPS:
            errors.append(f"{where}.props: must be a list of at most {MAX_PROPS}")
        for j, p in enumerate(items):
            pw = f"{where}.props[{j}]"
            if not _keys(p, PROP_KEYS, pw, errors):
                continue
            if _slug(p["id"], SLUG, f"{pw}.id", errors) and p["id"] not in props:
                request("props", p["id"], i, "")
            _enum(p["position"], POSITIONS, f"{pw}.position", errors)

        lines = s["lines"] if isinstance(s["lines"], list) else []
        if not isinstance(s["lines"], list) or not 1 <= len(lines) <= MAX_LINES:
            errors.append(f"{where}.lines: must be a list of 1-{MAX_LINES} lines")
        for j, ln in enumerate(lines):
            lw = f"{where}.lines[{j}]"
            if not _keys(ln, LINE_KEYS, lw, errors):
                continue
            if ln["speaker"] != NARRATOR and ln["speaker"] not in on_stage - {HOST}:
                errors.append(f"{lw}.speaker: {ln['speaker']!r} must be {NARRATOR!r} or a cast id on stage")
            _text(ln["text"], f"{lw}.text", errors)
    return errors, list(requests.values())


REVIEW_KEYS = {"format", "scenes_file", "verdict", "issues"}
ISSUE_KEYS = {"scene", "area", "severity", "owner", "problem", "fix"}
VERDICTS = ["pass", "fix"]
AREAS = ["story", "dialogue", "staging", "background", "props", "character", "audio", "subtitle", "pacing",
         "render"]
SEVERITIES = ["blocker", "major", "minor"]
OWNERS = ["codex", "tool"]


def validate_review(review, scene_count: int | None = None) -> list[str]:
    """Problems in a QA report (review.json). A "pass" may only carry minor issues; a "fix" needs at least one."""
    errors: list[str] = []
    if not _keys(review, REVIEW_KEYS, "$", errors):
        return errors
    if review["format"] != REVIEW_FORMAT:
        errors.append(f"$.format: must be {REVIEW_FORMAT!r}")
    _text(review["scenes_file"], "$.scenes_file", errors)
    _enum(review["verdict"], VERDICTS, "$.verdict", errors)
    issues = review["issues"] if isinstance(review["issues"], list) else []
    if not isinstance(review["issues"], list):
        errors.append("$.issues: must be a list")
    for i, issue in enumerate(issues):
        where = f"$.issues[{i}]"
        if not _keys(issue, ISSUE_KEYS, where, errors):
            continue
        scene = issue["scene"]
        if scene is not None and (not isinstance(scene, int) or isinstance(scene, bool) or scene < 0
                                  or (scene_count is not None and scene >= scene_count)):
            errors.append(f"{where}.scene: must be null or a scene index (0-based)")
        _enum(issue["area"], AREAS, f"{where}.area", errors)
        _enum(issue["severity"], SEVERITIES, f"{where}.severity", errors)
        _enum(issue["owner"], OWNERS, f"{where}.owner", errors)
        _text(issue["problem"], f"{where}.problem", errors)
        _text(issue["fix"], f"{where}.fix", errors)
    serious = [x for x in issues if isinstance(x, dict) and x.get("severity") in ("blocker", "major")]
    if review["verdict"] == "pass" and serious:
        errors.append("$.verdict: 'pass' is not allowed with blocker or major issues")
    if review["verdict"] == "fix" and not issues:
        errors.append("$.verdict: 'fix' needs at least one issue")
    return errors


def review_schema() -> dict:
    enum = lambda values: {"type": "string", "enum": list(values)}  # noqa: E731
    string = {"type": "string", "minLength": 1}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": REVIEW_FORMAT,
        "title": "storyvid review.json (QA report)",
        "type": "object",
        "required": sorted(REVIEW_KEYS),
        "additionalProperties": False,
        "properties": {
            "format": {"const": REVIEW_FORMAT},
            "scenes_file": string,
            "verdict": {**enum(VERDICTS), "description": "pass: ready to publish (minor issues only); fix: send back."},
            "issues": {"type": "array", "items": {
                "type": "object", "required": sorted(ISSUE_KEYS), "additionalProperties": False,
                "properties": {
                    "scene": {"type": ["integer", "null"], "minimum": 0,
                              "description": "0-based scene index, null for the whole video."},
                    "area": enum(AREAS), "severity": enum(SEVERITIES),
                    "owner": {**enum(OWNERS), "description": "Who fixes it: codex (scenes.json, assets) or "
                                                              "tool (a bug in storyvid code)."},
                    "problem": string, "fix": string}}},
        },
    }


def _validate_short(short, scenes, errors: list) -> None:
    """short.scenes: the scenes cut into the 9:16 Short, by index, in story order."""
    if not _keys(short, {"scenes"}, "$.short", errors):
        return
    picked = short["scenes"]
    count = len(scenes) if isinstance(scenes, list) else 0
    if (not isinstance(picked, list) or not picked
            or not all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < count for i in picked)):
        errors.append(f"$.short.scenes: must be a non-empty list of scene indices (0-{count - 1})")
    elif picked != sorted(set(picked)):
        errors.append("$.short.scenes: indices must be increasing, without repeats")


def request_file(requests: list[dict], scenes_path: Path) -> dict:
    """The asset_requests.json document handed to the asset agent."""
    items = []
    for r in requests:
        spec = {k: v.replace("{id}", r["id"]) for k, v in ASSET_SPECS[r["group"]].items()}
        items.append({**r, "spec": spec})
    path = scenes_path.resolve()
    shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
    return {"format": REQUESTS_FORMAT, "scenes_file": str(shown), "requests": items}


def json_schema() -> dict:
    """JSON Schema of FORMAT for agents and models. Asset ids are patterns, not enums: an id that is
    not in the pack yet is allowed and becomes an asset request (see schema/assets.catalog.json)."""
    string = {"type": "string", "minLength": 1}
    enum = lambda values: {"type": "string", "enum": list(values)}  # noqa: E731
    obj = lambda props, optional=(): {  # noqa: E731
        "type": "object", "properties": props, "required": [k for k in props if k not in optional],
        "additionalProperties": False}
    position = enum(POSITIONS)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "storyvid.scenes/1",
        "title": "storyvid scenes.json",
        **obj({
            "format": {"const": FORMAT},
            "title": string,
            "lang": enum(LANG_NAMES),
            "character": {"type": "object", "description": "Optional look of the host (actor id 'host')."},
            "short": {"type": "object", "required": ["scenes"], "additionalProperties": False,
                      "description": "Optional: scenes cut into the 9:16 Short (aim for 30-60 s, hook first).",
                      "properties": {"scenes": {"type": "array", "minItems": 1, "uniqueItems": True,
                                                "items": {"type": "integer", "minimum": 0}}}},
            "cast": {"type": "array", "items": obj({
                "id": {"type": "string", "pattern": SLUG, "not": {"enum": [HOST, NARRATOR]}},
                "name": string,
                "preset": {"type": "string", "pattern": SLUG,
                           "description": "Character preset id; unknown ids become asset requests."},
                "outfit": enum(OUTFITS), "accessory": enum(ACCESSORIES), "kind": enum(KINDS)})},
            "scenes": {"type": "array", "minItems": 1, "items": obj({
                "bg_id": {"type": "string", "pattern": BG_SLUG,
                          "description": "Background id <place>_<day|night>; unknown ids become asset requests."},
                "bg_prompt": {"type": "string", "description": "English description of the place."},
                "camera": enum(CAMERAS),
                "actors": {"type": "array", "maxItems": MAX_ACTORS, "items": obj({
                    "id": {"type": "string", "description": "A cast id, or 'host'."},
                    "position": position, "pose": enum(POSES), "expression": enum(EXPRESSIONS),
                    "action": enum(ACTIONS)})},
                "props": {"type": "array", "maxItems": MAX_PROPS, "items": obj({
                    "id": {"type": "string", "pattern": SLUG,
                           "description": "Animal or prop id; unknown ids become asset requests."},
                    "position": position})},
                "lines": {"type": "array", "minItems": 1, "maxItems": MAX_LINES, "items": obj({
                    "speaker": {"type": "string", "description": "'narrator' or a cast id on stage."},
                    "text": string})},
            })},
        }, optional=("character", "short")),
    }


def catalog() -> dict:
    """Every id an agent can use without requesting a new asset."""
    return {
        "backgrounds": pack.labels("backgrounds"),
        "animals": pack.labels("animals"),
        "props": pack.labels("props"),
        "characters": [[k, v["label"]] for k, v in PRESETS.items()],
        "outfits": list(OUTFITS), "accessories": list(ACCESSORIES),
    }


def write_reference_files() -> None:
    SCHEMA_PATH.parent.mkdir(exist_ok=True)
    SCHEMA_PATH.write_text(json.dumps(json_schema(), ensure_ascii=False, indent=2) + "\n")
    CATALOG_PATH.write_text(json.dumps(catalog(), ensure_ascii=False, indent=2) + "\n")
    REVIEW_SCHEMA_PATH.write_text(json.dumps(review_schema(), ensure_ascii=False, indent=2) + "\n")
