"""Muse images and clips for a script: visuals.json (format "storyvid.visuals/1") next to scenes.json.

    python -m storyvid.visuals prompts output/<id> [--provider offline|muse|openai|codex] [--ratio 16:9|9:16]
    python -m storyvid.visuals cast output/<id> [--only <cast id>] [--redo]
    python -m storyvid.visuals scenes output/<id> [--only <scene index>] [--redo] [--images-only|--clips-only]

Clips can continue from the previous scene's last frame (visuals.json "continuity": auto = when two scenes in
a row share the same place, all, or off). Linked scenes make their clips one after another; separate chains run
at the same time on different accounts.
    python -m storyvid.visuals status

The script must be approved by a person first (web UI, tab Kịch bản, "Duyệt kịch bản"; meta.json
"approved_script"), and the character sheets before the scenes step (tab Hình Muse, "Duyệt nhân vật"; meta.json
"approved_cast"); --skip-review is for tests only. storyvid.auto runs all steps in a row between those two gates. The style comes from meta.json "style" (storyvid/styles.py).

prompts writes the plan (style, a fixed look per character, an opening-frame and a motion prompt per scene).
cast makes one reference sheet per character; scenes makes each scene's opening image (with the sheets of the
actors in that scene attached, plus a photo of any real place from refs/places.json the scene shows, see
storyvid/places.py) and then a clip from that image. Generation goes through MuseFlow
(museflow/, `npm start`), which drives the signed-in Muse accounts; it must be running.
Render with: python -m storyvid.cli --script output/<id>/scenes.json --visuals
"""
import argparse
import hashlib
import json
import shutil
import os
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import places
from .contract import HOST, VISUALS_FORMAT, validate_visuals

ROOT = Path(__file__).resolve().parents[1]
MUSEFLOW_API = os.environ.get("MUSEFLOW_API", "http://127.0.0.1:8770")
CLIP_SECONDS = 10  # Muse returns 10 s clips whatever is asked; the renderer fits them to the narration
BATCH = 10         # scenes per prompt-writing request, so long stories fit in one reply
MAX_SHEETS = 3     # character sheets attached to one scene image
MAX_REFS = 4       # all images attached to one scene image (sheets first, then style references)
SOURCE_CHARS = 12000  # story text sent with the first prompt batch, for the character looks
DEFAULT_STYLE = ("Cinematic 3D animated film still, moody low-key lighting, soft volumetric light, rich texture, "
                 "shallow depth of field. No text, no subtitles, no logos, no watermark.")
NEGATIVE = "text, subtitles, watermark, logo, extra fingers, distorted faces, gore"

# offline wording for the fields of scenes.json
PRESET_LOOK = {"young_man": "a Vietnamese man in his twenties", "young_woman": "a Vietnamese woman in her twenties",
               "elder_man": "an elderly Vietnamese man with grey hair", "elder_woman": "an elderly Vietnamese woman "
               "with grey hair in a bun", "boy": "a Vietnamese boy about eight years old",
               "girl": "a Vietnamese girl about eight years old", "middle_man": "a middle-aged Vietnamese man",
               "middle_woman": "a middle-aged Vietnamese woman"}
OUTFIT_LOOK = {"earth": "earth-brown traditional cotton clothes", "indigo": "indigo-dyed traditional clothes",
               "moss": "moss-green traditional clothes", "cream": "undyed cream cotton clothes"}
ACCESSORY_LOOK = {"bag": "a cloth shoulder bag", "scarf": "a checkered scarf", "flashlight": "a flashlight"}
POSE_LOOK = {"idle": "standing still", "talk": "talking", "point": "pointing", "scared": "recoiling in fear",
             "think": "thinking, hand on chin", "shrug": "shrugging", "reach": "reaching out",
             "wave": "waving", "cower": "cowering"}
CAMERA_LOOK = {"zoom_in": ("Close-up", "Slow push-in toward the faces"), "zoom_out": ("Wide shot", "Slow pull-back"),
               "pan_left": ("Wide shot", "Slow pan to the left"), "pan_right": ("Wide shot", "Slow pan to the right"),
               "static": ("Medium shot", "Locked-off camera, subtle movement only")}
ACTION_LOOK = {"enter": "walks into frame", "exit": "walks out of frame", "approach": "steps closer",
               "jump": "jumps back, startled", "shake": "trembles"}

