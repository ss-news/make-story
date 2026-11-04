"""Step 1: rewrite a raw story into a scene-by-scene script (scenes.json)."""
import json
import os
import re
import unicodedata

POSES = ["idle", "talk", "point", "scared", "think", "shrug", "reach", "wave", "cower"]
EXPRESSIONS = ["neutral", "happy", "scared", "surprised", "sad", "angry", "smirk"]
POSITIONS = ["center", "left", "right", "far_left", "far_right"]
CAMERAS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "static"]
ACTIONS = ["none", "enter", "exit", "approach", "jump", "shake"]
KINDS = ["human", "ghost"]
NARRATOR = "narrator"   # speaker id for off-screen narration (spoken by the host voice)
HOST = "host"           # actor id of the channel host, whose look is script["character"]
MAX_PROPS = 3           # animals / objects standing on the ground in one scene
LANG_NAMES = {"en": "English", "vi": "Vietnamese", "de": "German", "fr": "French", "es": "Spanish"}
# What each kind of video asks of the script, the review and the upload kit. "story" keeps its id (ghost and
# folklore) so older projects stay as they were.
GENRE_INFO = {
    "story": {
        "label": "Truyện ma, dân gian",
        "video": "ghost and folklore story",
        "host": "a calm, slightly nervous storyteller who tells old ghost stories and folklore; dry humor, never gory",
        "cast_rule": 'Spirits and monsters use kind "ghost" (drawn pale, see-through and floating); everyone else "human".',
        "arc": ('- The first 30 seconds show the scariest or strangest moment of the story, its subject big and clear, and '
                'end on a question; no description of the village, the setting or daytime before something strange '
                'happens. Then explain the folklore "rules" once for viewers who never heard of it (keep local terms '
                'like ma da, ma lai), build tension, end with a twist or a chilling quiet line, then the narrator '
                'invites viewers to the next story.\n- Atmosphere over gore; characters react with real fear, never comedy.'),
        "night": True,
        "titles": "a mystery or a question about the story, no clickbait that overpromises",
        "thumbnail": ("a dark background, one big frightening subject filling the frame, one accent colour, a real "
                      "ghost-story look that cannot be mistaken for a children's cartoon"),
    },
    "drama": {
        "label": "Đời thường, kịch tính",
        "video": "real-life drama story (family, love, money, betrayal, kindness, second chances)",
        "host": "a warm, calm storyteller who tells true-to-life stories with empathy; never preachy",
        "cast_rule": 'Everyone is kind "human" unless the story really has a ghost.',
        "arc": ('- The first 30 seconds show the most dramatic moment of the story (the conflict at its peak, a shock, '
                'a humiliation, a reveal) with the main character big and clear, and end on a question. Then go back '
                'to how it came to this, build to a turning point where someone makes a choice, and end with the '
                'consequence and one quiet closing line; then the narrator invites viewers to the next story.\n'
                '- Real emotions shown through faces and actions, not melodrama or lectures; no gore.'),
        "night": False,
        "titles": "the conflict or the twist as a hook, emotional but true to the story, no clickbait that overpromises",
        "thumbnail": ("one main character's face big in frame with a strong emotion (shock, tears, anger), the "
                      "conflict readable at a glance, strong contrast, one accent colour"),
    },
    "explainer": {
        "label": "Kiến thức (khoa học, tâm lý)",
        "video": "science / psychology explainer",
        "night": False,
        "titles": "curiosity plus a clear benefit, no clickbait that overpromises",
        "thumbnail": "one big clear subject with a strong emotion, using the recurring characters when it helps",
    },
}
GENRES = list(GENRE_INFO)
CHUNK_CHARS = 2200  # longer texts are written in parts: a long reply from Muse can be cut off silently


def prop_ids() -> list[str]:
    from . import pack
    return pack.ids("animals", "props")


