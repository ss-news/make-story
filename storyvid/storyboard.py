"""Storyboard: plan the story the way a film is planned, before scenes.json is written.

    python -m storyvid.storyboard show output/<id>      print storyboard.json as a shot list

Pass 1, treatment: the whole story becomes a logline, a protagonist (what they want, what stands in the way, what
is at stake), the cold open (the strongest moment, shown first, ending on a question), a beat sheet mapped to the
source (setup, inciting incident, rising complications, midpoint, crisis and choice, climax, resolution) and the
setups that pay off later.
Pass 2, shots: each part of the source becomes film scenes (a slugline, what the scene is for, the conflict in it
and how it turns), each broken into shots: size, angle, camera movement, composition, the action seen, the lines
heard, transition and sound.

One shot is one 10-second clip and becomes one scene of scenes.json (storyvid.scenes/1, unchanged).
storyboard.json (format "storyvid.storyboard/1") keeps the rest; storyvid.visuals frames each image and clip from
it, and the web UI shows it in tab Kịch bản. A shot is matched to its scene by the spoken text, so scenes edited
later simply lose their shot notes.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FORMAT = "storyvid.storyboard/1"
SIZES = {"EWS": "extreme wide shot", "WS": "wide shot", "FS": "full shot", "MS": "medium shot",
         "MCU": "medium close-up", "CU": "close-up", "ECU": "extreme close-up", "INSERT": "insert shot of an object"}
ANGLES = {"eye": "eye-level", "low": "low angle", "high": "high angle", "overhead": "top-down overhead shot",
          "ots": "over-the-shoulder", "pov": "point-of-view shot", "dutch": "dutch tilt"}
MOVES = {"static": "locked-off camera", "push_in": "slow push-in", "pull_out": "slow pull-back",
         "pan_left": "slow pan to the left", "pan_right": "slow pan to the right", "tilt_up": "slow tilt up",
         "tilt_down": "slow tilt down", "track": "tracking shot following the subject",
         "handheld": "handheld camera, slight shake", "crane_up": "crane up, revealing the place",
         "orbit": "slow orbit around the subject"}
CAMERA_OF = {"push_in": "zoom_in", "pull_out": "zoom_out", "crane_up": "zoom_out", "pan_left": "pan_left",
             "pan_right": "pan_right"}  # scenes.json "camera" for the stage renderer; anything else is static
TRANSITIONS = ["cut", "match_cut", "smash_cut", "dissolve", "fade_in", "fade_out"]
LINKS = {"continuous": "liền mạch (máy chạy tiếp, không cắt)", "cut_on_action": "cắt theo hành động",
         "eyeline": "cắt theo hướng nhìn", "reaction": "cắt sang phản ứng", "match_cut": "cắt khớp hình",
         "cutaway": "cắt sang chi tiết", "new_scene": "sang cảnh mới"}
BEATS = ["cold_open", "setup", "inciting", "rising", "midpoint", "crisis", "climax", "resolution", "outro"]
BEAT_LABELS = {"cold_open": "Mở đầu nóng", "setup": "Giới thiệu", "inciting": "Biến cố khởi đầu",
               "rising": "Leo thang", "midpoint": "Bước ngoặt giữa", "crisis": "Khủng hoảng, lựa chọn",
               "climax": "Cao trào", "resolution": "Kết", "outro": "Lời chào"}
SECONDS_PER_SHOT = 7


def _rate(lang: str) -> float:
    from .script_review import WORDS_PER_SECOND
    return WORDS_PER_SECOND.get(lang, 2.6)


def _schemas() -> tuple[dict, dict]:
    from .script import SCENE_SCHEMA
    scene = SCENE_SCHEMA["properties"]["scenes"]["items"]["properties"]
    string = {"type": "string"}
    enum = lambda values: {"type": "string", "enum": list(values)}  # noqa: E731
    obj = lambda props: {"type": "object", "properties": props, "required": list(props),  # noqa: E731
                         "additionalProperties": False}
    treatment = obj({
        "title": string, "logline": string,
        "protagonist": string, "want": string, "obstacle": string, "stakes": string, "theme": string,
        "cold_open": obj({"moment": string, "question": string}),
        "cast": SCENE_SCHEMA["properties"]["cast"],
        "beats": {"type": "array", "items": obj({"beat": enum(BEATS), "summary": string, "source": string,
                                                 "seconds": {"type": "integer"}})},
        "setups": {"type": "array", "items": obj({"setup": string, "payoff": string})},
    })
    shot = obj({"link": enum(LINKS), "size": enum(SIZES), "angle": enum(ANGLES), "movement": enum(MOVES),
                "subject": string, "description": string, "start_frame": string, "action": string,
                "performance": string, "end_frame": string, "composition": string, "actors": scene["actors"],
                "props": scene["props"], "lines": scene["lines"], "sound": string, "transition": enum(TRANSITIONS),
                "transition_note": string})
    shots = obj({"scenes": {"type": "array", "items": obj({
        "slug": string, "bg_id": string, "bg_prompt": string, "beat": enum(BEATS), "setting": string,
        "bridge": string, "purpose": string, "conflict": string, "turn": string,
        "shots": {"type": "array", "items": shot}})}})
    return treatment, shots


TREATMENT_SCHEMA, SHOTS_SCHEMA = _schemas()

CRAFT = """How a film script and storyboard are made (follow all of it):
Structure
- Every film scene earns its place in the beat sheet: someone in it wants something, something stands in the way, and the scene ends changed (the turn: good news turns bad, a secret comes out, a choice is made). A stretch of the source with no turn is folded into one or two shots, not a scene of its own.
- Enter late, leave early: start a scene at its first moment of tension, cut away right after its turn.
- Plant every payoff: an object, a rule or a line that matters later gets its own shot (often an INSERT) when it is first seen.
- Escalate: each complication is worse than the one before; the climax answers the cold open's question.
Show, don't tell
- Anything that can be seen is a shot, not narration: "he was afraid" becomes a CU of his hands shaking.
- Narration only bridges time, gives what no image can show (a thought, a rule of the story's world, a date), or asks the hook question; at most about 40% of the spoken words. Where the source narrates what a character does or feels, give that character a short line or a reaction instead; never two narration lines in one shot.
- Dialogue is short and wants something; people do not explain what both of them know. Subtext over statements.
Coverage and the camera
- A new place opens with one establishing shot (EWS or WS); then the camera moves closer as tension rises.
- Emotional peaks in CU or ECU; after a shock, cut to the reaction (a CU of the face that receives it).
- Never three shots of the same size in a row. Keep each character on the same side of frame within a scene (180-degree rule).
- Angles carry meaning: low = power or threat, high = small and vulnerable, dutch = unease, pov = fear of what is seen, ots = two people facing off.
- Movement has a reason: push_in to an idea dawning, pull_out to loneliness or a reveal, track to follow a chase, handheld for panic, static for stillness and dread.
Continuity: the film must play as one piece, never as separate clips
- Each scene opens with a bridge from the one before: a time jump the viewer can read (light, weather, a sound carried over), a character carrying the action into the new place, a match cut, or the question the last scene left. setting: the place, time of day, light, weather and mood in detail.
- Every shot starts where the previous one ended. start_frame repeats what end_frame of the previous shot left (who is where, which way they face, what they hold, the light), seen from this shot's camera. Keep screen direction: someone leaving frame right enters the next shot from frame left; someone looking off-screen left is answered by a shot of what is on the left.
- link says how a shot joins the one before: continuous = the same camera keeps rolling, no cut (only within one place and moment, and the clip starts from the previous clip's last frame); cut_on_action = the movement started at the end of the last shot finishes in this one from a new angle; eyeline = what the character just looked at; reaction = the face that receives what just happened; match_cut = a shape or gesture repeated across a jump; cutaway = a detail in the same moment; new_scene = the first shot of a scene.
- end_frame: the last image of the shot, which hands over to the next one (a turn of the head, a hand reaching out of frame, a door opening, a sound starting).
- transition_note: in the video's language, one sentence on how this shot hands over to the next, e.g. "Ông lão quay phắt ra cửa → cắt theo hướng nhìn sang khung cửa tối".
Shots are clips
- One shot = one clip an image-to-video model makes from a single opening frame: 4-10 seconds, one subject, one clear action that can be filmed (no montage, no time jump, no text on screen, no one speaking to camera). If the action needs "then" or a list of moves, it is two shots.
- description: in the video's language, 2-3 sentences a storyboard artist would draw from: the place, the light, who is where, what happens and the mood.
- action: what moves during the shot, concrete and visual (in English). performance: how each character on screen acts: gesture, where they look, the emotion on the face, how it changes during the shot (in English). composition: where the subject sits in frame, foreground and background, light (in English). start_frame and end_frame in English. subject: who or what the shot is about.
- Every shot has 1-3 lines (narration or dialogue) heard over it; whoever speaks a line is in that shot's actors (no off-screen voices but the narrator); at most {max_words} spoken words per shot. A quiet beat still gets one short line.
- Shorter shots and closer sizes as tension rises; one longer, wider shot to breathe after the climax.
- transition: cut by default; smash_cut out of the cold open or into a shock, match_cut between two shapes or gestures, dissolve for time passing, fade_in to open, fade_out to end.
- sound: what we hear beyond the words (wind, footsteps, a sudden silence), in Vietnamese or English."""


COLD_OPEN = ("the most dangerous, shocking or mysterious moment anywhere in the story (a threat seen or heard, a "
             "confrontation, a reveal), its subject big and clear; never a calm moment such as a ritual, a meal, a "
             "lesson or a greeting")


def _genre(genre: str) -> dict:
    from .script import GENRE_INFO
    return GENRE_INFO[genre if genre in GENRE_INFO and genre != "explainer" else "story"]


def _host(channel: dict, character, genre: str) -> dict:
    from .character_catalog import PRESETS, resolve_character
    info = _genre(genre)
    host = dict(channel.get("host") or {})
    host.setdefault("name", "the host")
    host.setdefault("personality", info["host"])
    if genre != "story":
        host["personality"] = info["host"]
    choice = resolve_character(host, character)
    if choice["preset"] != host.get("preset", "young_man"):
        p = PRESETS[choice["preset"]]
        host["name"] = p["label"].split(" · ")[-1]
        host["personality"] = f"a Vietnamese {p['age']} {'woman' if p['female'] else 'man'}, {info['host']}"
    return host


def treatment_prompt(channel: dict, lang: str, minutes: float, genre: str, character=None) -> str:
    from .character_catalog import PRESETS
    from .script import LANG_NAMES
    info = _genre(genre)
    host = _host(channel, character, genre)
    seconds = int(minutes * 60)
    presets = "; ".join(f"{k} = {v['label']}" for k, v in PRESETS.items())
    return f"""You are the head writer of a film studio, adapting a story into a short film for the YouTube channel "{channel.get('channel_name', '')}"; this one is a {info["video"]}, about {seconds} seconds long. The host {host['name']} ({host['personality']}) narrates over the images.
First write the treatment, the plan every later step follows. Write title, logline, want, obstacle, stakes, theme, cold_open, beat summaries and setups in {LANG_NAMES.get(lang, lang)}.
- logline: one sentence: who, what they want, what stands in the way, what is at stake.
- protagonist: the cast id of the main character; the film follows them. want: what they try to get; obstacle; stakes: what they lose if they fail; theme: what the story is really about, in a few words.
- cold_open: the moment shown first and the question it leaves the viewer with. Pick {info.get("cold_open", COLD_OPEN)}.
- beats: in story order, from {", ".join(BEATS)}; cold_open first, outro last only if the narrator invites viewers to the next story. source = the first words of the source passage the beat comes from (empty for cold_open and outro). seconds = screen time; together about {seconds}.
- setups: things planted early that pay off later.
- cast: every character who appears (not the host). id = short ascii slug, name = how the story calls them. Pick the closest preset ({presets}). {info["cast_rule"]}
Genre rules:
{info["arc"]}
Stay true to the source: keep its events, names and world; cut, merge and reorder only to make it play as a film."""


def shots_prompt(channel: dict, lang: str, minutes: float, genre: str, character=None) -> str:
    from . import pack
    from .script import HOST, LANG_NAMES, MAX_PROPS, NARRATOR, prop_ids
    info = _genre(genre)
    host = _host(channel, character, genre)
    max_words = int(9 * _rate(lang))
    shots = max(1, round(minutes * 60 / SECONDS_PER_SHOT))
    words = int(minutes * 60 * _rate(lang))
    return f"""You are the director and storyboard artist of a short film, a {info["video"]} for the YouTube channel "{channel.get('channel_name', '')}". The treatment is fixed; now break this part of the source into film scenes and shots.
{CRAFT.format(max_words=max_words)}
Format
- scenes: film scenes in screen order. slug: a slugline in {LANG_NAMES.get(lang, lang)}, e.g. "NGOẠI. BỜ SÔNG - ĐÊM" / "EXT. RIVERBANK - NIGHT". beat: which treatment beat it plays. purpose, conflict, turn: one short sentence each, in {LANG_NAMES.get(lang, lang)}.
- bg_id: the closest of {", ".join(pack.ids("backgrounds"))} (only a code for the place and day/night); bg_prompt: a short English description of the real place. camera work goes in the shots.
- This part runs about {int(minutes * 60)} seconds: about {shots} shots and about {words} spoken words in all (count them: a film that is too short fails as much as one that rambles; add reactions and short exchanges rather than narration).
- lines: spoken {LANG_NAMES.get(lang, lang)}; speaker "{NARRATOR}" for {host['name']} the narrator, or a cast id on screen in that shot. The host may appear as actor id "{HOST}" only in the opening and the ending.
- actors: who is visible in the shot (0-3) with position, pose, expression and action (enter, exit, approach, jump, shake, none); an INSERT or a pure landscape has none. props: 0-{MAX_PROPS} of {", ".join(prop_ids())}, usually none.
Genre rules (they win over the craft rules above when the two disagree):
{info["arc"]}"""


def _ask(provider: str, system: str, user: str, schema: dict) -> dict:
    from .script import _ask as ask
    return ask(provider, system, user, schema)


def _plain(text: str) -> str:
    return " ".join(re.findall(r"\w+", str(text).lower()))


def shot_key(lines: list) -> str:
    return _plain(" ".join(str(l.get("text", "")) for l in lines or [] if isinstance(l, dict)))


def write(story: str, channel: dict, lang: str, minutes: float, provider: str, character=None,
          genre: str = "story") -> tuple[dict, dict]:
    """(storyboard, raw script for scenes.json's _normalize): treatment first, then the shots part by part."""
    from .script import split_text
    system = treatment_prompt(channel, lang, minutes, genre, character)
    print("  storyboard: treatment...")
    treatment = _ask(provider, system, story, TREATMENT_SCHEMA)
    cast = list(treatment.get("cast") or [])
    plan = {k: treatment.get(k) for k in ("title", "logline", "protagonist", "want", "obstacle", "stakes", "theme",
                                          "cold_open", "beats", "setups")}
    parts = split_text(story)
    film_scenes: list[dict] = []
    for k, part in enumerate(parts):
        share = minutes * len(part) / max(1, len(story))
        system = shots_prompt(channel, lang, share, genre, character)
        note = [f"This is part {k + 1} of {len(parts)} of the source."]
        if k == 0:
            note.append("Open with the cold open from the treatment (its shots come first even if the moment "
                        "happens later in the story; end it on its question), then go back to the beginning.")
        else:
            note.append("Continue from the shots before: no new cold open, no new establishing of places already "
                        "seen unless the time changed.")
        if k < len(parts) - 1:
            note.append("Do not end the film or invite viewers to the next video.")
        user = json.dumps({"treatment": plan, "cast": cast, "part": part,
                           "previous_shots": [{"slug": s["slug"], "action": sh.get("action"),
                                               "end_frame": sh.get("end_frame"), "lines": sh.get("lines")}
                                              for s in film_scenes[-2:] for sh in s["shots"][-2:]]},
                          ensure_ascii=False)
        if len(parts) > 1:
            print(f"  storyboard: shots, part {k + 1}/{len(parts)}...")
        else:
            print("  storyboard: shots...")
        reply = _ask(provider, f"{system}\n\n" + " ".join(note), user, SHOTS_SCHEMA)
        known = {c.get("id") for c in cast}
        cast += [c for c in reply.get("cast", []) if isinstance(c, dict) and c.get("id") not in known]
        film_scenes += [s for s in reply.get("scenes", []) if isinstance(s, dict)]
    return assemble(plan, cast, film_scenes, lang)


def _pick(value, values, default):
    return value if value in values else default


def on_screen(shot: dict, cast_ids: set) -> tuple[list, list]:
    """scenes.json lets only characters on screen speak: a speaker missing from the shot is added to it (at a free
    position, talking); when the frame is full (3 actors) the line goes to the narrator."""
    from .script import NARRATOR, POSITIONS
    actors = [a for a in shot.get("actors") or [] if isinstance(a, dict)]
    lines = [dict(l) for l in shot.get("lines") or [] if isinstance(l, dict)]
    for line in lines:
        who = line.get("speaker")
        if who == NARRATOR or who not in cast_ids or any(a.get("id") == who for a in actors):
            continue
        free = [p for p in POSITIONS if p not in {a.get("position") for a in actors}]
        if len(actors) < 3 and free:
            actors.append({"id": who, "position": free[0], "pose": "talk", "expression": "neutral", "action": "none"})
        else:
            line["speaker"] = NARRATOR
    return actors, lines


def assemble(plan: dict, cast: list, film_scenes: list, lang: str) -> tuple[dict, dict]:
    """Shots -> scenes.json scenes (one per shot with spoken lines) and the storyboard that remembers each shot."""
    from .script import _normalize
    scenes, board = [], []
    for s in film_scenes:
        kept = []
        for sh in s.get("shots") or []:
            if not isinstance(sh, dict) or not shot_key(sh.get("lines")):
                continue  # scenes.json needs words in every scene; a silent shot cannot become one
            movement = _pick(sh.get("movement"), MOVES, "static")
            actors, lines = on_screen(sh, {c.get("id") for c in cast if isinstance(c, dict)})
            scenes.append({"bg_id": s.get("bg_id"), "bg_prompt": s.get("bg_prompt"),
                           "camera": CAMERA_OF.get(movement, "static"), "actors": actors,
                           "props": sh.get("props") or [], "lines": lines})
            text = lambda key: str(sh.get(key) or "").strip()  # noqa: E731
            link = _pick(sh.get("link"), LINKS, "cut_on_action")
            if not kept:
                link = "new_scene"
            elif link == "new_scene":
                link = "cut_on_action"
            kept.append({"link": link, "size": _pick(sh.get("size"), SIZES, "MS"),
                         "angle": _pick(sh.get("angle"), ANGLES, "eye"), "movement": movement,
                         **{k: text(k) for k in ("subject", "description", "start_frame", "action", "performance",
                                                 "end_frame", "composition", "sound")},
                         "transition": _pick(sh.get("transition"), TRANSITIONS, "cut"),
                         "transition_note": text("transition_note"), "lines": sh.get("lines")})
        if kept:
            board.append({"slug": str(s.get("slug") or ""), "beat": _pick(s.get("beat"), BEATS, "rising"),
                          **{k: str(s.get(k) or "").strip() for k in ("setting", "bridge", "purpose", "conflict",
                                                                      "turn")},
                          "shots": kept})
    script = _normalize({"title": plan.get("title"), "cast": cast, "scenes": scenes}, lang)
    # _normalize keeps every scene that has words, in order: shot n is scene n
    n = 0
    for s in board:
        for sh in s["shots"]:
            sh["scene"] = n
            sh["lines"] = script["scenes"][n]["lines"]
            n += 1
    storyboard = {"format": FORMAT, "scenes_file": "scenes.json", **{k: v for k, v in plan.items() if v is not None},
                  "scenes": board}
    return storyboard, script


def load(project: Path) -> dict | None:
    path = project / "storyboard.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) and data.get("format") == FORMAT else None


def aligned(storyboard: dict | None, script: dict) -> list[dict | None]:
    """For each scene of scenes.json, its shot (with the film scene's slug and beat), matched by spoken text."""
    if not storyboard:
        return [None] * len(script.get("scenes", []))
    by_text: dict[str, list] = {}
    previous = None
    for s in storyboard.get("scenes", []):
        for sh in s.get("shots", []):
            by_text.setdefault(shot_key(sh.get("lines")), []).append(
                {**{k: v for k, v in sh.items() if k not in ("lines", "scene")}, "slug": s.get("slug", ""),
                 "beat": s.get("beat", ""), "setting": s.get("setting", ""),
                 "previous_end": (previous or {}).get("end_frame", "")})
            previous = sh
    out = []
    for sc in script.get("scenes", []):
        found = by_text.get(shot_key(sc.get("lines")))
        out.append(found.pop(0) if found else None)
    return out


def describe(shot: dict) -> str:
    """The shot in film words, in English, for image and video prompts."""
    parts = [f"{SIZES.get(shot.get('size'), 'medium shot')}, {ANGLES.get(shot.get('angle'), 'eye-level')}"]
    if shot.get("composition"):
        parts.append(shot["composition"])
    return ". ".join(parts)


def brief(shot: dict) -> dict:
    """The shot for the prompt writer, in plain film words."""
    joins = {"continuous": "the same camera keeps rolling from the previous shot, no cut",
             "cut_on_action": "a cut on action: the movement from the previous shot continues from a new angle",
             "eyeline": "a cut to what the character in the previous shot was looking at",
             "reaction": "a cut to the reaction of the person receiving what just happened",
             "match_cut": "a match cut: the shape or gesture of the previous shot's end repeats here",
             "cutaway": "a cutaway to a detail in the same moment", "new_scene": "the first shot of a new scene"}
    return {"framing": f"{SIZES.get(shot.get('size'), 'medium shot')}, {ANGLES.get(shot.get('angle'), 'eye-level')}",
            "camera_move": MOVES.get(shot.get("movement"), "locked-off camera"),
            "joins_previous": joins.get(shot.get("link"), joins["cut_on_action"]),
            **{k: shot[k] for k in ("subject", "start_frame", "action", "performance", "end_frame", "composition",
                                    "previous_end") if shot.get(k)}}


def summary(project: Path, script: dict | None) -> dict | None:
    """What the web UI shows: the treatment and each scene's shot."""
    board = load(project)
    if not board or not script:
        return None
    return {**{k: board.get(k) for k in ("logline", "protagonist", "want", "obstacle", "stakes", "theme",
                                         "cold_open", "beats", "setups")},
            "beat_labels": BEAT_LABELS, "links": LINKS, "sizes": SIZES, "angles": ANGLES, "moves": MOVES,
            "shots": [{**{k: v for k, v in sh.items() if k not in ("lines", "scene")}, "key": shot_key(sh.get("lines")),
                       "slug": s.get("slug", ""), "beat": s.get("beat", ""), "purpose": s.get("purpose", ""),
                       "setting": s.get("setting", ""), "bridge": s.get("bridge", ""),
                       "conflict": s.get("conflict", ""), "turn": s.get("turn", ""), "first": j == 0}
                      for s in board.get("scenes", []) for j, sh in enumerate(s.get("shots", []))]}


def show(project: Path) -> None:
    board = load(project)
    if not board:
        raise SystemExit(f"No storyboard.json in {project}")
    print(f"{board.get('title', '')}\n{board.get('logline', '')}")
    for key in ("want", "obstacle", "stakes", "theme"):
        if board.get(key):
            print(f"  {key}: {board[key]}")
    for b in board.get("beats") or []:
        print(f"  [{BEAT_LABELS.get(b.get('beat'), b.get('beat'))}] {b.get('summary', '')} ({b.get('seconds', '?')}s)")
    for s in board.get("scenes", []):
        print(f"\n{s['slug']}  ({BEAT_LABELS.get(s['beat'], s['beat'])})")
        for key, label in (("bridge", "nối từ cảnh trước"), ("setting", "bối cảnh"), ("purpose", "mục đích"),
                           ("conflict", "xung đột"), ("turn", "bước ngoặt")):
            if s.get(key):
                print(f"  {label}: {s[key]}")
        for sh in s["shots"]:
            words = " / ".join(f"{l['speaker']}: {l['text']}" for l in sh["lines"])
            print(f"  {sh['scene'] + 1:>3}. [{LINKS.get(sh.get('link'), '')}] {sh['size']} · {sh['angle']} · "
                  f"{sh['movement']} · {sh['transition']}")
            for key in ("description", "performance", "end_frame"):
                if sh.get(key):
                    print(f"       {key}: {sh[key]}")
            print(f"       lời: {words}")
            if sh.get("transition_note"):
                print(f"       → {sh['transition_note']}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["show"])
    ap.add_argument("project")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    show(Path(args.project))


if __name__ == "__main__":
    main()