SYSTEM = (
    "You are a film storyboard artist. For each scene of a narrated story, write prompts for an image model "
    "(the scene's opening frame) and for an image-to-video model (a 10-second clip that starts from that frame). "
    "Write the prompts in English. Describe what is seen, not what is said; narration and dialogue are added later "
    "as voice-over, so no one in frame should speak to camera. Name characters by their name; their fixed look is "
    "given separately, so do not restate clothing or faces in the scene prompts. No text, subtitles or logos in "
    "frame. Keep every prompt acceptable to mainstream generators: no gore or explicit violence; build tension "
    "through mood, light, framing and what is half-hidden. Each cast member comes with a draft_look taken from a "
    "stick-figure catalogue: it only hints at age and gender. When the source story is given, write every look "
    "from it instead (age, build, skin, hair, face, clothing, what they carry, and the story's world and era) and "
    "drop any draft detail the story contradicts; an animal or creature character keeps its animal body (species, "
    "size, colours, legs, shell or wings), drawn as a cartoon character with a readable face, never as a person; "
    "keep each look to one or two sentences that fit the style. "
    "When a scene comes with a storyboard shot, follow it: the image_prompt opens with its framing and shows its "
    "start_frame with its composition; the video_prompt is its camera move, its action and performance, and ends "
    "on its end_frame, nothing more happening, then 'Sound:' with the shot's sound in English (real sounds and "
    "sound effects only: no speech, no music). Scenes follow one another as one film: the opening frame continues "
    "from previous_end as joins_previous says (same positions, screen direction, light, what people hold), so the "
    "cut feels motivated.")
SCHEMA = {
    "type": "object", "required": ["style", "cast", "scenes"],
    "properties": {
        "style": {"type": "string", "description": "One visual style for the whole video"},
        "cast": {"type": "array", "items": {"type": "object", "required": ["id", "look"], "properties": {
            "id": {"type": "string"}, "look": {"type": "string",
                                               "description": "Fixed appearance: age, face, hair, clothing"}}}},
        "scenes": {"type": "array", "items": {"type": "object",
                                              "required": ["index", "image_prompt", "video_prompt", "negative"],
                                              "properties": {"index": {"type": "integer"},
                                                             "image_prompt": {"type": "string"},
                                                             "video_prompt": {"type": "string"},
                                                             "negative": {"type": "string"}}}},
    },
}


