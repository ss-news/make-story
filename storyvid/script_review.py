"""Review rounds for scenes.json before a person approves it: an AI scores the script against the source text,
lists problems per scene, and can revise those scenes. History: output/<id>/script_reviews.json
(format "storyvid.script-review/1").

    python -m storyvid.script_review review output/<id> [--provider muse|claude|openai|codex]
    python -m storyvid.script_review revise output/<id>      fix the issues of the last review
    python -m storyvid.script_review auto output/<id> --rounds 2   review, revise, review... until it passes
    python -m storyvid.script_review polish output/<id>     before splitting: critique the storytelling language of
                                                             story.txt and rewrite it once, keeping every fact

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
    "accuracy": "Đúng nội dung nguồn, không bịa (video kiến thức: đúng khoa học)",
    "clarity": "Dễ hiểu, giải thích rõ",
    "flow": "Mạch lạc, nhịp và chuyển ý",
    "structure": "Cấu trúc phim: nhân vật chính có mục tiêu, trở ngại, leo thang, cao trào, kết",
    "cinema": "Ngôn ngữ phim: cho xem thay vì kể, mỗi cảnh có xung đột và bước ngoặt, thoại có ý đồ",
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


NARRATION_SHARE = 0.6  # story and drama: above this the video is read aloud, not acted
TELLING_RUN = 3        # scenes in a row with only narration and nobody on screen


def telling_issues(script: dict) -> list[dict]:
    """Show, don't tell, measured: too much narration overall, or long stretches of narration over empty places."""
    issues = []
    spoken = [(l["speaker"], words(l["text"])) for s in script["scenes"] for l in s["lines"]]
    total = sum(n for _, n in spoken)
    told = sum(n for who, n in spoken if who == "narrator")
    if total and told / total > NARRATION_SHARE:
        issues.append({"scene": None, "severity": "minor", "problem": f"Lời dẫn chiếm {told / total:.0%} số chữ: "
                       "video thành đọc truyện, nhân vật ít diễn.", "fix": "Đổi những đoạn tả hành động, cảm xúc "
                       "thành thoại hoặc hành động trên hình; lời dẫn chỉ để nối thời gian và đặt câu hỏi."})
    run = []
    for i, s in enumerate(script["scenes"] + [None]):
        if s is not None and not s["actors"] and all(l["speaker"] == "narrator" for l in s["lines"]):
            run.append(i)
            continue
        if len(run) >= TELLING_RUN:
            issues.append({"scene": run[0], "severity": "minor", "problem": f"Cảnh {run[0] + 1}–{run[-1] + 1}: "
                           f"{len(run)} cảnh liền chỉ có lời dẫn trên nền trống.", "fix": "Đưa nhân vật vào làm "
                           "điều lời dẫn đang kể, hoặc gộp lại còn một cảnh."})
        run = []
    return issues


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
        # search forward from the last match, so a sentence said twice must be there twice
        start = anchor if anchor is not None else 0
        found = next((i for i in range(start, len(scene_text)) if key in " ".join(scene_text[i:i + 3])), None)
        if found is None:
            missing.append(sentence)
        else:
            flush()
            # anchor on the scene where the sentence ends, not where its window starts
            anchor = next(j for j in range(found, min(found + 3, len(scene_text)))
                          if key in " ".join(scene_text[found:j + 1]))
    flush()
    return issues


def dedupe(script: dict) -> tuple[dict, list[int]]:
    """Drop spoken lines that repeat narration already said (exactly, or as part of the two scenes before);
    scenes left without lines go too. Returns the script and the original indices of scenes that changed."""
    import copy
    out, changed, said = copy.deepcopy(script), [], []
    kept = []
    for i, sc in enumerate(out["scenes"]):
        recent = " ".join(said[-2:])
        lines = []
        for line in sc["lines"]:
            key = _plain(line["text"])
            n = len(key.split())
            # short phrases ("đó là hành vi") may repeat on purpose; only a long one is a repeat anywhere
            if (n >= 3 and key in recent) or (n >= 8 and key in " ".join(said)):
                continue
            lines.append(line)
        if len(lines) != len(sc["lines"]):
            changed.append(i)
        if lines:
            text = _plain(" ".join(l["text"] for l in lines))
            # the scene before said a shorter cut of the same narration: keep only the fuller one
            if kept and len(said[-1].split()) >= 3 and said[-1] in text:
                kept.pop()
                said.pop()
                changed.append(i - 1)
            kept.append({**sc, "lines": lines})
            said.append(text)
    out["scenes"] = kept
    return out, changed


