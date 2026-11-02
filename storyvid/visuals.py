"""Muse images and clips for a script: visuals.json (format "storyvid.visuals/1") next to scenes.json.

    python -m storyvid.visuals prompts output/<id> [--provider offline|muse|openai|codex] [--ratio 16:9|9:16]
    python -m storyvid.visuals cast output/<id> [--only <cast id>] [--redo]
    python -m storyvid.visuals scenes output/<id> [--only <scene index>] [--redo] [--images-only|--clips-only]
    python -m storyvid.visuals status

The script must be approved by a person first (web UI, tab Kịch bản, "Duyệt kịch bản"; meta.json
"approved_script"); --skip-review is for tests only. The style comes from meta.json "style" (storyvid/styles.py).

prompts writes the plan (style, a fixed look per character, an opening-frame and a motion prompt per scene).
cast makes one reference sheet per character; scenes makes each scene's opening image (with the sheets of the
actors in that scene attached) and then a clip from that image. Generation goes through MuseFlow
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

from .contract import HOST, VISUALS_FORMAT, validate_visuals

ROOT = Path(__file__).resolve().parents[1]
MUSEFLOW_API = os.environ.get("MUSEFLOW_API", "http://127.0.0.1:8770")
CLIP_SECONDS = 10  # Muse returns 10 s clips whatever is asked; the renderer fits them to the narration
BATCH = 10         # scenes per prompt-writing request, so long stories fit in one reply
MAX_SHEETS = 3     # character sheets attached to one scene image
MAX_REFS = 4       # all images attached to one scene image (sheets first, then style references)
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
    "frame. Keep every prompt acceptable to mainstream generators: no gore or explicit violence; build fear "
    "through mood, light, framing and what is half-hidden.")
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


def _offline_scene(scene: dict, names: dict) -> dict:
    framing, motion = CAMERA_LOOK.get(scene["camera"], CAMERA_LOOK["static"])
    when = "at night" if scene["bg_id"].endswith("_night") else "in daylight"
    people = [f"{names.get(a['id'], a['id'])} {POSE_LOOK.get(a['pose'], 'standing')}, {a['expression']} expression, "
              f"{a['position'].replace('_', ' ')} of frame" for a in scene["actors"]]
    actions = [f"{names.get(a['id'], a['id'])} {ACTION_LOOK[a['action']]}" for a in scene["actors"]
               if a["action"] in ACTION_LOOK]
    beat = " ".join(line["text"] for line in scene["lines"])[:300]
    return {
        "image_prompt": f"{framing} of {scene['bg_prompt']} {when}. " + ("; ".join(people) + ". " if people else "")
                        + f"Story moment: {beat}",
        "video_prompt": f"{motion}. " + ("; ".join(actions) + ". " if actions else "")
                        + f"Natural, subtle movement that shows this moment: {beat}",
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


def write_prompts(script: dict, channel: dict, ratio: str, provider: str, style: str = "") -> dict:
    """style: the project's chosen style text; when empty the writer picks one."""
    names = cast_names(script, channel)
    members = {c["id"]: c for c in script.get("cast", [])}
    members[HOST] = {"id": HOST, "name": names[HOST], **{k: v for k, v in channel.get("host", {}).items()
                                                          if k in ("preset", "outfit", "accessory")}}
    ids = used_cast(script)
    fixed_style = bool(style)
    style = style or DEFAULT_STYLE
    looks = {cid: _offline_look(members.get(cid, {})) for cid in ids}
    scenes = [_offline_scene(s, names) for s in script["scenes"]]
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
                            "narration": [line["text"] for line in script["scenes"][i]["lines"]]} for i in batch],
            }
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
def sheet_prompt(name: str, look: str, style: str) -> str:
    return (f"Character reference sheet for {name}. Appearance (must match exactly): {look}.\n\n"
            "Show this one character only, full body, front view and three-quarter view side by side, neutral pose, "
            "calm expression, plain light grey background, even soft lighting. No text, no labels, no other people, "
            f"no scenery.\n\nVisual style: {style}")