# ---------- MuseFlow ----------
def muse(path: str, body: dict | None = None, timeout: float = 30) -> dict:
    """Call the MuseFlow API (museflow/electron/api.js)."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(MUSEFLOW_API + path, data=data, method="POST" if body is not None else "GET",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode(errors="replace") or "{}") or {"ok": False, "error": f"HTTP {e.code}"}
    except urllib.error.URLError as e:
        raise RuntimeError(f"MuseFlow is not running at {MUSEFLOW_API} ({e.reason}). Start it: cd museflow && npm start"
                           ) from None


def ready_accounts() -> int:
    status = muse("/api/status")
    return int(status.get("ready", 0))


# ---------- review gate ----------
def script_digest(script: dict) -> str:
    return hashlib.sha256(json.dumps(script, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def meta(project: Path) -> dict:
    path = project / "meta.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def is_approved(project: Path) -> bool:
    """A person approved this exact scenes.json; any later edit needs a new approval."""
    path = project / "scenes.json"
    if not path.exists():
        return False
    script = json.loads(path.read_text(encoding="utf-8"))
    return meta(project).get("approved_script") == script_digest(script)


def cast_digest(project: Path, visuals: dict) -> str:
    """The character sheets as they are now: a new look or a remade sheet needs a new approval."""
    from .continuity import content
    sheets = [(c["id"], c["look"], c["sheet"], content(project, c["sheet"])) for c in visuals["cast"]]
    return hashlib.sha256(json.dumps(sheets, ensure_ascii=False).encode()).hexdigest()


def cast_ready(project: Path, visuals: dict | None) -> bool:
    return bool(visuals) and all(c["sheet"] and (project / c["sheet"]).is_file() for c in visuals["cast"])


def is_cast_approved(project: Path, visuals: dict | None = None) -> bool:
    """A person looked at every character sheet and lets the scene images start (meta.json "approved_cast")."""
    visuals = visuals if visuals is not None else load(project)[1]
    return cast_ready(project, visuals) and meta(project).get("approved_cast") == cast_digest(project, visuals)


# ---------- visuals.json ----------
def load(project: Path) -> tuple[dict, dict | None]:
    script = json.loads((project / "scenes.json").read_text(encoding="utf-8"))
    path = project / "visuals.json"
    return script, (json.loads(path.read_text(encoding="utf-8")) if path.exists() else None)


_save_lock = threading.Lock()


def save(project: Path, visuals: dict) -> None:
    with _save_lock:
        tmp = project / "visuals.json.tmp"
        tmp.write_text(json.dumps(visuals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(project / "visuals.json")


def cast_names(script: dict, channel: dict) -> dict:
    names = {c["id"]: c["name"] for c in script.get("cast", [])}
    names[HOST] = channel.get("host", {}).get("name", "Host")
    return names


def used_cast(script: dict) -> list[str]:
    """Cast ids that appear on stage, in order of first appearance."""
    order = []
    for scene in script["scenes"]:
        for a in scene["actors"]:
            if a["id"] not in order:
                order.append(a["id"])
    return order


def _offline_look(member: dict) -> str:
    if member.get("kind") == "ghost":
        return ("a pale ghost of " + PRESET_LOOK.get(member.get("preset"), "a person") + ", long black hair covering "
                "the face, faded white clothes, translucent, floating just above the ground")
    parts = [PRESET_LOOK.get(member.get("preset"), "a Vietnamese villager"),
             "wearing " + OUTFIT_LOOK.get(member.get("outfit"), "simple village clothes")]
    if ACCESSORY_LOOK.get(member.get("accessory")):
        parts.append("with " + ACCESSORY_LOOK[member["accessory"]])
    return ", ".join(parts)


def _offline_scene(scene: dict, names: dict, shot: dict | None = None) -> dict:
    framing, motion = CAMERA_LOOK.get(scene["camera"], CAMERA_LOOK["static"])
    if shot:
        from .storyboard import MOVES, describe
        framing, motion = describe(shot), MOVES.get(shot.get("movement"), motion).capitalize()
        if shot.get("start_frame"):
            framing = f"{framing}. {shot['start_frame']}"
        for key, lead in (("action", ""), ("performance", ""), ("end_frame", "Ends on: ")):
            if shot.get(key):
                motion = f"{motion}. {lead}{shot[key]}"
    when = "at night" if scene["bg_id"].endswith("_night") else "in daylight"
    people = [f"{names.get(a['id'], a['id'])} {POSE_LOOK.get(a['pose'], 'standing')}, {a['expression']} expression, "
              f"{a['position'].replace('_', ' ')} of frame" for a in scene["actors"]]
    actions = [f"{names.get(a['id'], a['id'])} {ACTION_LOOK[a['action']]}" for a in scene["actors"]
               if a["action"] in ACTION_LOOK]
    beat = " ".join(line["text"] for line in scene["lines"])[:300]
    return {
        "image_prompt": (f"{framing}. Setting: {scene['bg_prompt']} {when}. " if shot
                         else f"{framing} of {scene['bg_prompt']} {when}. ") + ("; ".join(people) + ". " if people else "")
                        + f"Story moment: {beat}",
        "video_prompt": f"{motion}. " + ("; ".join(actions) + ". " if actions else "")
                        + f"Natural, subtle movement that shows this moment: {beat}"
                        + (f". Sound: {shot['sound']}" if shot and shot.get("sound") else ""),
        "negative": NEGATIVE,
    }


def _ask(provider: str, system: str, user: str) -> dict:
    from . import llm
    if provider == "muse":
        prompt = (f"{system}\n\nReply with only one JSON object matching this schema, no other text, and do not "
                  f"create any image or video in this reply:\n{json.dumps(SCHEMA)}\n\n{user}")
        reply = muse("/api/chat", {"prompt": prompt, "timeoutSec": 600}, timeout=720)
        if not reply.get("ok"):
            raise RuntimeError(f"Muse could not write the prompts: {reply.get('error')}")
        return llm.extract_json(reply["text"])
    if provider == "openai":
        return llm.openai_compatible(system, user, SCHEMA)
    if provider == "codex":
        return llm.codex(system, user, SCHEMA)
    raise ValueError(f"Unknown provider: {provider}")


def write_prompts(script: dict, channel: dict, ratio: str, provider: str, style: str = "", source: str = "",
                  storyboard: dict | None = None) -> dict:
    """style: the project's chosen style text; when empty the writer picks one. source: the original story, so the
    looks follow how the story describes each character. storyboard: storyboard.json, whose shots frame each scene."""
    from .storyboard import aligned, brief as shot_brief
    shots = aligned(storyboard, script)
    names = cast_names(script, channel)
    members = {c["id"]: c for c in script.get("cast", [])}
    members[HOST] = {"id": HOST, "name": names[HOST], **{k: v for k, v in channel.get("host", {}).items()
                                                          if k in ("preset", "outfit", "accessory")}}
    ids = used_cast(script)
    fixed_style = bool(style)
    style = style or DEFAULT_STYLE
    looks = {cid: _offline_look(members.get(cid, {})) for cid in ids}
    scenes = [_offline_scene(s, names, shots[i]) for i, s in enumerate(script["scenes"])]
    if provider != "offline":
        for start in range(0, len(script["scenes"]), BATCH):
            batch = list(range(start, min(start + BATCH, len(script["scenes"]))))
            payload = {
                "title": script["title"], "aspect_ratio": ratio,
                "cast": [{"id": cid, "name": names.get(cid, cid), "kind": members.get(cid, {}).get("kind", "human"),
                          "draft_look": looks[cid]} for cid in ids],
                "scenes": [{"index": i, "place": script["scenes"][i]["bg_prompt"],
                            "time": "night" if script["scenes"][i]["bg_id"].endswith("_night") else "day",
                            "camera": script["scenes"][i]["camera"],
                            "on_stage": [{"name": names.get(a["id"], a["id"]), "pose": a["pose"],
                                          "expression": a["expression"], "action": a["action"]}
                                         for a in script["scenes"][i]["actors"]],
                            "narration": [line["text"] for line in script["scenes"][i]["lines"]],
                            **({"shot": shot_brief(shots[i])} if shots[i] else {})} for i in batch],
            }
            if source and not start:  # looks are fixed with the first batch
                payload["source_story"] = source[:SOURCE_CHARS]
            if fixed_style or start:
                payload["style"] = style
                payload["note"] = ("The style is fixed: return it unchanged and write every look and prompt so it "
                                   "fits that style." if not start else
                                   "Style and cast looks are already fixed; return them unchanged.")
            print(f"  prompts for scenes {batch[0] + 1}-{batch[-1] + 1} ({provider})...")
            reply = _ask(provider, SYSTEM, json.dumps(payload, ensure_ascii=False))
            if not start:
                if not fixed_style:
                    style = str(reply.get("style") or style).strip()
                for c in reply.get("cast", []):
                    if c.get("id") in looks and str(c.get("look", "")).strip():
                        looks[c["id"]] = c["look"].strip()
            for item in reply.get("scenes", []):
                i = item.get("index")
                if isinstance(i, int) and i in batch and str(item.get("image_prompt", "")).strip() \
                        and str(item.get("video_prompt", "")).strip():
                    scenes[i] = {"image_prompt": item["image_prompt"].strip(),
                                 "video_prompt": item["video_prompt"].strip(),
                                 "negative": str(item.get("negative") or NEGATIVE).strip()}
    return {"format": VISUALS_FORMAT, "scenes_file": "scenes.json", "ratio": ratio, "style": style,
            "cast": [{"id": cid, "look": looks[cid], "sheet": ""} for cid in ids],
            "scenes": [{**s, "image": "", "clip": ""} for s in scenes]}


def merge_files(new: dict, old: dict | None) -> dict:
    """Keep generated files whose prompt did not change, so rewriting prompts does not throw work away."""
    if not old or old.get("ratio") != new["ratio"] or old.get("style") != new["style"]:
        return new
    old_cast = {c["id"]: c for c in old.get("cast", [])}
    for c in new["cast"]:
        if old_cast.get(c["id"], {}).get("look") == c["look"]:
            c["sheet"] = old_cast[c["id"]].get("sheet", "")
    for s, o in zip(new["scenes"], old.get("scenes", [])):
        if o.get("image_prompt") == s["image_prompt"]:
            s["image"] = o.get("image", "")
            if o.get("video_prompt") == s["video_prompt"]:
                s["clip"] = o.get("clip", "")
    return new


# ---------- generation ----------
SHEET_RATIO = "16:9"  # four panels side by side; the sheet is only a reference, whatever the video's frame


def sheet_prompt(name: str, look: str, style: str) -> str:
    """One image per character: a face close-up plus a full-body turnaround, so a scene uses one reference slot."""
    return (f"Character reference sheet for {name}. Appearance (must match exactly): {look}.\n\n"
            "Layout, four panels side by side on one sheet: (1) a head-and-shoulders close-up portrait with a natural, "
            "characteristic expression, showing the face, hair and any accessories clearly; then the full body, "
            "standing in a neutral pose, in (2) front view, (3) three-quarter view and (4) back view. The same outfit, "
            "props, colours and proportions in every panel; something the appearance says they carry or wear shows "
            "from every angle it faces, and nothing the appearance does not mention is added. Solid white background, flat even studio lighting, no shadows on the "
            "background. This one character only: no text, no labels, no other people, no scenery.\n\n"
            f"Visual style: {style}")


def scene_image_prompt(visuals: dict, scene_index: int, script: dict, names: dict) -> str:
    """Style first, then the frame; only the characters on stage in this scene are described."""
    looks = {c["id"]: c["look"] for c in visuals["cast"]}
    actors = [a["id"] for a in script["scenes"][scene_index]["actors"]]
    who = [f"{names.get(cid, cid)}: {looks[cid]}" for cid in actors if cid in looks]
    text = f"{visuals['style']}\n\n{visuals['scenes'][scene_index]['image_prompt']}"
    if who:
        text += ("\n\nCharacters in this frame (keep exactly this look; each attached sheet shows one of them: a face "
                 "close-up, then front, three-quarter and back views):\n" + "\n".join(who))
    return text


def _generate(media: str, prompt: str, size: str, save_to: Path, references: list[Path], negative: str = "") -> Path:
    reply = muse("/api/generate", {"mediaType": media, "prompt": prompt, "size": size, "duration": CLIP_SECONDS,
                                   "negative": negative, "references": [str(p) for p in references],
                                   "saveTo": str(save_to)}, timeout=1500)
    if not reply.get("ok"):
        raise RuntimeError(reply.get("error") or "Muse did not return media")
    note = " (after a safer retry)" if reply.get("retried") else ""
    print(f"  {media} -> {Path(reply['file']).name} via {reply.get('profileName', 'Muse')}{note}")
    return Path(reply["file"])


def style_refs(project: Path, visuals: dict) -> list[Path]:
    return [project / r for r in visuals.get("style_refs", []) if (project / r).is_file()]


def make_cast(project: Path, only: str | None, redo: bool) -> int:
    script, visuals = load(project)
    if not visuals:
        raise SystemExit("No visuals.json yet: run the prompts step first")
    names = cast_names(script, json.loads((ROOT / "channel.json").read_text(encoding="utf-8")))
    failed = 0
    for c in visuals["cast"]:
        if (only and c["id"] != only) or (c["sheet"] and not redo and (project / c["sheet"]).is_file()):
            continue
        print(f"[cast] {names.get(c['id'], c['id'])}")
        try:
            file = _generate("image", sheet_prompt(names.get(c["id"], c["id"]), c["look"], visuals["style"]),
                             SHEET_RATIO, project / "muse" / "cast" / f"{c['id']}.png",
                             style_refs(project, visuals))
            c["sheet"] = file.relative_to(project).as_posix()
            c.pop("error", None)
        except RuntimeError as e:
            failed += 1
            c["error"] = str(e)[:500]
            print(f"  failed: {e}")
        save(project, visuals)
    return failed


CONTINUITY_NOTE = ("CONTINUITY: attached image 1 is the exact last frame of the previous clip. Start this clip from "
                   "exactly that frame (same characters, pose, place, camera and light) and continue the motion "
                   "naturally, with no cut, jump or fade at the start. Attached image 2 shows how this scene should "
                   "look as it goes on.")


def linked(script: dict, visuals: dict, shots: list | None = None) -> list[bool]:
    """linked[i]: scene i's clip continues from scene i-1's last frame. In auto mode a storyboard shot decides
    (link "continuous" = the camera keeps rolling; any cut gets its own opening image); scenes without one link
    when they stay in the same place."""
    mode = visuals.get("continuity", "auto")
    scenes = script["scenes"]
    shots = shots or [None] * len(scenes)

    def auto(i: int) -> bool:
        if shots[i] and shots[i - 1]:
            return shots[i].get("link") == "continuous"
        return scenes[i]["bg_id"] == scenes[i - 1]["bg_id"]
    return [i > 0 and (mode == "all" or (mode == "auto" and auto(i))) for i in range(len(scenes))]


def chains(links: list[bool], todo: list[int]) -> list[list[int]]:
    """Group the scenes to clip into runs that must go in order (each linked to the one before)."""
    out: list[list[int]] = []
    for i in sorted(todo):
        if out and links[i] and out[-1][-1] == i - 1:
            out[-1].append(i)
        else:
            out.append([i])
    return out


def last_frame(clip: Path, out: Path) -> Path | None:
    from .ffmpeg import ffmpeg_exe
    import subprocess
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-sseof", "-0.15", "-i", str(clip), "-frames:v", "1",
                    "-update", "1", str(out)], capture_output=True)
    return out if out.is_file() and out.stat().st_size else None


def same_as(project: Path, visuals: dict, i: int, key: str, file: Path) -> int | None:
    """1-based number of another scene whose image/clip is byte for byte this file (Muse handed back an old result)."""
    data = None
    for n, other in enumerate(visuals["scenes"]):
        path = project / other[key] if n != i and other.get(key) else None
        if path and path.is_file() and path != file and path.stat().st_size == file.stat().st_size:
            data = data or hashlib.sha256(file.read_bytes()).digest()
            if hashlib.sha256(path.read_bytes()).digest() == data:
                return n + 1
    return None


def checked(project: Path, visuals: dict, i: int, key: str, file: Path) -> Path:
    twin = same_as(project, visuals, i, key, file)
    if twin:
        file.unlink()
        raise RuntimeError(f"Muse returned scene {twin}'s {key} again instead of a new one; run this scene again")
    return file


def make_scenes(project: Path, only: list[int] | None, redo: bool, images_only: bool, clips_only: bool = False,
                skip_review: bool = False) -> int:
    from . import continuity
    if not skip_review:
        continuity.require(project)
    approval_inputs = continuity.digest(project)
    script, visuals = load(project)
    if not visuals:
        raise SystemExit("No visuals.json yet: run the prompts step first")
    names = cast_names(script, json.loads((ROOT / "channel.json").read_text(encoding="utf-8")))
    sheets = {c["id"]: project / c["sheet"] for c in visuals["cast"] if c["sheet"] and (project / c["sheet"]).is_file()}
    looks = {c["id"]: c["look"] for c in visuals["cast"]}
    styling = style_refs(project, visuals)
    todo = [i for i in range(len(visuals["scenes"])) if only is None or i in only]
    has = lambda key, i: bool(visuals["scenes"][i][key]) and (project / visuals["scenes"][i][key]).is_file()  # noqa: E731
    failed: set[int] = set()

    def fail(i: int, e: Exception) -> None:
        failed.add(i)
        if not skip_review and continuity.digest(project) != approval_inputs:
            print(f"[scene {i + 1}] failed after inputs changed: {e}")
            return  # never overwrite edits made while Muse was generating
        visuals["scenes"][i]["error"] = str(e)[:500]
        print(f"[scene {i + 1}] failed: {e}")
        save(project, visuals)

    def image(i: int) -> None:
        s = visuals["scenes"][i]
        try:
            if not skip_review:
                continuity.require(project)
            expected = continuity.input_digest(project, i, "image")
            print(f"[scene {i + 1}] image")
            refs = [sheets[a["id"]] for a in script["scenes"][i]["actors"] if a["id"] in sheets][:MAX_SHEETS]
            prompt = scene_image_prompt(visuals, i, script, names)
            for name, photos in places.for_scene(project, script, visuals, i):
                if len(refs) + len(photos) <= MAX_REFS:
                    refs += photos
                    prompt += "\n\n" + places.PLACE_NOTE.format(name=name)
            note, locked_refs = continuity.references(project, i)
            prompt += "\n\n" + note
            refs = refs + locked_refs + styling
            if len(refs) > MAX_REFS:
                raise RuntimeError(f"Cảnh {i + 1}: vượt {MAX_REFS} ảnh tham chiếu")
            file = checked(project, visuals, i, "image", _generate("image", prompt, visuals["ratio"],
                           project / "muse" / f"scene_{i:02d}.png", refs, s["negative"]))
            if not skip_review:
                continuity.require(project)
                if expected != continuity.input_digest(project, i, "image"):
                    raise RuntimeError("Bộ mẫu hoặc prompt đổi trong khi tạo ảnh; hãy chạy lại")
            s["image"], s["clip"] = file.relative_to(project).as_posix(), ""
            s.pop("error", None)
            save(project, visuals)
            continuity.record(project, i, "image", expected)
        except RuntimeError as e:
            fail(i, e)

    from .storyboard import aligned, load as load_storyboard
    links = linked(script, visuals, aligned(load_storyboard(project), script))

    def clip(i: int) -> None:
        s = visuals["scenes"][i]
        prompt, refs = f"{s['video_prompt']}\n\nVisual style: {visuals['style']}", [project / s["image"]]
        continues = False
        if links[i] and has("clip", i - 1):
            end = last_frame(project / visuals["scenes"][i - 1]["clip"], project / "muse" / f"scene_{i - 1:02d}_end.png")
            if end:
                prompt, refs, continues = f"{prompt}\n\n{CONTINUITY_NOTE}", [end, project / s["image"]], True
        elif links[i]:
            print(f"[scene {i + 1}] previous clip missing: starting from this scene's own image")
        # Without the sheets a character who turns or moves is redrawn as someone else; they come after the frame.
        actors = [a["id"] for a in script["scenes"][i]["actors"]]
        refs += [sheets[cid] for cid in actors if cid in sheets]
        note, locked_refs = continuity.references(project, i)
        refs += locked_refs
        prompt += "\n\n" + note
        for name, photos in places.for_scene(project, script, visuals, i):
            refs += photos
            prompt += "\n\n" + places.PLACE_NOTE.format(name=name)
        who = [f"{names.get(cid, cid)}: {looks[cid]}" for cid in actors if cid in looks]
        if who:
            prompt += ("\n\nCharacters in this clip keep exactly this look from the first to the last frame (the "
                       "attached sheets after the opening frame show them):\n" + "\n".join(who))
        try:
            if len(refs) > MAX_REFS:
                raise RuntimeError(f"Cảnh {i + 1}: vượt {MAX_REFS} ảnh tham chiếu")
            if not skip_review:
                continuity.require(project)
                if links[i] and not continuity.current(project, i - 1, "clip"):
                    raise RuntimeError(f"Tạo lại clip cảnh {i} trước: cảnh này nối từ khung cuối của nó")
            if not skip_review and not continuity.current(project, i, "image"):
                raise RuntimeError("Ảnh mở cảnh dùng bộ mẫu cũ; tạo lại ảnh trước khi tạo clip")
            expected = continuity.input_digest(project, i, "clip")
            print(f"[scene {i + 1}] clip" + (" (continues from scene %d)" % i if continues else ""))
            file = checked(project, visuals, i, "clip", _generate("video", prompt, visuals["ratio"],
                           project / "muse" / f"scene_{i:02d}.mp4", refs, s["negative"]))
            if not skip_review:
                continuity.require(project)
                if expected != continuity.input_digest(project, i, "clip"):
                    raise RuntimeError("Bộ mẫu hoặc khung nối đổi trong khi tạo clip; hãy chạy lại")
            s["clip"] = file.relative_to(project).as_posix()
            s.pop("error", None)
            save(project, visuals)
            continuity.record(project, i, "clip", expected)
            nxt = i + 1
            if only is not None and nxt not in only and nxt < len(links) and links[nxt] and has("clip", nxt):
                print(f"  note: scene {nxt + 1} continues from this clip; make its clip again if the seam shows")
        except RuntimeError as e:
            fail(i, e)

    if clips_only:
        for i in todo:
            if not has("image", i):
                fail(i, RuntimeError("Chưa có ảnh mở cảnh; chạy thử ảnh trước khi tạo clip"))
    workers = max(1, ready_accounts())  # one generation per signed-in account at a time
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(todo)))) as pool:
        if not clips_only:  # opening images do not depend on each other
            wanted_images = [i for i in todo if redo or not has("image", i)
                             or (not skip_review and not continuity.current(project, i, "image"))]
            list(pool.map(image, wanted_images))
        if not images_only:
            # a chain of linked scenes goes in order; separate chains run side by side
            # a scene whose new image failed keeps its old image: making a clip from that would hide the failure
            wanted = [i for i in todo if i not in failed and has("image", i)
                      and (redo or not has("clip", i)
                           or (not skip_review and not continuity.current(project, i, "clip")))]
            list(pool.map(lambda chain: [clip(i) for i in chain], chains(links, wanted)))
    return len(failed)


def main() -> None:
    from .cli import load_env
    load_env(ROOT / ".env")
    sys.stdout.reconfigure(line_buffering=True)  # the web UI tails this output live
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["prompts", "cast", "scenes", "status"])
    ap.add_argument("project", nargs="?", help="project folder, e.g. output/ma_lon")
    ap.add_argument("--provider", choices=["offline", "muse", "openai", "codex"], default="muse",
                    help="who writes the prompts (default: Muse through MuseFlow)")
    ap.add_argument("--ratio", choices=["16:9", "9:16"], help="frame shape (default: keep, else 16:9)")
    ap.add_argument("--only", help="one cast id (cast), or 0-based scene indices separated by commas (scenes)")
    ap.add_argument("--redo", action="store_true", help="generate again even if a file exists")
    ap.add_argument("--images-only", action="store_true", help="scenes: stop after the opening images")
    ap.add_argument("--clips-only", action="store_true", help="scenes: only make clips from existing images")
    ap.add_argument("--skip-review", action="store_true", help="tests only: run without a person's approval")
    args = ap.parse_args()
    if args.step == "status":
        print(json.dumps(muse("/api/status"), ensure_ascii=False, indent=2))
        return
    if not args.project:
        ap.error("give the project folder")
    project = Path(args.project).resolve()
    if not args.skip_review and not is_approved(project):
        raise SystemExit("The script is not approved yet: a person reviews it first (web UI, tab Kịch bản, "
                         "\"Duyệt kịch bản\"). Any edit after approval needs a new approval.")
    if args.step == "prompts":
        from .styles import resolve
        script, old = load(project)
        info = meta(project)
        ratio = args.ratio or info.get("ratio") or (old or {}).get("ratio") or "16:9"
        channel = json.loads((ROOT / "channel.json").read_text(encoding="utf-8"))
        chosen = resolve(info.get("style"))
        story = project / "story.txt"
        from .storyboard import load as load_storyboard
        visuals = write_prompts(script, channel, ratio, args.provider, chosen.get("text", ""),
                                story.read_text(encoding="utf-8") if story.exists() else "",
                                load_storyboard(project))
        refs = []
        for k, ref in enumerate(chosen.get("refs", [])):
            target = project / "muse" / "style" / f"ref_{k}{Path(ref).suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ref, target)
            refs.append(target.relative_to(project).as_posix())
        if refs:
            visuals["style_refs"] = refs
        visuals["continuity"] = (old or {}).get("continuity") or info.get("continuity") or "auto"
        visuals = merge_files(visuals, old)
        errors = validate_visuals(visuals, script, project)
        if errors:
            raise SystemExit("\n".join(f"ERROR {e}" for e in errors))
        save(project, visuals)
        print(f"{len(visuals['scenes'])} scene prompt(s), {len(visuals['cast'])} character(s) -> "
              f"{project / 'visuals.json'}")
        return
    if args.step == "cast":
        failed = make_cast(project, args.only, args.redo)
    else:
        if not args.skip_review and not is_cast_approved(project):
            raise SystemExit("The character sheets are not approved yet: a person looks at them first (web UI, tab "
                             "Hình Muse, \"Duyệt nhân vật\"). A new or remade sheet needs a new approval.")
        only = [int(x) for x in args.only.split(",") if x.strip()] if args.only is not None else None
        failed = make_scenes(project, only, args.redo, args.images_only,
                             args.clips_only, skip_review=args.skip_review)
    if failed:
        raise SystemExit(f"{failed} item(s) failed; see the error fields in visuals.json and retry them")
    print("Done")


if __name__ == "__main__":
    main()