def source_order(script: dict, source: str) -> tuple[dict, list[int]]:
    """With a kept narration the right order is the source's: sort scenes by where their first line appears in it
    (scenes not found keep their place next to the scene before). Returns the script and the moved indices."""
    plain_source = _plain(source)

    def places(text: str) -> list[int]:
        return [m.start() for m in re.finditer(re.escape(text), plain_source)] if text else []

    keys, last = [], 0.0
    for sc in script["scenes"]:
        # the whole scene's narration is usually unique; a line like "I am Cu Rua" can appear twice, so among
        # several matches take the first one after the scene before
        found = places(_plain(" ".join(l["text"] for l in sc["lines"]))) or \
            (places(_plain(sc["lines"][0]["text"])) if sc["lines"] else [])
        pos = next((p for p in found if p >= last), found[0]) if found else -1
        last = float(pos) if pos >= 0 else last + 0.001
        keys.append(last)
    order = sorted(range(len(keys)), key=lambda i: (keys[i], i))
    moved = [i for k, i in enumerate(order) if i != k]
    return {**script, "scenes": [script["scenes"][i] for i in order]}, moved


def compact(script: dict, indices=None) -> list[dict]:
    names = {c["id"]: c["name"] for c in script.get("cast", [])}
    return [{"scene": i, "place": s["bg_prompt"], "on_stage": [names.get(a["id"], a["id"]) for a in s["actors"]],
             "lines": [f"{names.get(l['speaker'], l['speaker'])}: {l['text']}" for l in s["lines"]]}
            for i, s in enumerate(script["scenes"]) if indices is None or i in indices]


