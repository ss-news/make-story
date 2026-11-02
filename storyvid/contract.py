"""The scenes.json contract every model and agent writes to: format "storyvid.scenes/1".

validate() is strict and fixes nothing: it returns the problems with their JSON path. Ids of backgrounds,
props or character presets that are well-formed but missing from the asset pack are not errors; they come
back as asset requests (format "storyvid.asset-requests/1") for the asset agent to draw.
See docs/pipeline.md for the whole flow.
"""
import json
import re
from pathlib import Path

from . import audio, pack
from .character_catalog import ACCESSORIES, OUTFITS, PRESETS, validate_selection
from .script import ACTIONS, CAMERAS, EXPRESSIONS, HOST, KINDS, LANG_NAMES, NARRATOR, POSES, POSITIONS

FORMAT = "storyvid.scenes/1"
REQUESTS_FORMAT = "storyvid.asset-requests/1"
REVIEW_FORMAT = "storyvid.review/1"
ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "scenes.v1.schema.json"
CATALOG_PATH = ROOT / "schema" / "assets.catalog.json"
REVIEW_SCHEMA_PATH = ROOT / "schema" / "review.v1.schema.json"
VISUALS_FORMAT = "storyvid.visuals/1"
VISUALS_SCHEMA_PATH = ROOT / "schema" / "visuals.v1.schema.json"
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
              "rules": "Transparent background, object standing on its base, centred. Set 'height' in the "
                       "manifest: on-screen height as a share of the frame height (a character is 0.54, a buffalo "
                       "0.26, an oil lamp 0.12). If it is an animal, "
                       "use group 'animals', file assets/bac-bo-stick/extra/animals/{id}.svg, and set "
                       "'facing' (-1 looks left, 1 looks right)."},
    "characters": {"file": "assets/bac-bo-stick/extra/characters/{id}/rig.json + one SVG per part",
                   "rules": "Copy the folder of the closest existing preset, keep every part file name and the "
                            "rig anchors, then restyle. Register it under 'characters' in the extra manifest "
                            "with label, female, age (child|young|middle|elder), scale, skin, hair."},
}
TOP_KEYS = {"format", "title", "lang", "cast", "scenes"}
OPTIONAL_TOP_KEYS = {"character", "short", "music"}
CAST_KEYS = {"id", "name", "preset", "outfit", "accessory", "kind"}
SCENE_KEYS = {"bg_id", "bg_prompt", "camera", "actors", "props", "lines"}
OPTIONAL_SCENE_KEYS = {"ambience", "sfx"}
MAX_SFX = 6
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
    if "music" in script and _keys(script["music"], {"id"}, "$.music", errors):
        _sound(script["music"]["id"], "music", "$.music.id", errors)

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
        if not _keys(s, SCENE_KEYS, where, errors, OPTIONAL_SCENE_KEYS):
            continue
        if "ambience" in s:
            _sound(s["ambience"], "ambience", f"{where}.ambience", errors)
        if "sfx" in s:
            cues = s["sfx"] if isinstance(s["sfx"], list) else []
            if not isinstance(s["sfx"], list) or len(cues) > MAX_SFX:
                errors.append(f"{where}.sfx: must be a list of at most {MAX_SFX}")
            n_lines = len(s["lines"]) if isinstance(s["lines"], list) else 0
            for j, cue in enumerate(cues):
                cw = f"{where}.sfx[{j}]"
                if not _keys(cue, {"id", "line"}, cw, errors):
                    continue
                _sound(cue["id"], "sfx", f"{cw}.id", errors)
                if not isinstance(cue["line"], int) or isinstance(cue["line"], bool) or not 0 <= cue["line"] < max(1, n_lines):
                    errors.append(f"{cw}.line: must be the index of a line in this scene (0-{max(0, n_lines - 1)})")
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


def _sound(sound_id, kind: str, where: str, errors: list) -> None:
    """Sounds must already be in assets/audio/manifest.json: agents cannot draw audio, only pick it."""
    if sound_id not in audio.ids(kind):
        errors.append(f"{where}: {sound_id!r} is not a {kind} in assets/audio/manifest.json "
                      f"(choose from schema/assets.catalog.json)")


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
            "music": {"type": "object", "required": ["id"], "additionalProperties": False,
                      "description": "Optional background music for the whole video (ducked under the voice).",
                      "properties": {"id": {"type": "string", "description": "A music id from the catalog."}}},
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
                "ambience": {"type": "string", "description": "Optional ambience id looped under this scene."},
                "sfx": {"type": "array", "maxItems": MAX_SFX, "items": obj({
                    "id": {"type": "string", "description": "An sfx id from the catalog."},
                    "line": {"type": "integer", "minimum": 0,
                             "description": "Index of the line the sound starts with."}})},
            }, optional=("ambience", "sfx"))},
        }, optional=("character", "short", "music")),
    }


VISUALS_KEYS = {"format", "scenes_file", "ratio", "style", "cast", "scenes"}
VISUAL_CAST_KEYS = {"id", "look", "sheet"}
VISUAL_SCENE_KEYS = {"image_prompt", "video_prompt", "negative", "image", "clip"}
VISUAL_OPTIONAL_KEYS = {"error"}  # last generation error, written by the tool
RATIOS = ["16:9", "9:16"]


def _media_path(value, where: str, errors: list, base: Path | None) -> None:
    """"" (not generated yet) or a file inside the project folder."""
    if not isinstance(value, str):
        errors.append(f"{where}: must be a string")
        return
    if not value:
        return
    if value.startswith("/") or ".." in Path(value).parts:
        errors.append(f"{where}: must be a path inside the project folder")
    elif base is not None and not (base / value).is_file():
        errors.append(f"{where}: file {value} does not exist")