def _schema() -> dict:
    from .character_catalog import ACCESSORIES, OUTFITS, PRESETS
    string = {"type": "string"}
    enum = lambda values: {"type": "string", "enum": list(values)}  # noqa: E731
    obj = lambda props: {"type": "object", "properties": props, "required": list(props),  # noqa: E731
                         "additionalProperties": False}
    return obj({
        "title": string,
        "cast": {"type": "array", "items": obj({
            "id": string, "name": string, "preset": enum(PRESETS), "outfit": enum(OUTFITS),
            "accessory": enum(ACCESSORIES), "kind": enum(KINDS)})},
        "scenes": {"type": "array", "items": obj({
            "bg_id": string, "bg_prompt": string, "camera": enum(CAMERAS),
            "actors": {"type": "array", "items": obj({
                "id": string, "position": enum(POSITIONS), "pose": enum(POSES),
                "expression": enum(EXPRESSIONS), "action": enum(ACTIONS)})},
            "props": {"type": "array", "items": obj({"id": enum(prop_ids()), "position": enum(POSITIONS)})},
            "lines": {"type": "array", "items": obj({"speaker": string, "text": string})},
        })},
    })


SCENE_SCHEMA = _schema()


def build_prompt(story: str, channel: dict, lang: str, minutes: float, character=None,
                 genre: str = "story") -> tuple[str, str]:
    from . import pack
    from .character_catalog import PRESETS, resolve_character
    info_genre = GENRE_INFO[genre if genre in GENRE_INFO and genre != "explainer" else "story"]
    host = dict(channel["host"])
    if genre != "story":  # channel.json describes the host as a ghost-story teller
        host["personality"] = info_genre["host"]
    choice = resolve_character(host, character)
    if choice['preset'] != host.get('preset', 'young_man'):
        info = PRESETS[choice['preset']]
        host['name'] = info['label'].split(' · ')[-1]
        host['personality'] = f"a Vietnamese {info['age']} {'woman' if info['female'] else 'man'}, {info_genre['host']}"
    from .character_catalog import PRESETS as ALL_PRESETS
    words = int(minutes * 150)
    presets = "; ".join(f"{k} = {v['label']}" for k, v in ALL_PRESETS.items())
    system = f"""You write scripts for the faceless YouTube channel "{channel['channel_name']}": short animated videos; this one is a {info_genre["video"]}.
The host is {host['name']}: {host['personality']}. The host narrates; narration lines use speaker "{NARRATOR}". The host can also appear on stage as actor id "{HOST}" (good for the opening hook and the ending), but most scenes should show the story's own characters.

Write the story in {LANG_NAMES.get(lang, lang)} as an acted scene-by-scene script:
- cast: every character who appears (not the host). id = short ascii slug, name = how the story calls them. Pick the closest preset ({presets}). {info_genre["cast_rule"]}
- Mix narration with dialogue: characters should talk to each other, react, argue, call out, scream. Each scene has 1-4 lines; a line's speaker is "{NARRATOR}" or a cast id that is on stage in that scene.
- actors: who is visible in the scene (0-3), where they stand, pose, expression, and an action that shows interaction:
  enter = walks in from the nearest edge; exit = walks out at the end; approach = moves toward the others; jump = jolts in surprise; shake = trembles with fear.
  Characters facing each other while talking is automatic. Put people talking together on neighbouring positions (left/right, far_left/center...).
  Poses: talk, point, reach (reaching or grabbing toward someone), wave, scared, cower, think, shrug, idle.
{info_genre["arc"]}
- About {words} words of spoken text in total.
- props: 0-{MAX_PROPS} animals or objects standing in the scene ({", ".join(prop_ids())}), on positions no actor uses.
- bg_id: one of {", ".join(pack.ids("backgrounds"))} (day or night version of each place); bg_prompt: a short English description of the location; camera: slow move for the background."""
    return system, story