def review(script: dict, source: str, minutes: float, provider: str, genre: str, keep_text: bool = False) -> dict:
    from .script import GENRE_INFO
    system = ("You are a strict script editor for an animated YouTube video, a "
              + GENRE_INFO.get(genre, GENRE_INFO["story"])["video"] + ". Score the script "
              "against the source text from 1 to 10 on each criterion, then list concrete problems with the scene "
              "index (0-based; null for the whole video) and how to fix them. Major = must fix before production "
              "(wrong or invented facts, confusing explanation, weak opening, a scene that cannot be shown). Judge it as "
              "a film: a protagonist who wants something against a rising obstacle, scenes that each turn, things "
              "shown on screen rather than told by the narrator, dialogue that wants something. Write "
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
    if genre in ("story", "drama", "comedy"):
        issues += telling_issues(script)
    if keep_text and source:
        _, moved = source_order(script, source)
        if moved:
            issues.append({"scene": None, "severity": "major", "problem": f"{len(moved)} cảnh không theo thứ tự của "
                           "lời kể gốc.", "fix": "Sắp lại cảnh theo thứ tự lời kể gốc."})
        _, repeated = dedupe(script)
        issues += [{"scene": i, "severity": "major", "problem": "Lời kể lặp lại câu đã nói ở cảnh trước.",
                    "fix": "Bỏ câu lặp."} for i in repeated]
        missing = coverage_issues(script, source)
        criteria.append({"id": "coverage", "label": "Giữ đủ lời kể gốc", "score": max(1, 10 - 2 * len(missing)),
                         "comment": "Đủ mọi câu." if not missing else f"Thiếu {len(missing)} đoạn so với lời kể gốc."})
        issues += missing
    score = round(sum(c["score"] for c in criteria) / max(1, len(criteria)) * 10)
    verdict = "pass" if score >= PASS_SCORE and not any(i["severity"] == "major" for i in issues) else "fix"
    return {"kind": "review", "provider": provider, "score": score, "verdict": verdict, "criteria": criteria,
            "issues": issues, "summary": str(reply.get("summary", ""))}


def revise(script: dict, source: str, issues: list[dict], provider: str, genre: str, lang: str,
           keep_text: bool = False) -> tuple[dict, list]:
    """Rewrite the scenes the issues point at (whole-video issues touch the opening). A scene may become several.

    keep_text: the narration is fixed. The AI may only restage scenes or split them (a replacement whose spoken
    text differs from the scene's is dropped); repeated lines are removed and missing source sentences are split
    into scenes again and inserted, by the tool itself."""
    from .script import GENRE_INFO, LANG_NAMES, SCENE_SCHEMA, _normalize
    from .script import write_script
    if keep_text:  # missing and repeated narration are fixed by the tool below, not by the AI
        issues = [i for i in issues if not i.get("missing") and not i["problem"].startswith("Lời kể lặp lại")]
    whole = [i for i in issues if i["scene"] is None and not (keep_text and "thứ tự" in i["problem"])]
    targets = sorted({i["scene"] for i in issues if i["scene"] is not None} | ({0, 1, 2} if whole else set()))
    targets = [i for i in targets if i < len(script["scenes"])]
    scene_schema = SCENE_SCHEMA["properties"]["scenes"]["items"]
    schema = {"type": "object", "required": ["replacements"], "properties": {"replacements": {"type": "array", "items": {
        "type": "object", "required": ["index", "scenes"],
        "properties": {"index": {"type": "integer"}, "scenes": {"type": "array", "items": scene_schema}}}}}}
    replacements: dict[int, list] = {}
    for start in range(0, len(targets), REVISE_BATCH):
        batch = targets[start:start + REVISE_BATCH]
        system = (f"You revise scenes of an animated {GENRE_INFO.get(genre, GENRE_INFO['story'])['video']} script. For "
                  "each scene index given, return the replacement scene(s) in the same JSON shape: one scene, or "
                  "several when a scene is too long for one 10-second clip. Fix exactly the listed problems, stay "
                  "faithful to the source text, never invent facts and keep the cast ids. "
                  + ("The narration is fixed: keep every spoken line word for word (you may only split lines between "
                     "scenes) and fix the problems through staging: actors, poses, bg_prompt, camera. "
                     if keep_text else "")
                  + f"Write spoken lines in {LANG_NAMES.get(lang, lang)}.")
        user = json.dumps({"source_text": source, "cast": script.get("cast", []),
                           "scenes": {i: script["scenes"][i] for i in batch},
                           "neighbours": compact(script, {j for i in batch for j in (i - 1, i + 1)} - set(batch)),
                           "issues": [i for i in issues if i["scene"] in batch or i["scene"] is None]},
                          ensure_ascii=False)
        print(f"  revising scenes {', '.join(str(i + 1) for i in batch)}...")
        for item in _ask(provider, system, user, schema).get("replacements", []):
            i = item.get("index")
            if i not in batch or not isinstance(item.get("scenes"), list):
                continue
            new = item["scenes"]
            if keep_text:
                said = lambda scenes: _plain(" ".join(l.get("text", "") for sc in scenes for l in sc.get("lines", [])))  # noqa: E731
                if said(new) != said([script["scenes"][i]]):
                    print(f"  scene {i + 1}: AI changed the narration; kept the original")
                    continue
            replacements[i] = new
    scenes = []
    for i, s in enumerate(script["scenes"]):
        scenes += replacements.get(i, [s])
    revised = _normalize({**script, "scenes": scenes}, lang)
    changed = set(replacements)
    if keep_text:
        revised, moved = source_order(revised, source)
        if moved:
            print(f"  put {len(moved)} scene(s) back in the source's order")
        revised, repeated = dedupe(revised)
        repeated = repeated or moved
        if repeated:
            print(f"  removed repeated narration in {len(repeated)} scene(s)")
        inserts: dict = {}
        for issue in coverage_issues(revised, source):
            print(f"  re-splitting {len(issue['missing'])} characters of missing narration...")
            part = write_script(issue["missing"], {"channel_name": "", "host": {}}, lang, 1, provider,
                                genre=genre, keep_text=True, cast=revised.get("cast", []))
            inserts[issue["scene"]] = part["scenes"]
        if inserts:
            scenes = list(inserts.get(None, []))
            for i, s in enumerate(revised["scenes"]):
                scenes += [s] + inserts.get(i, [])
            revised = _normalize({**revised, "scenes": scenes}, lang)
        changed |= {-1} if repeated or inserts else set()
    return revised, sorted(i for i in changed if i >= 0)


# ---------- polishing the narration text (before it is split into scenes) ----------
POLISH_CRITERIA = {
    "voice": "Giọng người kể nhất quán, có cá tính",
    "rhythm": "Nhịp câu khi đọc thành tiếng",
    "hooks": "Câu mở, móc nối và kết từng đoạn",
    "clarity": "Dễ hiểu với người xem nước ngoài",
    "imagery": "Hình ảnh cụ thể, gợi cảnh để dựng hình",
}
CRITIQUE_SCHEMA = {"type": "object", "required": ["criteria", "notes", "summary"], "properties": {
    "criteria": {"type": "array", "items": {"type": "object", "required": ["id", "score", "comment"], "properties": {
        "id": {"type": "string", "enum": list(POLISH_CRITERIA)}, "score": {"type": "integer", "minimum": 1, "maximum": 10},
        "comment": {"type": "string"}}}},
    "notes": {"type": "array", "items": {"type": "string"}, "description": "concrete edits to make, in Vietnamese"},
    "summary": {"type": "string"}}}
REWRITE_SCHEMA = {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}}
NUMBER_WORDS = ("one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen "
                "seventeen eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand "
                "million").split()