def validate_visuals(visuals, script: dict | None = None, base: Path | None = None) -> list[str]:
    """Problems in visuals.json: the Muse image/clip plan that sits next to scenes.json.

    script: the scenes.json it belongs to (scene count and cast ids must match). base: the project folder,
    to check that generated files exist."""
    errors: list[str] = []
    if not _keys(visuals, VISUALS_KEYS, "$", errors):
        return errors
    if visuals["format"] != VISUALS_FORMAT:
        errors.append(f"$.format: must be {VISUALS_FORMAT!r}")
    _text(visuals["scenes_file"], "$.scenes_file", errors)
    _enum(visuals["ratio"], RATIOS, "$.ratio", errors)
    _text(visuals["style"], "$.style", errors)
    cast_ids = {c["id"] for c in (script or {}).get("cast", []) if isinstance(c, dict)} | {HOST}
    seen = set()
    for i, c in enumerate(visuals["cast"] if isinstance(visuals["cast"], list) else []):
        where = f"$.cast[{i}]"
        if not _keys(c, VISUAL_CAST_KEYS, where, errors, VISUAL_OPTIONAL_KEYS):
            continue
        if _slug(c["id"], SLUG, f"{where}.id", errors):
            if script is not None and c["id"] not in cast_ids:
                errors.append(f"{where}.id: {c['id']!r} is not in the cast of scenes.json")
            if c["id"] in seen:
                errors.append(f"{where}.id: {c['id']!r} is listed twice")
            seen.add(c["id"])
        _text(c["look"], f"{where}.look", errors)
        _media_path(c["sheet"], f"{where}.sheet", errors, base)
    if not isinstance(visuals["cast"], list):
        errors.append("$.cast: must be a list")
    scenes = visuals["scenes"] if isinstance(visuals["scenes"], list) else []
    if not isinstance(visuals["scenes"], list):
        errors.append("$.scenes: must be a list")
    elif script is not None and len(scenes) != len(script.get("scenes", [])):
        errors.append(f"$.scenes: has {len(scenes)} scene(s), scenes.json has {len(script.get('scenes', []))}")
    for i, sc in enumerate(scenes):
        where = f"$.scenes[{i}]"
        if not _keys(sc, VISUAL_SCENE_KEYS, where, errors, VISUAL_OPTIONAL_KEYS):
            continue
        _text(sc["image_prompt"], f"{where}.image_prompt", errors)
        _text(sc["video_prompt"], f"{where}.video_prompt", errors)
        if not isinstance(sc["negative"], str):
            errors.append(f"{where}.negative: must be a string")
        _media_path(sc["image"], f"{where}.image", errors, base)
        _media_path(sc["clip"], f"{where}.clip", errors, base)
    return errors


def visuals_schema() -> dict:
    string = {"type": "string", "minLength": 1}
    media = {"type": "string", "description": "File inside the project folder, or \"\" until generated."}
    error = {"type": "string", "description": "Last generation error, written by the tool."}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": VISUALS_FORMAT,
        "title": "storyvid visuals.json (Muse images and clips for scenes.json)",
        "type": "object",
        "required": sorted(VISUALS_KEYS),
        "additionalProperties": False,
        "properties": {
            "format": {"const": VISUALS_FORMAT},
            "scenes_file": string,
            "ratio": {"type": "string", "enum": RATIOS},
            "style": {**string, "description": "Visual style added to every image and clip prompt."},
            "cast": {"type": "array", "items": {
                "type": "object", "required": sorted(VISUAL_CAST_KEYS), "additionalProperties": False,
                "properties": {"id": {"type": "string", "pattern": SLUG,
                                      "description": "A cast id from scenes.json, or host."},
                               "look": {**string, "description": "Fixed appearance used for the character sheet "
                                                                 "and every scene the character is in."},
                               "sheet": media, "error": error}}},
            "scenes": {"type": "array", "description": "One entry per scene of scenes.json, same order.", "items": {
                "type": "object", "required": sorted(VISUAL_SCENE_KEYS), "additionalProperties": False,
                "properties": {"image_prompt": {**string, "description": "Opening frame of the scene."},
                               "video_prompt": {**string, "description": "Motion and action from that frame."},
                               "negative": {"type": "string"}, "image": media, "clip": media, "error": error}}},
        },
    }


def catalog() -> dict:
    """Every id an agent can use without requesting a new asset."""
    return {
        "backgrounds": pack.labels("backgrounds"),
        "animals": pack.labels("animals"),
        "props": pack.labels("props"),
        "characters": [[k, v["label"]] for k, v in PRESETS.items()],
        "outfits": list(OUTFITS), "accessories": list(ACCESSORIES),
        "music": [[s["id"], s["label"]] for s in audio.sounds("music")],
        "ambience": [[s["id"], s["label"]] for s in audio.sounds("ambience")],
        "sfx": [[s["id"], s["label"]] for s in audio.sounds("sfx")],
    }


def write_reference_files() -> None:
    SCHEMA_PATH.parent.mkdir(exist_ok=True)
    SCHEMA_PATH.write_text(json.dumps(json_schema(), ensure_ascii=False, indent=2) + "\n")
    CATALOG_PATH.write_text(json.dumps(catalog(), ensure_ascii=False, indent=2) + "\n")
    REVIEW_SCHEMA_PATH.write_text(json.dumps(review_schema(), ensure_ascii=False, indent=2) + "\n")
    VISUALS_SCHEMA_PATH.write_text(json.dumps(visuals_schema(), ensure_ascii=False, indent=2) + "\n")
