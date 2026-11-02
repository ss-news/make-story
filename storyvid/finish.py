"""Finishing a video (web UI tab "6. Hoàn thành"): machine checks, one frame per scene, an AI review written to
review.json, and the publish kit (titles, description with chapters and credits, tags, thumbnails).

    python -m storyvid.finish check output/<id>        machine checks -> finish.json
    python -m storyvid.finish loudnorm output/<id>     bring the audio to -14 LUFS (video stream copied)
    python -m storyvid.finish frames output/<id>       one frame per scene -> publish/frames/
    python -m storyvid.finish review output/<id> [--provider muse]   AI review -> review.json (storyvid.review/1)
    python -m storyvid.finish publish output/<id> [--provider muse] [--thumbnails 3]   -> publish/youtube.md + thumbnails

Publishing on YouTube stays a person's job; the web UI then records the links ("Đã đăng").
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .ffmpeg import ffmpeg_exe

ROOT = Path(__file__).resolve().parents[1]
LOUDNESS = (-16.0, -12.0)   # integrated LUFS window; YouTube plays back at about -14
TRUE_PEAK = -1.0            # dBTP ceiling
MAX_SILENCE = 3.0           # seconds of silence allowed in a row
GRID = (5, 4)               # scenes per review sheet (columns, rows)
FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
AREAS = ["story", "dialogue", "staging", "background", "props", "character", "audio", "subtitle", "pacing", "render"]


# ---------- helpers ----------
def load(project: Path) -> dict:
    read = lambda name, default: (json.loads((project / name).read_text(encoding="utf-8"))  # noqa: E731
                                  if (project / name).exists() else default)
    return {"script": read("scenes.json", None), "meta": read("meta.json", {}), "render": read("render.json", {}),
            "visuals": read("visuals.json", None), "finish": read("finish.json", {})}


def save_finish(project: Path, key: str, value) -> None:
    path = project / "finish.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    data[key] = {**value, "at": int(time.time())}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ffmpeg_log(*args: str) -> str:
    return subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", *args], capture_output=True, text=True).stderr


def probe(video: Path) -> dict:
    out = ffmpeg_log("-i", str(video))
    d = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", out)
    size = re.search(r"Video:.*?(\d{3,5})x(\d{3,5})", out)
    return {"duration": int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]) if d else 0.0,
            "width": int(size[1]) if size else 0, "height": int(size[2]) if size else 0, "audio": "Audio:" in out}


def loudness(video: Path) -> dict:
    out = ffmpeg_log("-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-")
    summary = out[out.rfind("Summary:"):] if "Summary:" in out else out
    i = re.search(r"I:\s+(-?\d+(?:\.\d+)?) LUFS", summary)
    peak = re.search(r"Peak:\s+(-?\d+(?:\.\d+)?|-inf) dBFS", summary)
    return {"lufs": float(i[1]) if i else None,
            "peak": (float(peak[1]) if peak[1] != "-inf" else -99.0) if peak else None}


def silences(video: Path, minimum: float = MAX_SILENCE) -> list[tuple[float, float]]:
    out = ffmpeg_log("-i", str(video), "-vn", "-af", f"silencedetect=noise=-45dB:d={minimum}", "-f", "null", "-")
    starts = [float(x) for x in re.findall(r"silence_start: (-?\d+(?:\.\d+)?)", out)]
    lengths = [float(x) for x in re.findall(r"silence_duration: (\d+(?:\.\d+)?)", out)]
    return list(zip(starts, lengths))


def srt_cues(path: Path) -> list[tuple[float, float, str]]:
    def t(s):
        h, m, rest = s.split(":")
        sec, ms = rest.split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000
    cues = []
    for block in path.read_text(encoding="utf-8").strip().split("\n\n"):
        lines = block.split("\n")
        if len(lines) >= 3 and " --> " in lines[1]:
            a, b = lines[1].split(" --> ")
            cues.append((t(a), t(b), " ".join(lines[2:]).strip()))
    return cues


def clock(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s // 60 % 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60}:{s % 60:02d}"


# ---------- 1. machine checks ----------
def check(project: Path, name: str = "video") -> dict:
    from .visuals import is_approved, script_digest
    data = load(project)
    video = project / f"{name}.mp4"
    rec = data["render"].get(name)
    checks = []

    def add(cid, label, ok, detail):
        checks.append({"id": cid, "label": label, "ok": bool(ok), "detail": detail})

    add("rendered", "Đã dựng video", video.exists() and rec, "có render.json" if rec else
        "chưa có video, hoặc video dựng trước khi app ghi render.json: dựng lại")
    if not (video.exists() and rec):
        return {"ok": False, "checks": checks}
    info = probe(video)
    add("approved", "Dựng từ bản kịch bản đã duyệt",
        is_approved(project) and rec["scenes_digest"] == script_digest(data["script"]),
        "khớp" if rec["scenes_digest"] == script_digest(data["script"]) else
        "kịch bản đã đổi sau khi dựng, hoặc chưa được duyệt: duyệt rồi dựng lại")
    add("no_fallback", "Không dựng bản nháp (--fallback)", not rec["fallback"],
        "đủ asset/clip" if not rec["fallback"] else "dựng với --fallback: dựng lại không dùng --fallback")
    if rec["visuals"] and data["visuals"]:
        missing = [s["index"] + 1 for s in rec["scenes"] if not data["visuals"]["scenes"][s["index"]]["clip"]]
        add("clips", "Cảnh nào cũng có clip", not missing, "đủ" if not missing else f"thiếu clip: cảnh {missing}")
    short_side = min(info["width"], info["height"])
    add("resolution", "Độ phân giải 1080p", short_side >= 1080, f"{info['width']}x{info['height']}")
    target = float(data["meta"].get("minutes", 0)) * 60 * (0.9 if name == "video" else 0)
    if name == "video_short":
        add("duration", "Short dài tối đa 60 giây", info["duration"] <= 60.5, clock(info["duration"]))
    else:
        add("duration", "Đủ thời lượng mục tiêu", info["duration"] >= target,
            f"{clock(info['duration'])} / mục tiêu {data['meta'].get('minutes', '?')} phút")
    loud = loudness(video) if info["audio"] else {"lufs": None, "peak": None}
    ok_loud = loud["lufs"] is not None and LOUDNESS[0] <= loud["lufs"] <= LOUDNESS[1] and loud["peak"] <= TRUE_PEAK
    add("loudness", "Âm lượng chuẩn YouTube (-16 đến -12 LUFS, đỉnh dưới -1 dB)", ok_loud,
        f"{loud['lufs']} LUFS, đỉnh {loud['peak']} dB" + ("" if ok_loud else " → bấm “Chuẩn hóa âm lượng”"))
    gaps = [(a, b) for a, b in silences(video) if a < info["duration"] - 4]  # the ending fade is fine
    add("silence", f"Không im lặng quá {MAX_SILENCE:g} giây", not gaps,
        "không có" if not gaps else ", ".join(f"{clock(a)} ({b:.1f}s)" for a, b in gaps[:5]))
    srt = project / f"{name}.srt"
    cues = srt_cues(srt) if srt.exists() else []
    covered = bool(cues) and cues[-1][1] >= info["duration"] - 15 and all(c[2] for c in cues)
    add("subtitles", "Phụ đề SRT đủ và phủ hết video", covered,
        f"{len(cues)} dòng, đến {clock(cues[-1][1])}" if cues else "không có file .srt")
    result = {"ok": all(c["ok"] for c in checks), "checks": checks, "video": name, "info": info}
    return result


def loudnorm(project: Path, name: str = "video") -> Path:
    """Normalize the audio to -14 LUFS / -1.5 dBTP; the video stream is copied, so this takes seconds."""
    video = project / f"{name}.mp4"
    tmp = project / f"{name}.loudnorm.mp4"
    subprocess.run([ffmpeg_exe(), "-y", "-v", "error", "-i", str(video), "-c:v", "copy", "-af",
                    "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-movflags", "+faststart", str(tmp)], check=True)
    tmp.replace(video)
    return video


# ---------- 2. frames and review ----------
def frames(project: Path, name: str = "video") -> list[Path]:
    """One frame from the middle of every scene, and numbered sheets of GRID scenes for the reviewer."""
    data = load(project)
    rec = data["render"].get(name)
    if not rec:
        raise SystemExit("No render.json: render the video first")
    out = project / "publish" / "frames"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.jpg"):
        old.unlink()
    font = ImageFont.truetype(FONT, 26)
    thumbs = []
    for s in rec["scenes"]:
        path = out / f"scene_{s['index']:03d}.jpg"
        subprocess.run([ffmpeg_exe(), "-v", "error", "-y", "-ss", f"{(s['start'] + s['end']) / 2:.2f}", "-i",
                        str(project / f"{name}.mp4"), "-frames:v", "1", "-vf", "scale=384:-2", str(path)])
        if path.exists():
            thumbs.append((s["index"], path))
    cols, rows = GRID
    sheets = []
    for k in range(0, len(thumbs), cols * rows):
        part = thumbs[k:k + cols * rows]
        w, h = Image.open(part[0][1]).size
        sheet = Image.new("RGB", (cols * w, rows * h), "white")
        for j, (index, path) in enumerate(part):
            img = Image.open(path).convert("RGB")
            ImageDraw.Draw(img).text((8, 6), str(index + 1), font=font, fill="yellow", stroke_width=3,
                                     stroke_fill="black")
            sheet.paste(img, ((j % cols) * w, (j // cols) * h))
        sheet_path = out / f"sheet_{k // (cols * rows) + 1:02d}.jpg"
        sheet.save(sheet_path, quality=85)
        sheets.append(sheet_path)
    return sheets


def _ask(provider: str, system: str, user: str, schema: dict, images: list[Path] = ()) -> dict:
    from . import llm
    if provider != "muse":
        from .script_review import _ask as ask_text
        return ask_text(provider, system, user, schema)  # text-only providers review the narration
    from .visuals import muse
    prompt = (f"{system}\n\nReply with only one JSON object matching this schema, no other text, and do not create "
              f"any image or video in this reply:\n{json.dumps(schema)}\n\n{user}")
    reply = muse("/api/chat", {"prompt": prompt, "timeoutSec": 900, "references": [str(p) for p in images]},
                 timeout=1020)
    if not reply.get("ok"):
        raise RuntimeError(f"Muse did not answer: {reply.get('error')}")
    return llm.extract_json(reply["text"])


ISSUES_SCHEMA = {"type": "object", "required": ["issues"], "properties": {"issues": {"type": "array", "items": {
    "type": "object", "required": ["scene", "area", "severity", "problem", "fix"],
    "properties": {"scene": {"type": ["integer", "null"]}, "area": {"type": "string", "enum": AREAS},
                   "severity": {"type": "string", "enum": ["blocker", "major", "minor"]},
                   "problem": {"type": "string"}, "fix": {"type": "string"}}}}}}


def review(project: Path, provider: str) -> dict:
    """AI review of the finished video: each numbered frame against its narration, plus a fact check."""
    from .contract import REVIEW_FORMAT, validate_review
    data = load(project)
    script, rec = data["script"], data["render"].get("video")
    if not rec:
        raise SystemExit("No render.json: render the video first")
    sheets = sorted((project / "publish" / "frames").glob("sheet_*.jpg")) or frames(project)
    names = {c["id"]: c["name"] for c in script.get("cast", [])}
    looks = {c["id"]: c["look"] for c in (data["visuals"] or {}).get("cast", [])}
    per_sheet = GRID[0] * GRID[1]
    issues = []
    system = ("You review a finished animated video, one numbered frame per scene. Compare each frame with that "
              "scene's narration and the characters' fixed looks. Report only real problems: frame does not show "
              "what is said, a main character looks different from their look, text or garbled letters in frame, "
              "a broken or ugly frame, or an unsuitable image. Scene numbers in the attached sheets are 1-based; "
              "answer with 1-based scene numbers. Write problems and fixes in Vietnamese. Areas: " + ", ".join(AREAS))
    for k, sheet in enumerate(sheets):
        scenes = rec["scenes"][k * per_sheet:(k + 1) * per_sheet]
        print(f"[review] frames {scenes[0]['index'] + 1}-{scenes[-1]['index'] + 1}...")
        user = json.dumps({"characters": {names.get(i, i): looks.get(i, "") for i in names},
                           "scenes": [{"scene": s["index"] + 1,
                                       "on_stage": [names.get(a["id"], a["id"]) for a in script["scenes"][s["index"]]["actors"]],
                                       "narration": " ".join(l["text"] for l in script["scenes"][s["index"]]["lines"])}
                                      for s in scenes]}, ensure_ascii=False)
        for x in _ask(provider, system, user, ISSUES_SCHEMA, [sheet]).get("issues", []):
            issues.append(x)
    print("[review] fact check...")
    facts = _ask(provider, "You fact-check the narration of an educational video against general scientific "
                 "knowledge and the source it names. List claims that are wrong, overstated, or need checking "
                 "against the source (numbers, study results, quotes). Severity major if likely wrong, minor if it "
                 "only needs checking. Use area story. Write in Vietnamese. Scene numbers are 1-based.",
                 json.dumps([{"scene": i + 1, "narration": " ".join(l["text"] for l in s["lines"])}
                             for i, s in enumerate(script["scenes"])], ensure_ascii=False), ISSUES_SCHEMA)
    issues += facts.get("issues", [])
    clean = []
    for x in issues:
        scene = x.get("scene")
        scene = scene - 1 if isinstance(scene, int) and 1 <= scene <= len(script["scenes"]) else None
        if str(x.get("problem", "")).strip():
            clean.append({"scene": scene, "area": x.get("area") if x.get("area") in AREAS else "render",
                          "severity": x.get("severity") if x.get("severity") in ("blocker", "major", "minor") else "minor",
                          "owner": "codex", "problem": str(x["problem"]), "fix": str(x.get("fix") or "Tạo lại cảnh.")})
    verdict = "fix" if any(i["severity"] in ("blocker", "major") for i in clean) else "pass"
    doc = {"format": REVIEW_FORMAT, "scenes_file": f"{project.relative_to(ROOT).as_posix()}/scenes.json",
           "verdict": verdict, "issues": clean}
    errors = validate_review(doc, len(script["scenes"]))
    if errors:
        raise SystemExit("\n".join(errors))
    (project / "review.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  {verdict}: {len(clean)} issue(s) -> review.json")
    return doc


# ---------- 3. publish kit ----------
PUBLISH_SCHEMA = {"type": "object", "required": ["titles", "hook", "body", "tags", "hashtags", "chapters", "thumbnails"],
                  "properties": {
    "titles": {"type": "array", "items": {"type": "string"}, "description": "3 options, under 70 characters"},
    "hook": {"type": "string", "description": "first 2 lines of the description, with the main keywords"},
    "body": {"type": "string", "description": "short summary of what the viewer learns"},
    "tags": {"type": "array", "items": {"type": "string"}},
    "hashtags": {"type": "array", "items": {"type": "string"}},
    "chapters": {"type": "array", "items": {"type": "object", "required": ["scene", "title"], "properties": {
        "scene": {"type": "integer", "description": "1-based scene where the chapter starts"}, "title": {"type": "string"}}}},
    "thumbnails": {"type": "array", "items": {"type": "object", "required": ["text", "picture", "cast"], "properties": {
        "text": {"type": "string", "description": "at most 4 words, big and readable"},
        "picture": {"type": "string", "description": "English image prompt: one big clear subject, strong emotion, "
                                                     "simple background, empty space on the left for the text"},
        "cast": {"type": "array", "items": {"type": "string"}, "description": "cast ids shown"}}}}}}


def thumbnail_text(img: Image.Image, text: str) -> Image.Image:
    """Big title on the left third: white letters with a dark outline over a soft dark gradient."""
    img = img.convert("RGB").resize((1280, 720)) if img.size != (1280, 720) else img.convert("RGB")
    shade = Image.new("L", (1280, 1), 0)
    for x in range(1280):
        shade.putpixel((x, 0), int(170 * max(0.0, 1 - x / 760)))
    img.paste((10, 10, 20), (0, 0), shade.resize((1280, 720)))
    draw = ImageDraw.Draw(img)
    words, size = text.upper().split(), 120
    while size > 50:
        font = ImageFont.truetype(FONT, size)
        lines, line = [], ""
        for w in words:
            trial = f"{line} {w}".strip()
            if font.getlength(trial) > 600 and line:
                lines.append(line)
                line = w
            else:
                line = trial
        lines.append(line)
        if len(lines) <= 3:
            break
        size -= 10
    lh = int(size * 1.08)
    y = (720 - lh * len(lines)) // 2
    for k, line in enumerate(lines):
        draw.text((60, y + k * lh), line, font=font, fill=(255, 214, 64) if k == 0 else "white",
                  stroke_width=max(6, size // 12), stroke_fill=(20, 16, 30))
    return img


def publish(project: Path, provider: str, count: int = 3) -> dict:
    from .visuals import _generate
    data = load(project)
    script, meta, rec, vis = data["script"], data["meta"], data["render"].get("video"), data["visuals"]
    if not rec:
        raise SystemExit("No render.json: render the video first")
    from .script import LANG_NAMES
    lang = LANG_NAMES.get(meta.get("lang") or script["lang"], "English")
    names = {c["id"]: c["name"] for c in script.get("cast", [])}
    narration = [{"scene": i + 1, "text": " ".join(l["text"] for l in s["lines"])} for i, s in enumerate(script["scenes"])]
    print("[publish] titles, description, chapters, thumbnails ideas...")
    plan = _ask(provider, f"You prepare the YouTube upload of an educational animated video. Write titles, "
                "description, tags and chapter titles in " + lang + ". Titles: curiosity plus a clear benefit, no "
                "clickbait that overpromises, under 70 characters. Chapters: 5-10, the first at scene 1, each a "
                "new idea. Thumbnails: " + str(count) + " different concepts, each one big clear subject with a "
                "strong emotion, using the recurring characters when it helps; text at most 4 words in " + lang + ".",
                json.dumps({"title": script["title"], "characters": names, "credits": meta.get("credits", ""),
                            "narration": narration}, ensure_ascii=False)[:24000], PUBLISH_SCHEMA)
    out = project / "publish"
    out.mkdir(exist_ok=True)
    starts = {s["index"]: s["start"] for s in rec["scenes"]}
    chapters, last = [], -999.0
    for c in sorted(plan.get("chapters", []), key=lambda c: c.get("scene", 0)):
        i = max(0, int(c.get("scene", 1)) - 1)
        t = 0.0 if not chapters else starts.get(i, last)
        if t - last >= 10:  # YouTube needs chapters at least 10 seconds apart, the first at 0:00
            chapters.append({"time": clock(t), "title": str(c.get("title", "")).strip()})
            last = t
    if chapters:
        chapters[0]["time"] = "0:00"
    sheets = {c["id"]: project / c["sheet"] for c in (vis or {}).get("cast", []) if c.get("sheet")}
    style = (vis or {}).get("style", "")
    thumbs = []
    for k, idea in enumerate(plan.get("thumbnails", [])[:count], 1):
        print(f"[publish] thumbnail {k}: {idea.get('text')}")
        refs = [sheets[c] for c in idea.get("cast", []) if c in sheets][:2]
        try:
            bg = _generate("image", f"YouTube thumbnail background. {idea.get('picture')} Keep the left third simple "
                           f"and darker for a title. No text, no letters.\n\nVisual style: {style}", "16:9",
                           out / f"thumb_bg_{k}.png", [p for p in refs if p.is_file()])
            path = out / f"thumbnail_{k}.jpg"
            thumbnail_text(Image.open(bg), idea.get("text", "")).save(path, quality=90)
            thumbs.append({"file": path.relative_to(project).as_posix(), "text": idea.get("text", "")})
        except RuntimeError as e:
            print(f"  thumbnail {k} failed: {e}")
    credits = meta.get("credits", "").strip()
    sounds = project / "credits.txt"  # music and sound credits written by the render (storyvid/cli.py)
    if sounds.exists():
        credits = "\n".join(filter(None, [credits, sounds.read_text(encoding="utf-8").strip()]))
    note = ("Hình ảnh và chuyển động trong video được tạo bằng AI; kịch bản và lời kể do kênh biên soạn."
            if lang == "Vietnamese" else
            "Images and motion in this video were made with AI; the script and narration were written by the channel.")
    description = "\n\n".join(filter(None, [
        plan.get("hook", "").strip(), plan.get("body", "").strip(),
        "\n".join(f"{c['time']} {c['title']}" for c in chapters),
        credits, note, " ".join(plan.get("hashtags", []))]))
    kit = {"titles": plan.get("titles", [])[:3], "description": description, "tags": plan.get("tags", []),
           "chapters": chapters, "thumbnails": thumbs}
    (out / "publish.json").write_text(json.dumps(kit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [f"# YouTube upload: {script['title']}", "",
          f"File: `video.mp4` · Phụ đề: `video.srt` · Thumbnail: {', '.join(t['file'] for t in thumbs) or '(chưa có)'}",
          "", "## Tiêu đề (chọn 1)", *[f"- {t}" for t in kit["titles"]], "", "## Mô tả", "", description, "",
          "## Tags", ", ".join(kit["tags"]), "", "## Cài đặt",
          "- Đối tượng: Không, video không dành cho trẻ em",
          f"- Ngôn ngữ: {lang} · Phụ đề: tải `video.srt`",
          "- Nội dung đã thay đổi/tổng hợp: chỉ bật khi hình AI trông như người hoặc sự kiện thật",
          "- Thêm vào playlist; màn hình kết thúc trỏ tới video khác; Short (nếu có) gắn Related video về bản dài"]
    (out / "youtube.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"  -> {out / 'youtube.md'}, {len(thumbs)} thumbnail(s)")
    return kit


def main() -> None:
    from .cli import load_env
    load_env(ROOT / ".env")
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["check", "loudnorm", "frames", "review", "publish"])
    ap.add_argument("project")
    ap.add_argument("--video", choices=["video", "video_short"], default="video")
    ap.add_argument("--provider", choices=["muse", "claude", "openai", "codex"], default="muse")
    ap.add_argument("--thumbnails", type=int, default=3)
    args = ap.parse_args()
    project = Path(args.project).resolve()
    if args.step == "check":
        result = check(project, args.video)
        for c in result["checks"]:
            print(f"  {'✓' if c['ok'] else '✗'} {c['label']}: {c['detail']}")
        save_finish(project, f"check_{args.video}", result)
        print("Đạt" if result["ok"] else "Chưa đạt")
    elif args.step == "loudnorm":
        print(f"  -> {loudnorm(project, args.video)}")
        result = check(project, args.video)
        save_finish(project, f"check_{args.video}", result)
        print(next(f"  {c['detail']}" for c in result["checks"] if c["id"] == "loudness"))
    elif args.step == "frames":
        print(f"  {len(frames(project, args.video))} sheet(s)")
    elif args.step == "review":
        frames(project)
        doc = review(project, args.provider)
        save_finish(project, "review", {"verdict": doc["verdict"], "issues": len(doc["issues"])})
    else:
        kit = publish(project, args.provider, args.thumbnails)
        save_finish(project, "publish", {"thumbnails": len(kit["thumbnails"]), "chapters": len(kit["chapters"])})


if __name__ == "__main__":
    main()
