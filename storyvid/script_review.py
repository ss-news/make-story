"""Review rounds for scenes.json before a person approves it: an AI scores the script against the source text,
lists problems per scene, and can revise those scenes. History: output/<id>/script_reviews.json
(format "storyvid.script-review/1").

    python -m storyvid.script_review review output/<id> [--provider muse|claude|openai|codex]
    python -m storyvid.script_review revise output/<id>      fix the issues of the last review
    python -m storyvid.script_review auto output/<id> --rounds 2   review, revise, review... until it passes

A revision keeps the previous script as scenes.round<N>.json and clears the approval; the person still reviews
and approves the final script (web UI, tab Kịch bản).
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "storyvid.script-review/1"
PASS_SCORE = 80
WORDS_PER_SECOND = {"vi": 3.8, "en": 2.6}  # narration speed with pauses (VieNeu, Vietnamese syllables), for estimates
MAX_SCENE_SECONDS = 11  # longer narration does not fit a 10-second clip, even slowed down a little
REVISE_BATCH = 8       # scenes rewritten per request
CRITERIA = {
    "hook": "Mở đầu cuốn hút (30 giây đầu)",
    "accuracy": "Đúng nội dung nguồn và khoa học, không bịa",
    "clarity": "Dễ hiểu, giải thích rõ",
    "flow": "Mạch lạc, nhịp và chuyển ý",
    "visual": "Mỗi cảnh hình dung được thành clip, nhân vật nhất quán",
    "safety": "Tránh nội dung dễ bị Muse từ chối",
}
SEVERITIES = ["major", "minor"]
REVIEW_SCHEMA = {
    "type": "object", "required": ["criteria", "issues", "summary"],
    "properties": {
        "criteria": {"type": "array", "items": {"type": "object", "required": ["id", "score", "comment"], "properties": {
            "id": {"type": "string", "enum": list(CRITERIA)}, "score": {"type": "integer", "minimum": 1, "maximum": 10},
            "comment": {"type": "string"}}}},
        "issues": {"type": "array", "items": {"type": "object", "required": ["scene", "severity", "problem", "fix"],
                                              "properties": {"scene": {"type": ["integer", "null"]},
                                                             "severity": {"type": "string", "enum": SEVERITIES},
                                                             "problem": {"type": "string"}, "fix": {"type": "string"}}}},
        "summary": {"type": "string"},
    },
}


def _ask(provider: str, system: str, user: str, schema: dict) -> dict:
    from . import llm
    if provider == "muse":
        from .visuals import muse
        prompt = (f"{system}\n\nReply with only one JSON object matching this schema, no other text, and do not "
                  f"create any image or video in this reply:\n{json.dumps(schema)}\n\n{user}")
        reply = muse("/api/chat", {"prompt": prompt, "timeoutSec": 900}, timeout=1020)
        if not reply.get("ok"):
            raise RuntimeError(f"Muse did not answer: {reply.get('error')}")
        return llm.extract_json(reply["text"])
    if provider == "openai":
        return llm.openai_compatible(system, user, schema)
    if provider == "codex":
        return llm.codex(system, user, schema)
    if provider == "claude":
        import anthropic, os  # noqa: E401
        response = anthropic.Anthropic().messages.create(
            model=os.environ.get("CLAUDE_MODEL", "claude-opus-5-5"), max_tokens=16000, system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}})
        return json.loads(next(b.text for b in response.content if b.type == "text"))
    raise ValueError(f"Unknown provider: {provider}")


def words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def local_checks(script: dict, minutes: float) -> tuple[dict, list[dict]]:
    """Length and scene-size checks that need no AI: (length criterion, issues)."""
    rate = WORDS_PER_SECOND.get(script.get("lang"), 2.6)
    total = sum(words(l["text"]) for s in script["scenes"] for l in s["lines"])
    seconds = total / rate
    target = minutes * 60
    ratio = seconds / target if target else 1
    score = max(1, min(10, round(10 - abs(1 - ratio) * 20)))
    issues = []
    if ratio < 0.9:
        issues.append({"scene": None, "severity": "major", "problem": f"Ước tính {seconds / 60:.1f} phút, ngắn hơn mục "
                       f"tiêu {minutes:g} phút.", "fix": "Thêm ví dụ hoặc giải thích để đủ thời lượng."})
    for i, s in enumerate(script["scenes"]):
        n = sum(words(l["text"]) for l in s["lines"])
        if n / rate > MAX_SCENE_SECONDS:
            issues.append({"scene": i, "severity": "minor", "problem": f"Cảnh dài {n} từ (~{n / rate:.0f} giây), "
                           "quá một clip 10 giây.", "fix": "Tách thành hai cảnh, mỗi cảnh một hình."})
    return ({"id": "length", "label": "Thời lượng so với mục tiêu", "score": score,
             "comment": f"Ước tính {seconds / 60:.1f} phút / mục tiêu {minutes:g} phút, {len(script['scenes'])} cảnh."},
            issues)


def _plain(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


def coverage_issues(script: dict, source: str) -> list[dict]:
    """For a kept narration: source sentences missing from the script, grouped, each anchored to the scene that
    should come right before them (None = before the first scene)."""
    sentences = [x.strip() for x in re.split(r"(?<=[.!?…])\s+|\n+", source) if _plain(x)]
    scene_text = [_plain(" ".join(l["text"] for l in sc["lines"])) for sc in script["scenes"]]
    issues, anchor, missing = [], None, []

    def flush():
        if missing:
            text = " ".join(missing)
            where = f"sau cảnh {anchor + 1}" if anchor is not None else "ở đầu video"
            issues.append({"scene": anchor, "severity": "major", "missing": text,
                           "problem": f"Thiếu lời kể gốc ({len(missing)} câu): "
                           f"«{text[:300]}{'…' if len(text) > 300 else ''}»",
                           "fix": f"Chèn nguyên văn các câu này {where}, thành cảnh mới (15-28 từ mỗi cảnh): {text}"})
            missing.clear()

    for sentence in sentences:
        key = _plain(sentence)
        # a long sentence may be split over neighbouring scenes, so look through a window of three
        found = next((i for i in range(len(scene_text)) if key in " ".join(scene_text[i:i + 3])), None)
        if found is None:
            missing.append(sentence)
        else:
            flush()
            anchor = found
    flush()
    return issues


def compact(script: dict, indices=None) -> list[dict]:
    names = {c["id"]: c["name"] for c in script.get("cast", [])}
    return [{"scene": i, "place": s["bg_prompt"], "on_stage": [names.get(a["id"], a["id"]) for a in s["actors"]],
             "lines": [f"{names.get(l['speaker'], l['speaker'])}: {l['text']}" for l in s["lines"]]}
            for i, s in enumerate(script["scenes"]) if indices is None or i in indices]


def review(script: dict, source: str, minutes: float, provider: str, genre: str, keep_text: bool = False) -> dict:
    system = ("You are a strict script editor for an animated YouTube "
              + ("science / psychology explainer" if genre == "explainer" else "story") + " channel. Score the script "
              "against the source text from 1 to 10 on each criterion, then list concrete problems with the scene "
              "index (0-based; null for the whole video) and how to fix them. Major = must fix before production "
              "(wrong or invented facts, confusing explanation, weak opening, a scene that cannot be shown). Write "
              "comments, problems and fixes in Vietnamese. Criteria: "
              + "; ".join(f"{k}: {v}" for k, v in CRITERIA.items()))
    user = json.dumps({"source_text": source, "script": {"title": script["title"], "cast": script.get("cast", []),
                                                          "scenes": compact(script)}}, ensure_ascii=False)
    reply = _ask(provider, system, user, REVIEW_SCHEMA)
    criteria = [{"id": c["id"], "label": CRITERIA[c["id"]], "score": max(1, min(10, int(c.get("score", 5)))),
                 "comment": str(c.get("comment", ""))} for c in reply.get("criteria", []) if c.get("id") in CRITERIA]
    issues = [{"scene": x["scene"] if isinstance(x.get("scene"), int) and 0 <= x["scene"] < len(script["scenes"])
               else None, "severity": x.get("severity") if x.get("severity") in SEVERITIES else "minor",
               "problem": str(x.get("problem", "")), "fix": str(x.get("fix", ""))}
              for x in reply.get("issues", []) if str(x.get("problem", "")).strip()]
    length, local = local_checks(script, minutes)
    criteria.append(length)
    issues += local
    if keep_text and source:
        missing = coverage_issues(script, source)
        criteria.append({"id": "coverage", "label": "Giữ đủ lời kể gốc", "score": max(1, 10 - 2 * len(missing)),
                         "comment": "Đủ mọi câu." if not missing else f"Thiếu {len(missing)} đoạn so với lời kể gốc."})
        issues += missing
    score = round(sum(c["score"] for c in criteria) / max(1, len(criteria)) * 10)
    verdict = "pass" if score >= PASS_SCORE and not any(i["severity"] == "major" for i in issues) else "fix"
    return {"kind": "review", "provider": provider, "score": score, "verdict": verdict, "criteria": criteria,
            "issues": issues, "summary": str(reply.get("summary", ""))}


def revise(script: dict, source: str, issues: list[dict], provider: str, genre: str, lang: str) -> tuple[dict, list]:
    """Rewrite the scenes the issues point at (whole-video issues touch the opening). A scene may become several."""
    from .script import LANG_NAMES, SCENE_SCHEMA, _normalize
    from .script import split_text, write_script
    # missing narration is split into scenes again (in small parts) and inserted after its anchor scene
    inserts: dict = {}
    for issue in [i for i in issues if i.get("missing")]:
        print(f"  re-splitting {len(issue['missing'])} characters of missing narration...")
        part = write_script(issue["missing"], {"channel_name": "", "host": {}}, lang, 1, provider,
                            genre=genre, keep_text=True, cast=script.get("cast", []))
        inserts[issue["scene"]] = part["scenes"]
    issues = [i for i in issues if not i.get("missing")]
    whole = [i for i in issues if i["scene"] is None]
    targets = sorted({i["scene"] for i in issues if i["scene"] is not None} | ({0, 1, 2} if whole else set()))
    targets = [i for i in targets if i < len(script["scenes"])]
    scene_schema = SCENE_SCHEMA["properties"]["scenes"]["items"]
    schema = {"type": "object", "required": ["replacements"], "properties": {"replacements": {"type": "array", "items": {
        "type": "object", "required": ["index", "scenes"],
        "properties": {"index": {"type": "integer"}, "scenes": {"type": "array", "items": scene_schema}}}}}}
    replacements: dict[int, list] = {}
    for start in range(0, len(targets), REVISE_BATCH):
        batch = targets[start:start + REVISE_BATCH]
        system = (f"You revise scenes of an animated {'explainer' if genre == 'explainer' else 'story'} script. For "
                  "each scene index given, return the replacement scene(s) in the same JSON shape: one scene, or "
                  "several when a scene is too long for one 10-second clip. Fix exactly the listed problems, stay "
                  "faithful to the source text, never invent facts and keep the cast ids. When an issue says "
                  "narration is missing, return the scene itself followed by new scenes that speak the missing "
                  "sentences word for word (missing text that belongs before scene 0 goes before its own content). "
                  f"Write spoken lines in {LANG_NAMES.get(lang, lang)}.")
        user = json.dumps({"source_text": source, "cast": script.get("cast", []),
                           "scenes": {i: script["scenes"][i] for i in batch},
                           "neighbours": compact(script, {j for i in batch for j in (i - 1, i + 1)} - set(batch)),
                           "issues": [i for i in issues if i["scene"] in batch or i["scene"] is None]},
                          ensure_ascii=False)
        print(f"  revising scenes {', '.join(str(i + 1) for i in batch)}...")
        for item in _ask(provider, system, user, schema).get("replacements", []):
            if item.get("index") in batch and item.get("scenes"):
                replacements[item["index"]] = item["scenes"]
    scenes = list(inserts.get(None, []))
    for i, s in enumerate(script["scenes"]):
        scenes += replacements.get(i, [s]) + inserts.get(i, [])
    revised = _normalize({**script, "scenes": scenes}, lang)
    return revised, sorted(set(replacements) | {i for i in inserts if i is not None})


def load(project: Path) -> tuple[dict, dict, str, dict]:
    script = json.loads((project / "scenes.json").read_text(encoding="utf-8"))
    meta = json.loads((project / "meta.json").read_text(encoding="utf-8")) if (project / "meta.json").exists() else {}
    source = (project / "story.txt").read_text(encoding="utf-8") if (project / "story.txt").exists() else ""
    path = project / "script_reviews.json"
    history = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"format": FORMAT, "rounds": []}
    return script, meta, source, history


def record(project: Path, history: dict, entry: dict) -> dict:
    entry = {"round": len(history["rounds"]) + 1, "at": int(time.time()), **entry}
    history["rounds"].append(entry)
    (project / "script_reviews.json").write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
    return entry


def do_review(project: Path, provider: str) -> dict:
    script, meta, source, history = load(project)
    print(f"[review] {len(script['scenes'])} scenes ({provider})...")
    entry = record(project, history, review(script, source, float(meta.get("minutes", 2)), provider,
                                            meta.get("genre", "story"), bool(meta.get("keep_text"))))
    print(f"  score {entry['score']}/100 -> {entry['verdict']}; {len(entry['issues'])} issue(s)")
    for c in entry["criteria"]:
        print(f"    {c['score']:>2}/10 {c['label']}: {c['comment']}")
    for i in entry["issues"]:
        where = f"scene {i['scene'] + 1}" if i["scene"] is not None else "whole video"
        print(f"    [{i['severity']}] {where}: {i['problem']}")
    return entry


def do_revise(project: Path, provider: str) -> dict | None:
    from .check import check_script
    script, meta, source, history = load(project)
    last = next((r for r in reversed(history["rounds"]) if r["kind"] == "review"), None)
    if not last or not last["issues"]:
        print("Nothing to revise: run a review first (or the last review found no issues)")
        return None
    print(f"[revise] {len(last['issues'])} issue(s) from round {last['round']} ({provider})...")
    revised, changed = revise(script, source, last["issues"], provider, meta.get("genre", "story"),
                              meta.get("lang") or script.get("lang"))
    backup = project / f"scenes.round{len(history['rounds']) + 1}.json"
    backup.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (project / "scenes.json").write_text(json.dumps(revised, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if check_script(project / "scenes.json") == 1:
        backup.replace(project / "scenes.json")
        raise SystemExit("The revised script broke the standard; the previous version was restored")
    meta.pop("approved_script", None)  # a changed script needs a new human review
    (project / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    entry = record(project, history, {"kind": "revise", "provider": provider, "from_round": last["round"],
                                      "changed_scenes": changed, "scenes_before": len(script["scenes"]),
                                      "scenes_after": len(revised["scenes"]), "backup": backup.name})
    print(f"  rewrote {len(changed)} scene(s): {len(script['scenes'])} -> {len(revised['scenes'])} scenes "
          f"(previous version: {backup.name})")
    return entry


def main() -> None:
    from .cli import load_env
    load_env(ROOT / ".env")
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["review", "revise", "auto"])
    ap.add_argument("project")
    ap.add_argument("--provider", choices=["muse", "claude", "openai", "codex"], default="muse")
    ap.add_argument("--rounds", type=int, default=2, help="auto: at most this many revisions")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    if args.action == "review":
        do_review(project, args.provider)
    elif args.action == "revise":
        do_revise(project, args.provider)
    else:
        entry = do_review(project, args.provider)
        for _ in range(max(0, args.rounds)):
            if entry["verdict"] == "pass" or not do_revise(project, args.provider):
                break
            entry = do_review(project, args.provider)
        print(f"Final: {entry['score']}/100, {entry['verdict']}. A person still reads and approves the script.")


if __name__ == "__main__":
    main()