def fact_tokens(text: str) -> set[str]:
    """Numbers (digits or English number words) and names written with a capital letter mid-sentence: the parts
    a rewrite must keep."""
    tokens = set(re.findall(r"\d[\d,.]*\d|\d", text))
    low = text.lower()
    tokens |= {w for w in NUMBER_WORDS if re.search(rf"\b{w}\b", low)}
    tokens |= set(re.findall(r"(?<=[a-z,;] )[A-Z][\w'-]+", text))
    return tokens


def polish(text: str, provider: str, lang: str) -> dict:
    from .script import LANG_NAMES, split_text
    language = LANG_NAMES.get(lang, lang)
    critique = _ask(provider, "You are a story editor for narrated YouTube videos. Judge the storytelling language of "
                    f"this {language} narration as it will sound read aloud by a voice-over: the narrator's voice, "
                    "rhythm of sentences, hooks and transitions, clarity for viewers abroad, and concrete imagery that "
                    "can be animated. Score each criterion 1-10 and list concrete edits. Write comments and notes in "
                    "Vietnamese. Criteria: " + "; ".join(f"{k}: {v}" for k, v in POLISH_CRITERIA.items()),
                    text, CRITIQUE_SCHEMA)
    notes = [str(n) for n in critique.get("notes", [])]
    parts, out, kept = split_text(text, 2200), [], []
    for i, part in enumerate(parts):
        print(f"  rewriting part {i + 1}/{len(parts)}...")
        reply = _ask(provider, f"Rewrite this part of a {language} narration once, applying the editor's notes. Keep "
                     "the same narrator, the same events in the same order, every fact, number, date and name, and "
                     "every statement that something is a rumour or unproven. Do not add new facts, events or claims. "
                     "Keep about the same length, keep paragraph breaks, write for the ear, and return only the text.",
                     json.dumps({"editor_notes": notes, "previous_part_end": (out[-1][-600:] if out else ""),
                                 "part": part}, ensure_ascii=False), REWRITE_SCHEMA)
        new = str(reply.get("text", "")).strip()
        lost = fact_tokens(part) - fact_tokens(new)
        ratio = words(new) / max(1, words(part))
        if not new or lost or not 0.85 <= ratio <= 1.25:
            why = f"mất {', '.join(sorted(lost))}" if lost else f"độ dài x{ratio:.2f}" if new else "trống"
            print(f"  part {i + 1}: kept the original ({why})")
            kept.append({"part": i + 1, "reason": why})
            new = part
        out.append(new)
    criteria = [{"id": c["id"], "label": POLISH_CRITERIA[c["id"]], "score": max(1, min(10, int(c.get("score", 5)))),
                 "comment": str(c.get("comment", ""))} for c in critique.get("criteria", []) if c.get("id") in POLISH_CRITERIA]
    return {"text": "\n\n".join(out), "criteria": criteria, "notes": notes, "summary": str(critique.get("summary", "")),
            "kept_parts": kept, "parts": len(parts)}


def do_polish(project: Path, provider: str) -> dict:
    meta = json.loads((project / "meta.json").read_text(encoding="utf-8")) if (project / "meta.json").exists() else {}
    path = project / "story.txt"
    text = path.read_text(encoding="utf-8")
    print(f"[polish] {words(text)} words ({provider})...")
    result = polish(text, provider, meta.get("lang", "en"))
    n = 1
    while (project / f"story.v{n}.txt").exists():
        n += 1
    (project / f"story.v{n}.txt").write_text(text, encoding="utf-8")
    path.write_text(result["text"] + "\n", encoding="utf-8")
    hist_path = project / "script_reviews.json"
    history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else {"format": FORMAT, "rounds": []}
    entry = record(project, history, {"kind": "polish", "provider": provider, "criteria": result["criteria"],
                                      "notes": result["notes"], "summary": result["summary"],
                                      "kept_parts": result["kept_parts"], "parts": result["parts"],
                                      "words_before": words(text), "words_after": words(result["text"]),
                                      "backup": f"story.v{n}.txt"})
    for c in result["criteria"]:
        print(f"    {c['score']:>2}/10 {c['label']}: {c['comment']}")
    print(f"  {entry['words_before']} -> {entry['words_after']} words; previous text kept as story.v{n}.txt")
    if (project / "scenes.json").exists():
        print("  note: scenes.json was made from the old text; write the script again from the story")
    return entry


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
                              meta.get("lang") or script.get("lang"), bool(meta.get("keep_text")))
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
    ap.add_argument("action", choices=["review", "revise", "auto", "polish"])
    ap.add_argument("project")
    ap.add_argument("--provider", choices=["muse", "claude", "openai", "codex"], default="muse")
    ap.add_argument("--rounds", type=int, default=2, help="auto: at most this many revisions")
    args = ap.parse_args()
    project = Path(args.project).resolve()
    if args.action == "polish":
        do_polish(project, args.provider)
    elif args.action == "review":
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