def scene_image_prompt(visuals: dict, scene_index: int, script: dict, names: dict) -> str:
    """Style first, then the frame; only the characters on stage in this scene are described."""
    looks = {c["id"]: c["look"] for c in visuals["cast"]}
    actors = [a["id"] for a in script["scenes"][scene_index]["actors"]]
    who = [f"{names.get(cid, cid)}: {looks[cid]}" for cid in actors if cid in looks]
    text = f"{visuals['style']}\n\n{visuals['scenes'][scene_index]['image_prompt']}"
    if who:
        text += "\n\nCharacters in this frame (keep exactly this look; the attached sheets show them):\n" + "\n".join(who)
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
                             visuals["ratio"], project / "muse" / "cast" / f"{c['id']}.png",
                             style_refs(project, visuals))
            c["sheet"] = file.relative_to(project).as_posix()
            c.pop("error", None)
        except RuntimeError as e:
            failed += 1
            c["error"] = str(e)[:500]
            print(f"  failed: {e}")
        save(project, visuals)
    return failed


def make_scenes(project: Path, only: int | None, redo: bool, images_only: bool, clips_only: bool = False) -> int:
    script, visuals = load(project)
    if not visuals:
        raise SystemExit("No visuals.json yet: run the prompts step first")
    names = cast_names(script, json.loads((ROOT / "channel.json").read_text(encoding="utf-8")))
    sheets = {c["id"]: project / c["sheet"] for c in visuals["cast"] if c["sheet"] and (project / c["sheet"]).is_file()}
    styling = style_refs(project, visuals)
    todo = [i for i in range(len(visuals["scenes"])) if only is None or i == only]
    if clips_only:  # clips start from an opening image; scenes without one wait for "images"
        todo = [i for i in todo if visuals["scenes"][i]["image"] and (project / visuals["scenes"][i]["image"]).is_file()]
    failed = []

    def one(i: int) -> None:
        s = visuals["scenes"][i]
        try:
            if not clips_only and (redo or not s["image"] or not (project / s["image"]).is_file()):
                print(f"[scene {i + 1}] image")
                refs = [sheets[a["id"]] for a in script["scenes"][i]["actors"] if a["id"] in sheets][:MAX_SHEETS]
                refs = (refs + styling)[:MAX_REFS]
                file = _generate("image", scene_image_prompt(visuals, i, script, names), visuals["ratio"],
                                 project / "muse" / f"scene_{i:02d}.png", refs, s["negative"])
                s["image"], s["clip"] = file.relative_to(project).as_posix(), ""
                save(project, visuals)
            if not images_only and (redo or not s["clip"] or not (project / s["clip"]).is_file()):
                print(f"[scene {i + 1}] clip")
                prompt = f"{s['video_prompt']}\n\nVisual style: {visuals['style']}"
                file = _generate("video", prompt, visuals["ratio"], project / "muse" / f"scene_{i:02d}.mp4",
                                 [project / s["image"]], s["negative"])
                s["clip"] = file.relative_to(project).as_posix()
            s.pop("error", None)
        except RuntimeError as e:
            failed.append(i)
            s["error"] = str(e)[:500]
            print(f"[scene {i + 1}] failed: {e}")
        save(project, visuals)

    # one scene per signed-in account at a time; with a single account the scenes run in order
    workers = max(1, min(ready_accounts(), len(todo)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(one, todo))
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
    ap.add_argument("--only", help="one cast id (cast) or one 0-based scene index (scenes)")
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
        visuals = write_prompts(script, channel, ratio, args.provider, chosen.get("text", ""))
        refs = []
        for k, ref in enumerate(chosen.get("refs", [])):
            target = project / "muse" / "style" / f"ref_{k}{Path(ref).suffix}"
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ref, target)
            refs.append(target.relative_to(project).as_posix())
        if refs:
            visuals["style_refs"] = refs
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
        failed = make_scenes(project, int(args.only) if args.only is not None else None, args.redo, args.images_only,
                             args.clips_only)
    if failed:
        raise SystemExit(f"{failed} item(s) failed; see the error fields in visuals.json and retry them")
    print("Done")


if __name__ == "__main__":
    main()