def _call_claude(system: str, user: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")
    response = client.beta.messages.create(
        model=model,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=system,
        messages=[{"role": "user", "content": user}],
        output_config={"format": {"type": "json_schema", "schema": SCENE_SCHEMA}},
    )
    if response.stop_reason == "refusal":
        raise RuntimeError(f"Claude declined the request: {response.stop_details}")
    if response.stop_reason == "max_tokens":
        raise RuntimeError("Script was cut off (max_tokens); shorten --minutes or the input story")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def _offline_script(story: str, genre: str = "story") -> dict:
    """No LLM available: keep the original text, split it into scenes narrated by the host."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", story.strip()) if s.strip()]
    title = sentences[0][:60] if sentences else "Untitled"
    scenes = []
    cues = [
        (("chết", " ma ", "hồn", "ghost", "dead", "scream", "hét"), "scared", "scared", "shake"),
        (("tại sao", "vì sao", "why", "?"), "think", "surprised", "none"),
        (("cười", "laugh"), "talk", "happy", "none"),
        (("khóc", "cry", "buồn"), "idle", "sad", "none"),
    ]
    for i in range(0, len(sentences), 2):
        text = " ".join(sentences[i:i + 2])
        low = f" {text.lower()} "
        pose, expr, action = ("point", "neutral", "enter") if i == 0 else ("talk", "neutral", "none")
        for keys, p, e, a in cues:
            if any(k in low for k in keys):
                pose, expr, action = p, e, a
                break
        n = len(scenes)
        scenes.append({
            "bg_id": (("village_path_night", "river_night") if GENRE_INFO.get(genre, {}).get("night")
                      else ("village_path_day", "interior_day"))[n // 3 % 2],
            "bg_prompt": "",
            "camera": CAMERAS[n % 4],
            "actors": [{"id": HOST, "position": POSITIONS[n % 3], "pose": pose, "expression": expr, "action": action}],
            "lines": [{"speaker": NARRATOR, "text": text}],
        })
    return {"title": title, "cast": [], "scenes": scenes}


def _pick(value, values):
    return value if value in values else values[0]


def _slug(value, fallback):
    text = unicodedata.normalize("NFD", str(value or "").lower().replace("đ", "d"))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9_]+", "_", text).strip("_") or fallback


def _normalize(script: dict, lang: str | None = None) -> dict:
    """Models without strict schemas may invent values; clamp them into the scenes.json contract
    (storyvid/contract.py). Unknown prop ids are kept: they become asset requests, not silent drops."""
    from .character_catalog import ACCESSORIES, OUTFITS, PRESETS
    cast, ids = [], {HOST}
    for i, c in enumerate(script.get("cast") or []):
        cid = _slug(c.get("id") or c.get("name"), f"c{i}")
        if cid in ids or cid == NARRATOR:
            continue
        ids.add(cid)
        cast.append({"id": cid, "name": str(c.get("name") or cid).strip(),
                     "preset": _pick(c.get("preset"), list(PRESETS)), "outfit": _pick(c.get("outfit"), list(OUTFITS)),
                     "accessory": _pick(c.get("accessory"), list(ACCESSORIES)), "kind": _pick(c.get("kind"), KINDS)})
    scenes = []
    for i, s in enumerate(script.get("scenes", [])):
        actors, seen = [], set()
        for a in s.get("actors") or []:
            aid = _slug(a.get("id"), "")
            if aid not in ids or aid in seen:
                continue
            seen.add(aid)
            actors.append({"id": aid, "position": _pick(a.get("position"), POSITIONS), "pose": _pick(a.get("pose"), POSES),
                           "expression": _pick(a.get("expression"), EXPRESSIONS), "action": _pick(a.get("action"), ACTIONS)})
        lines = []
        for ln in s.get("lines") or []:
            text = str(ln.get("text") or "").strip()
            if not text:
                continue
            speaker = _slug(ln.get("speaker"), NARRATOR)
            lines.append({"speaker": speaker if speaker in ids - {HOST} else NARRATOR, "text": text})
        if not lines:
            continue
        props = []
        for pr in (s.get("props") or [])[:MAX_PROPS]:
            if isinstance(pr, dict) and re.fullmatch(r"[a-z][a-z0-9_]*", str(pr.get("id") or "")):
                props.append({"id": pr["id"], "position": _pick(pr.get("position"), POSITIONS)})
        sound = {}  # optional audio cues are kept as written; the contract checks them against the audio manifest
        if isinstance(s.get("ambience"), str) and s["ambience"]:
            sound["ambience"] = s["ambience"]
        cues = [c for c in (s.get("sfx") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)
                and isinstance(c.get("line"), int) and 0 <= c["line"] < len(lines)]
        if cues:
            sound["sfx"] = [{"id": c["id"], "line": c["line"]} for c in cues]
        scenes.append({"bg_id": _slug(s.get("bg_id"), f"bg{i}"),
                       "bg_prompt": str(s.get("bg_prompt") or "a quiet Vietnamese village"),
                       "camera": _pick(s.get("camera"), CAMERAS), "actors": actors, "props": props,
                       "lines": lines, **sound})
    if not scenes:
        raise RuntimeError("Script has no scenes")
    from .contract import FORMAT
    lang = lang if lang in LANG_NAMES else script.get("lang") if script.get("lang") in LANG_NAMES else "en"
    result = {"format": FORMAT, "title": str(script.get("title") or "Untitled"), "lang": lang, "cast": cast,
              "scenes": scenes}
    if "character" in script:
        from .character_catalog import validate_selection
        result["character"] = validate_selection(script["character"])
    if isinstance(script.get("music"), dict) and isinstance(script["music"].get("id"), str):
        result["music"] = {"id": script["music"]["id"]}
    picked = (script.get("short") or {}).get("scenes") if isinstance(script.get("short"), dict) else None
    if isinstance(picked, list):
        picked = sorted({i for i in picked if isinstance(i, int) and 0 <= i < len(scenes)})
        if picked:
            result["short"] = {"scenes": picked}
    return result


def _call_muse(system: str, user: str) -> dict:
    """Muse writes the script through MuseFlow's chat (no API key needed; museflow/ must be running)."""
    from . import llm
    from .visuals import muse
    prompt = (f"{system}\n\nReply with only one JSON object matching this schema, no other text, and do not create any "
              f"image or video in this reply:\n{json.dumps(SCENE_SCHEMA)}\n\nSTORY:\n{user}")
    reply = muse("/api/chat", {"prompt": prompt, "timeoutSec": 900}, timeout=1020)
    if not reply.get("ok"):
        raise RuntimeError(f"Muse could not write the script: {reply.get('error')}")
    return llm.extract_json(reply["text"])


def explainer_prompt(channel: dict, lang: str, minutes: float, keep_text: bool) -> str:
    """System prompt for a science / psychology explainer acted out by a few recurring characters."""
    from . import pack
    from .character_catalog import PRESETS
    presets = "; ".join(f"{k} = {v['label']}" for k, v in PRESETS.items())
    words = int(minutes * 150)
    text_rule = ("The text is already the narration. Keep its wording, facts and order exactly; only split it into "
                 "lines and scenes (you may drop stage directions). Do not add or remove claims."
                 if keep_text else
                 f"Rewrite the text as clear spoken narration of about {words} words, faithful to its facts; never "
                 "invent studies, numbers or quotes.")
    return f"""You turn a text into a scene-by-scene script for "{channel['channel_name']}": animated explainer videos that teach science and psychology through small everyday stories with a few recurring characters.
{text_rule}
- Language of every spoken line: {LANG_NAMES.get(lang, lang)}. Narration lines use speaker "{NARRATOR}". Characters may say a short line now and then when it fits; a line's speaker is "{NARRATOR}" or a cast id on stage in that scene.
- Each scene is one visual idea that a 10-second animated clip can show: 1-3 lines and about 15-28 spoken words. Split long paragraphs into several scenes.
- Show, don't tell: for each idea pick a concrete everyday moment (scrolling a phone at night, a craving for a cigarette, a worried mind) or a simple visual metaphor (a glowing brain, a loop of three steps). Keep the same characters through the video.
- cast: the recurring characters (2-4). id = short ascii slug; pick the closest preset ({presets}); kind "human".
- actors: who is visible (0-3), position, pose, expression, action (enter, exit, approach, jump, shake or none). Scenes with only a metaphor or diagram have no actors.
- bg_id: the closest of {", ".join(pack.ids("backgrounds"))} (only a code for the scene's place and day/night); bg_prompt: a short English description of the real place, e.g. "modern bedroom at night". Scenes in the same place in a row keep the same bg_id. camera: slow move.
- props: usually none.
- The first 30 seconds must hook: a surprising question or moment. End with a short summary and an invitation to the next video."""


def _ask(provider: str, system: str, user: str) -> dict:
    if provider == "claude":
        return _call_claude(system, user)
    if provider == "muse":
        return _call_muse(system, user)
    if provider in ("openai", "codex"):
        from . import llm
        return (llm.openai_compatible if provider == "openai" else llm.codex)(system, user, SCENE_SCHEMA)
    raise ValueError(f"Unknown LLM provider: {provider}")


def split_text(text: str, size: int = CHUNK_CHARS) -> list[str]:
    """Parts of at most about `size` characters, cut between paragraphs (then sentences)."""
    pieces = []
    for para in [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]:
        if len(para) <= size:
            pieces.append(para)
            continue
        current = ""
        for sentence in re.split(r"(?<=[.!?…])\s+", para):
            if current and len(current) + len(sentence) > size:
                pieces.append(current.strip())
                current = ""
            current += sentence + " "
        if current.strip():
            pieces.append(current.strip())
    parts, current = [], ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > size:
            parts.append(current)
            current = ""
        current = f"{current}\n\n{piece}" if current else piece
    return parts + ([current] if current else [])


def write_script(story: str, channel: dict, lang: str, minutes: float, provider: str, character=None,
                 genre: str = "story", keep_text: bool = False, cast: list | None = None) -> dict:
    """cast: characters that already exist (e.g. when a missing passage is split into scenes again)."""
    if provider == "offline":
        return _normalize(_offline_script(story, genre), lang)
    parts = split_text(story)
    merged: dict = {"title": None, "cast": list(cast), "scenes": []} if cast else {}
    for k, part in enumerate(parts):
        share = minutes * len(part) / max(1, len(story))
        if genre == "explainer":
            system, user = explainer_prompt(channel, lang, share, keep_text), part
        else:
            system, user = build_prompt(part, channel, lang, share, character, genre)
        if len(parts) > 1 or cast:
            if len(parts) > 1:
                print(f"  part {k + 1}/{len(parts)}...")
            note = [f"This is part {k + 1} of {len(parts)} of "
                    + ("a passage in the middle of one video" if cast else "one video")
                    + "; write scenes for this text only."]
            if k or cast:
                note.append("Continue from what came before: no new opening hook. Reuse these cast ids and looks "
                            "exactly, adding a character only if the text needs one: "
                            + json.dumps(merged["cast"], ensure_ascii=False))
            if k < len(parts) - 1 or cast:
                note.append("Do not end the video or invite viewers to the next video.")
            system = f"{system}\n\n" + "\n".join(note)
        script = _ask(provider, system, user)
        if not merged:
            merged = {"title": script.get("title"), "cast": list(script.get("cast", [])), "scenes": []}
        known = {c.get("id") for c in merged["cast"]}
        merged["cast"] += [c for c in script.get("cast", []) if c.get("id") not in known]
        merged["scenes"] += list(script.get("scenes", []))
    return _normalize(merged, lang)
