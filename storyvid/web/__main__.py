"""Local web UI to manage projects: python -m storyvid.web  ->  http://127.0.0.1:8765"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from PIL import Image

from .. import pack
from ..character import ARM_POSES, Character
from ..character_catalog import PRESETS, OUTFITS, ACCESSORIES, resolve_character, validate_selection
from ..script import ACTIONS, CAMERAS, EXPRESSIONS, KINDS, LANG_NAMES, POSES, POSITIONS, _normalize

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output"
ENV_PATH = ROOT / ".env"
CHANNEL_PATH = ROOT / "channel.json"
ENV_KEYS = ["LLM_PROVIDER", "LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY", "CODEX_BIN", "CODEX_MODEL",
            "TTS_PROVIDER", "ELEVENLABS_API_KEY", "ELEVENLABS_EXTRA_KEYS", "ELEVENLABS_MODEL",
            "ELEVENLABS_NARRATOR_VOICE", "VIENEU_NARRATOR_VOICE"]
SECRET_KEYS = {"LLM_API_KEY", "ELEVENLABS_API_KEY", "ELEVENLABS_EXTRA_KEYS"}

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.json.sort_keys = False  # keep channel.json and language lists in their written order
jobs: dict[str, subprocess.Popen] = {}


@app.after_request
def no_stale_ui(response):
    """The page and its scripts change with the app; make the browser revalidate them every time."""
    if request.path == "/" or request.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
jobs_lock = threading.Lock()


# ---------- helpers ----------
def project_dir(pid: str) -> Path:
    if not re.fullmatch(r"[a-z0-9_]+", pid):
        abort(404)
    d = OUTPUT / pid
    if not d.is_dir():
        abort(404)
    return d


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def job_status(pid: str, d: Path) -> dict:
    with jobs_lock:
        proc = jobs.get(pid)
    job = read_json(d / "job.json", {"state": "idle"})
    if proc and proc.poll() is None:
        return {**job, "state": "running"}
    if job.get("state") == "running":  # server restarted while the job ran
        return {**job, "state": "interrupted"}
    return job


def summary(d: Path) -> dict:
    meta = read_json(d / "meta.json", {})
    scenes = read_json(d / "scenes.json")
    video = d / "video.mp4"
    return {
        "id": d.name,
        "name": meta.get("name", d.name),
        "title": (scenes or {}).get("title", ""),
        "lang": meta.get("lang", "en"),
        "scenes": len((scenes or {}).get("scenes", [])),
        "has_video": video.exists(),
        "published": bool(meta.get("published")),
        "video_mtime": int(video.stat().st_mtime) if video.exists() else None,
        "short_mtime": int((d / "video_short.mp4").stat().st_mtime) if (d / "video_short.mp4").exists() else None,
        "updated": int(max((p.stat().st_mtime for p in d.iterdir()), default=d.stat().st_mtime)),
        "status": job_status(d.name, d),
    }


def start_job(pid: str, d: Path, kind: str, args: list[str], module: str = "storyvid.cli",
              env: dict | None = None) -> None:
    with jobs_lock:
        proc = jobs.get(pid)
        if proc and proc.poll() is None:
            abort(409, "A job is already running for this project")
        log = open(d / "log.txt", "w", encoding="utf-8")
        log.write(f"$ {module} {' '.join(args)}\n")
        log.flush()
        proc = subprocess.Popen([sys.executable, "-m", module, *args], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True,  # Stop ends the group
                                env={**os.environ, **(env or {}), "PYTHONUNBUFFERED": "1"})
        jobs[pid] = proc
        write_json(d / "job.json", {"state": "running", "kind": kind, "started": int(time.time())})

    def wait():
        code = proc.wait()
        log.close()
        write_json(d / "job.json", {"state": "done" if code == 0 else "failed", "kind": kind,
                                    "finished": int(time.time()), "code": code})

    threading.Thread(target=wait, daemon=True).start()


def read_env() -> dict:
    values = {k: "" for k in ENV_KEYS}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                if k.strip() in values:
                    values[k.strip()] = v.strip()
    return values


def write_env(updates: dict) -> None:
    """Rewrite only KEY= lines we manage; comments and other lines are kept as they are."""
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    done = set()
    for i, line in enumerate(lines):
        if "=" in line and not line.lstrip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            if k in updates:
                lines[i] = f"{k}={updates[k]}"
                done.add(k)
    lines += [f"{k}={v}" for k, v in updates.items() if k not in done]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_PATH.chmod(0o600)


# ---------- pages ----------
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/options")
def options():
    channel = read_json(CHANNEL_PATH, {})
    return jsonify(poses=POSES, expressions=EXPRESSIONS, positions=POSITIONS, cameras=CAMERAS,
                   actions=ACTIONS, kinds=KINDS,
                   languages=[[k, v] for k, v in LANG_NAMES.items() if k in channel.get("voices", {})],
                   characters=[{"id":k, "label":v["label"], "colors":resolve_character(channel["host"], {"preset":k})} for k,v in PRESETS.items()],
                   outfits=[{"id":k, "label":v["label"], "color":v["color"]} for k,v in OUTFITS.items()],
                   accessories=[{"id":k, "label":v} for k,v in ACCESSORIES.items()],
                   default_character=resolve_character(channel["host"]),
                   backgrounds=pack.labels("backgrounds"), props=pack.labels("animals", "props"))


# ---------- projects ----------
@app.get("/api/projects")
def list_projects():
    OUTPUT.mkdir(exist_ok=True)
    items = [summary(d) for d in OUTPUT.iterdir() if d.is_dir() and re.fullmatch(r"[a-z0-9_]+", d.name)]
    return jsonify(sorted(items, key=lambda x: -x["updated"]))


@app.post("/api/projects")
def create_project():
    body = request.get_json(force=True)
    name = (body.get("name") or "").strip() or "untitled"
    ascii_name = unicodedata.normalize("NFD", name.lower().replace("đ", "d"))
    ascii_name = "".join(c for c in ascii_name if unicodedata.category(c) != "Mn")
    base = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")[:40] or "project"
    pid, n = base, 2
    while (OUTPUT / pid).exists():
        pid, n = f"{base}_{n}", n + 1
    d = OUTPUT / pid
    d.mkdir(parents=True)
    (d / "story.txt").write_text(body.get("story", ""), encoding="utf-8")
    write_json(d / "meta.json", {"name": name, "lang": body.get("lang", "en"),
                                 "minutes": float(body.get("minutes", 2)),
                                 "ratio": body.get("ratio") if body.get("ratio") in ("16:9", "9:16") else "9:16",
                                 "created": int(time.time())})
    return jsonify(summary(d))


@app.get("/api/projects/<pid>")
def get_project(pid):
    d = project_dir(pid)
    data = summary(d)
    data["meta"] = read_json(d / "meta.json", {})
    data["story"] = (d / "story.txt").read_text(encoding="utf-8") if (d / "story.txt").exists() else ""
    data["script"] = read_json(d / "scenes.json")
    if data["script"]:
        try:  # clamp hand-edited files for the editor; the file changes only on save
            data["script"] = _normalize(data["script"], data["meta"].get("lang"))
        except (RuntimeError, ValueError):
            pass
    from ..visuals import is_approved, is_cast_approved, load as load_visuals
    data["approved"] = is_approved(d)
    data["cast_approved"] = data["approved"] and is_cast_approved(d, load_visuals(d)[1])
    bgs = read_json(d / "backgrounds.json", {})
    data["backgrounds"] = {k: f"/files/{pid}/bg/{k}" for k in bgs}
    return jsonify(data)


@app.put("/api/projects/<pid>")
def update_project(pid):
    d = project_dir(pid)
    body = request.get_json(force=True)
    meta = read_json(d / "meta.json", {})
    for key in ("name", "lang"):
        if key in body:
            meta[key] = body[key]
    if body.get("ratio") in ("16:9", "9:16"):
        meta["ratio"] = body["ratio"]
    if isinstance(body.get("style"), dict):
        meta["style"] = {"preset": str(body["style"].get("preset", "")), "text": str(body["style"].get("text", ""))}
    if "credits" in body:
        meta["credits"] = str(body["credits"])
    if isinstance(body.get("published"), dict):
        meta["published"] = {"long": str(body["published"].get("long", "")),
                             "short": str(body["published"].get("short", "")), "at": int(time.time())}
    if isinstance(body.get("publish_checklist"), dict):
        meta["publish_checklist"] = {str(k): bool(v) for k, v in body["publish_checklist"].items()}
    if body.get("genre") in ("story", "explainer"):
        meta["genre"] = body["genre"]
    if "keep_text" in body:
        meta["keep_text"] = bool(body["keep_text"])
    if isinstance(body.get("voice"), dict):
        meta["voice"] = {"provider": str(body["voice"].get("provider", "")), "voice": str(body["voice"].get("voice", ""))}
    if "minutes" in body:
        meta["minutes"] = float(body["minutes"])
    write_json(d / "meta.json", meta)
    if "story" in body:
        (d / "story.txt").write_text(body["story"], encoding="utf-8")
    if "script" in body:
        try:
            write_json(d / "scenes.json", _normalize(body["script"], meta.get("lang")))
        except (RuntimeError, ValueError) as e:
            abort(400, str(e))
    return get_project(pid)


@app.delete("/api/projects/<pid>")
def delete_project(pid):
    d = project_dir(pid)
    if job_status(pid, d)["state"] == "running":
        abort(409, "Stop the running job first")
    shutil.rmtree(d)
    return jsonify(ok=True)


def voice_env(meta: dict) -> dict:
    """The project's own voice choice overrides TTS_PROVIDER and the narrator voice from .env."""
    voice = meta.get("voice") or {}
    provider = voice.get("provider")
    if provider not in ("edge", "elevenlabs", "vieneu"):
        return {}
    env = {"TTS_PROVIDER": provider}
    if voice.get("voice") and provider in ("vieneu", "elevenlabs"):
        env[f"{provider.upper()}_NARRATOR_VOICE"] = voice["voice"]
    return env


@app.post("/api/projects/<pid>/approve")
def approve_script(pid):
    """A person read the script and lets the AI picture steps start. Any later edit clears it."""
    from ..check import check_script
    from ..visuals import script_digest
    d = project_dir(pid)
    if not (d / "scenes.json").exists():
        abort(400, "Write or create the script first")
    if check_script(d / "scenes.json") == 1:
        abort(400, "The script does not follow the standard yet; see the log of python -m storyvid.check")
    meta = read_json(d / "meta.json", {})
    meta["approved_script"] = script_digest(read_json(d / "scenes.json"))
    meta["approved_at"] = int(time.time())
    write_json(d / "meta.json", meta)
    return get_project(pid)


@app.post("/api/projects/<pid>/approve-cast")
def approve_cast(pid):
    """A person looked at every character sheet; the scene images may start. A new or remade sheet clears it."""
    from ..visuals import cast_digest, cast_ready, load as load_visuals
    d = project_dir(pid)
    visuals = load_visuals(d)[1] if (d / "scenes.json").exists() else None
    if not cast_ready(d, visuals):
        abort(400, "Tạo đủ ảnh mẫu cho mọi nhân vật trước")
    meta = read_json(d / "meta.json", {})
    meta["approved_cast"] = cast_digest(d, visuals)
    meta["approved_cast_at"] = int(time.time())
    write_json(d / "meta.json", meta)
    return get_project(pid)


@app.post("/api/projects/<pid>/auto")
def run_auto(pid):
    """storyvid.auto: every remaining step in a row, stopping for the character approval."""
    from ..visuals import is_approved
    d = project_dir(pid)
    if not is_approved(d):
        abort(409, "Kịch bản chưa được duyệt: đọc và bấm “Duyệt kịch bản” ở tab Kịch bản trước")
    body = request.get_json(silent=True) or {}
    meta = read_json(d / "meta.json", {})
    args = [str(d), "--res", body["res"] if body.get("res") in ("480", "720", "1080") else "1080"]
    if body.get("provider") in ("offline", "muse", "openai", "codex"):
        args += ["--provider", body["provider"]]
    start_job(pid, d, "auto", args, module="storyvid.auto", env=voice_env(meta))
    return jsonify(job_status(pid, d))


@app.get("/api/projects/<pid>/script-reviews")
def get_script_reviews(pid):
    d = project_dir(pid)
    return jsonify(read_json(d / "script_reviews.json", {"rounds": []}))


@app.post("/api/projects/<pid>/script-review")
def run_script_review(pid):
    d = project_dir(pid)
    body = request.get_json(silent=True) or {}
    action = body.get("action") if body.get("action") in ("review", "revise", "auto", "polish") else "review"
    if action == "polish" and not (d / "story.txt").read_text(encoding="utf-8").strip():
        abort(400, "Paste the story first")
    if action != "polish" and not (d / "scenes.json").exists():
        abort(400, "Write or create the script first")
    args = [action, str(d)]
    if body.get("provider") in ("muse", "claude", "openai", "codex"):
        args += ["--provider", body["provider"]]
    if action == "auto":
        args += ["--rounds", str(max(1, min(4, int(body.get("rounds", 2)))))]
    start_job(pid, d, f"script_{action}", args, module="storyvid.script_review")
    return jsonify(job_status(pid, d))


@app.post("/api/projects/<pid>/script")
def run_script(pid):
    d = project_dir(pid)
    body = request.get_json(silent=True) or {}
    meta = read_json(d / "meta.json", {})
    args = [str(d / "story.txt"), "--script-only", "--out", str(d), "--lang", meta.get("lang", "en"),
            "--minutes", str(meta.get("minutes", 2))]
    if body.get("provider"):
        args += ["--provider", body["provider"]]
    if meta.get("genre") in ("story", "explainer"):
        args += ["--genre", meta["genre"]]
    if meta.get("keep_text"):
        args.append("--keep-text")
    start_job(pid, d, "script", args)
    meta.pop("approved_script", None)  # a new script needs a new review
    write_json(d / "meta.json", meta)
    return jsonify(job_status(pid, d))


@app.post("/api/projects/<pid>/render")
def run_render(pid):
    d = project_dir(pid)
    if not (d / "scenes.json").exists():
        abort(400, "Write or create the script first")
    body = request.get_json(silent=True) or {}
    meta = read_json(d / "meta.json", {})
    res = body.get("res", "720") if body.get("res") in ("480", "720", "1080") else "720"
    args = ["--script", str(d / "scenes.json"), "--out", str(d), "--lang", meta.get("lang", "en"), "--res", res]
    if body.get("short"):
        args.append("--short")
    if body.get("visuals"):
        args.append("--visuals")
    start_job(pid, d, "render", args, env=voice_env(meta))
    return jsonify(job_status(pid, d))


# ---------- Muse visuals (storyvid/visuals.py, MuseFlow) ----------
@app.get("/api/muse/status")
def muse_status():
    from ..visuals import muse
    try:
        return jsonify(running=True, **muse("/api/status", timeout=5))
    except RuntimeError as e:
        return jsonify(running=False, ready=0, accounts=[], error=str(e))


@app.get("/api/projects/<pid>/visuals")
def get_visuals(pid):
    """visuals.json plus "_files": {path: mtime} so the page reloads an image or clip only when it changed."""
    d = project_dir(pid)
    visuals = read_json(d / "visuals.json")
    if visuals:
        paths = [c["sheet"] for c in visuals.get("cast", [])] + [s[k] for s in visuals.get("scenes", [])
                                                                   for k in ("image", "clip")]
        visuals["_files"] = {f: int((d / f).stat().st_mtime) for f in paths if f and (d / f).is_file()}
    return jsonify(visuals)


@app.put("/api/projects/<pid>/visuals")
def put_visuals(pid):
    from ..contract import validate_visuals
    d = project_dir(pid)
    visuals = request.get_json(force=True)
    visuals.pop("_files", None)
    errors = validate_visuals(visuals, read_json(d / "scenes.json"), d)
    if errors:
        abort(400, "; ".join(errors[:5]))
    write_json(d / "visuals.json", visuals)
    return jsonify(ok=True)


@app.post("/api/projects/<pid>/visuals/<step>")
def run_visuals(pid, step):
    d = project_dir(pid)
    from ..visuals import is_approved
    if step not in ("prompts", "cast", "scenes"):
        abort(404)
    if not (d / "scenes.json").exists():
        abort(400, "Write or create the script first")
    if not is_approved(d):
        abort(409, "Kịch bản chưa được duyệt: đọc và bấm “Duyệt kịch bản” ở tab Kịch bản trước")
    from ..visuals import is_cast_approved
    if step == "scenes" and not is_cast_approved(d):
        abort(409, "Ảnh mẫu nhân vật chưa được duyệt: xem từng nhân vật rồi bấm “Duyệt nhân vật”")
    body = request.get_json(silent=True) or {}
    args = [step, str(d)]
    if step == "prompts":
        if body.get("provider") in ("offline", "muse", "openai", "codex"):
            args += ["--provider", body["provider"]]
        if body.get("ratio") in ("16:9", "9:16"):
            args += ["--ratio", body["ratio"]]
    if body.get("only") is not None and re.fullmatch(r"[a-z0-9_]+", str(body["only"])):
        args += ["--only", str(body["only"])]
    if body.get("redo"):
        args.append("--redo")
    if body.get("images_only"):
        args.append("--images-only")
    if body.get("clips_only"):
        args.append("--clips-only")
    start_job(pid, d, f"visuals_{step}", args, module="storyvid.visuals")
    return jsonify(job_status(pid, d))


@app.post("/api/muse/launch")
def muse_launch():
    """Open the MuseFlow app (museflow/, npm start) if its API is not answering."""
    from ..visuals import muse
    try:
        muse("/api/status", timeout=3)
        return jsonify(ok=True, started=False)
    except RuntimeError:
        pass
    npm = shutil.which("npm")
    if not npm:
        abort(500, "npm not found: install Node.js, then run cd museflow && npm install")
    if not (ROOT / "museflow" / "node_modules").exists():
        subprocess.run([npm, "install"], cwd=ROOT / "museflow", capture_output=True)
    subprocess.Popen([npm, "start"], cwd=ROOT / "museflow", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)
    return jsonify(ok=True, started=True)


# ---------- styles (storyvid/styles.py) ----------
@app.get("/api/projects/<pid>/styles")
def list_styles(pid):
    from .. import styles
    d = project_dir(pid)
    out = []
    for key, p in [*styles.PRESETS.items(), (styles.CUSTOM, {"label": "Tự viết", "about": "Mô tả phong cách của bạn"})]:
        sample = styles.existing_sample(key, d)
        out.append({"id": key, "label": p["label"], "about": p["about"],
                    "sample": f"/files/{pid}/style/{key}?v={int(sample.stat().st_mtime)}" if sample else None})
    return jsonify(out)


@app.post("/api/projects/<pid>/styles/sample")
def sample_styles(pid):
    from .. import styles
    d = project_dir(pid)
    body = request.get_json(silent=True) or {}
    meta = read_json(d / "meta.json", {})
    args = ["sample", "--project", str(d), "--ratio", meta.get("ratio", "9:16")]
    if body.get("preset") in (*styles.PRESETS, styles.CUSTOM):
        args += ["--preset", body["preset"]]
    if body.get("redo"):
        args.append("--redo")
    start_job(pid, d, "style_samples", args, module="storyvid.styles")
    return jsonify(job_status(pid, d))


@app.get("/files/<pid>/style/<preset>")
def style_file(pid, preset):
    from .. import styles
    d = project_dir(pid)
    if preset not in (*styles.PRESETS, styles.CUSTOM):
        abort(404)
    sample = styles.existing_sample(preset, d)
    if not sample:
        abort(404)
    return send_file(sample)


# ---------- voices ----------
@app.get("/api/voices")
def list_voices():
    from ..vieneu import VOICES
    lang = request.args.get("lang", "en")
    channel = read_json(CHANNEL_PATH, {})
    providers = [{"id": "edge", "label": "Edge (miễn phí, không chính thức)",
                  "voices": [channel.get("voices", {}).get(lang, "")]},
                 {"id": "elevenlabs", "label": "ElevenLabs (cần key, tính ký tự)", "voices": []}]
    if lang == "vi":
        providers.append({"id": "vieneu", "label": "VieNeu-TTS (tiếng Việt, chạy trên máy, miễn phí)",
                          "voices": [{"id": k, "label": f"{k} — {v}"} for k, v in VOICES.items()]})
    return jsonify(providers=providers, default=read_env().get("TTS_PROVIDER") or "edge")


_preview_lock = threading.Lock()


@app.post("/api/voice-preview")
def voice_preview():
    """A short sample of a VieNeu or Edge voice (ElevenLabs is skipped: it spends characters)."""
    from .. import tts, vieneu
    body = request.get_json(force=True)
    provider, voice = body.get("provider"), str(body.get("voice") or "")
    text = {"vi": "Xin chào, đây là giọng đọc thử cho video của bạn.",
            "en": "Hello, this is a sample of the narrator's voice."}.get(body.get("lang"), "Hello, this is a sample.")
    out = ROOT / "cache" / "voice-preview" / f"{provider}-{re.sub(r'[^A-Za-z0-9]+', '_', voice) or 'default'}"
    out.parent.mkdir(parents=True, exist_ok=True)
    with _preview_lock:  # one model in memory, one synthesis at a time
        if provider == "vieneu":
            path = out.with_suffix(".wav")
            if not path.exists():
                vieneu.synthesize(text, voice or vieneu.narrator_voice(), path)
        elif provider == "edge":
            path = out.with_suffix(".mp3")
            if not path.exists():
                tts._synthesize(text, voice or read_json(CHANNEL_PATH, {}).get("voices", {}).get(body.get("lang"), ""),
                                path)
        else:
            abort(400, "Preview is available for VieNeu and Edge voices")
    return send_file(path)


# ---------- finishing (storyvid/finish.py) ----------
@app.get("/api/projects/<pid>/flow")
def get_flow(pid):
    """The progress diagram (storyvid/flow.py), drawn by MuseFlow's Canvas tab."""
    from ..flow import steps
    d = project_dir(pid)
    meta = read_json(d / "meta.json", {})
    status = job_status(pid, d)
    return jsonify(id=pid, name=meta.get("name", pid), job=status, steps=steps(d, status))


@app.get("/api/projects/<pid>/finish")
def get_finish(pid):
    d = project_dir(pid)
    frames = sorted((d / "publish" / "frames").glob("scene_*.jpg"))
    return jsonify(finish=read_json(d / "finish.json", {}), review=read_json(d / "review.json"),
                   publish=read_json(d / "publish" / "publish.json"),
                   frames={int(p.stem.split("_")[1]): f"/files/{pid}/publish/frames/{p.name}?v={int(p.stat().st_mtime)}"
                           for p in frames})


@app.post("/api/projects/<pid>/finish/<step>")
def run_finish(pid, step):
    d = project_dir(pid)
    if step not in ("check", "loudnorm", "review", "publish"):
        abort(404)
    body = request.get_json(silent=True) or {}
    args = [step, str(d)]
    if body.get("video") == "video_short":
        args += ["--video", "video_short"]
    if body.get("provider") in ("muse", "claude", "openai", "codex"):
        args += ["--provider", body["provider"]]
    start_job(pid, d, f"finish_{step}", args, module="storyvid.finish")
    return jsonify(job_status(pid, d))


@app.get("/files/<pid>/publish/<path:name>")
def publish_file(pid, name):
    d = project_dir(pid)
    path = (d / "publish" / name).resolve()
    if not path.is_relative_to((d / "publish").resolve()) or not path.is_file():
        abort(404)
    return send_file(path, conditional=True)


# ---------- real places (storyvid/places.py): photos attached to the scenes that show them ----------
def places_reply(d: Path):
    from .. import places
    data, script, visuals = places.load(d), read_json(d / "scenes.json", {}), read_json(d / "visuals.json")
    return jsonify(places=[{**p, "used_in": places.scenes_of(p, script, visuals) if script else []}
                           for p in data["places"]])


def find_place(data: dict, place_id: str) -> dict:
    for p in data["places"]:
        if p["id"] == place_id:
            return p
    abort(404, "No such place")


@app.get("/api/projects/<pid>/places")
def get_places(pid):
    return places_reply(project_dir(pid))


@app.post("/api/projects/<pid>/places")
def add_place(pid):
    from .. import places
    d = project_dir(pid)
    body = request.get_json(silent=True) or {}
    name = str(body.get("name", "")).strip()
    if not name:
        abort(400, "Give the place a name")
    data = places.load(d)
    place_id = places.slug(name, {p["id"] for p in data["places"]})
    data["places"].append(places.clean({"id": place_id, "name": name, "keywords": body.get("keywords", [])}))
    places.save(d, data)
    return places_reply(d)


@app.put("/api/projects/<pid>/places/<place_id>")
def edit_place(pid, place_id):
    from .. import places
    d = project_dir(pid)
    data = places.load(d)
    place = find_place(data, place_id)
    body = request.get_json(silent=True) or {}
    place.update(places.clean({**place, **{k: body[k] for k in ("name", "keywords", "scenes", "skip") if k in body}}))
    places.save(d, data)
    return places_reply(d)


@app.delete("/api/projects/<pid>/places/<place_id>")
def delete_place(pid, place_id):
    from .. import places
    d = project_dir(pid)
    data = places.load(d)
    find_place(data, place_id)
    data["places"] = [p for p in data["places"] if p["id"] != place_id]
    places.save(d, data)
    shutil.rmtree(d / "refs" / place_id, ignore_errors=True)
    return places_reply(d)


@app.post("/api/projects/<pid>/places/<place_id>/photos")
def add_place_photos(pid, place_id):
    """Multipart files ("photos"), or JSON {"url": "..."} to download one image."""
    from .. import places
    d = project_dir(pid)
    data = places.load(d)
    place = find_place(data, place_id)
    try:
        if request.files:
            for f in request.files.getlist("photos"):
                place["files"].append(places.add_photo(d, place, f.read(), f.filename or "photo"))
        else:
            url = str((request.get_json(silent=True) or {}).get("url", "")).strip()
            raw, name = places.download(url)
            place["files"].append(places.add_photo(d, place, raw, name))
            place["sources"].append(url)
    except (ValueError, OSError) as e:
        abort(400, str(e))
    places.save(d, data)
    return places_reply(d)


@app.delete("/api/projects/<pid>/places/<place_id>/photos/<path:name>")
def delete_place_photo(pid, place_id, name):
    from .. import places
    d = project_dir(pid)
    data = places.load(d)
    place = find_place(data, place_id)
    rel = f"refs/{place_id}/{name}"
    if rel not in place["files"]:
        abort(404, "No such photo")
    place["files"].remove(rel)
    (d / rel).unlink(missing_ok=True)
    places.save(d, data)
    return places_reply(d)


@app.get("/files/<pid>/refs/<path:name>")
def ref_file(pid, name):
    d = project_dir(pid)
    path = (d / "refs" / name).resolve()
    if not path.is_relative_to((d / "refs").resolve()) or not path.is_file():
        abort(404)
    return send_file(path, conditional=True)


@app.get("/files/<pid>/muse/<path:name>")
def muse_file(pid, name):
    d = project_dir(pid)
    path = (d / "muse" / name).resolve()
    if not path.is_relative_to((d / "muse").resolve()) or not path.is_file():
        abort(404)
    return send_file(path, conditional=True)


def kill_group(proc: subprocess.Popen) -> None:
    """A job and the steps it started (storyvid.auto runs one child per step): SIGTERM, then SIGKILL after 5 s."""
    import signal
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return

    def finish():
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        try:
            os.killpg(proc.pid, signal.SIGKILL)  # whatever is left of the group
        except ProcessLookupError:
            pass

    threading.Thread(target=finish, daemon=True).start()


@app.post("/api/projects/<pid>/stop")
def stop_job(pid):
    d = project_dir(pid)
    with jobs_lock:
        proc = jobs.get(pid)
    if proc and proc.poll() is None:
        kill_group(proc)
        if read_json(d / "job.json", {}).get("kind", "").startswith(("visuals_", "auto")):
            from ..visuals import muse  # also cancel what MuseFlow is generating right now
            try:
                muse("/api/stop", {}, timeout=10)
            except RuntimeError:
                pass
    return jsonify(ok=True)


@app.get("/api/projects/<pid>/log")
def get_log(pid):
    d = project_dir(pid)
    log = (d / "log.txt").read_text(encoding="utf-8", errors="replace") if (d / "log.txt").exists() else ""
    return jsonify(status=job_status(pid, d), log=log[-20000:])


@app.get("/files/<pid>/<name>.mp4")
def video_file(pid, name):
    d = project_dir(pid)
    if name not in ("video", "video_short") or not (d / f"{name}.mp4").exists():
        abort(404)
    return send_file(d / f"{name}.mp4", conditional=True)


@app.get("/files/<pid>/bg/<bg_id>")
def bg_file(pid, bg_id):
    d = project_dir(pid)
    path = read_json(d / "backgrounds.json", {}).get(bg_id)
    if not path or not Path(path).resolve().is_relative_to((ROOT / "cache").resolve()):
        abort(404)
    return send_file(path)


# ---------- settings ----------
@app.get("/api/settings")
def get_settings():
    env = read_env()
    masked = {k: ("" if k in SECRET_KEYS else v) for k, v in env.items()}
    masked["_secret_set"] = {k: bool(env[k]) for k in SECRET_KEYS}
    return jsonify(env=masked, channel=read_json(CHANNEL_PATH, {}))


@app.put("/api/settings")
def put_settings():
    body = request.get_json(force=True)
    env_in = body.get("env", {})
    updates = {}
    for k in ENV_KEYS:
        if k not in env_in:
            continue
        v = str(env_in[k]).strip().replace("\n", "")
        if k in SECRET_KEYS and not v:
            continue  # blank secret field = keep the stored key
        updates[k] = v
    if updates:
        write_env(updates)
    if "channel" in body:
        write_json(CHANNEL_PATH, body["channel"])
    return get_settings()


@app.post("/api/character-preview")
def character_preview():
    """Preview sheet of the host in every pose, using the colours sent from the settings form."""
    body = request.get_json(force=True) or {}
    host = body.get("host") or read_json(CHANNEL_PATH, {})["host"]
    try:
        ch = Character(resolve_character(host, body.get("character")), 220)
    except (KeyError, ValueError, TypeError) as e:
        abort(400, str(e))
    poses = list(ARM_POSES)
    exprs = EXPRESSIONS
    w = ch.width + 10
    sheet = Image.new("RGBA", (w * max(len(poses), len(exprs)), 2 * 235), (0, 0, 0, 0))
    for i, p in enumerate(poses):
        s = ch.sprite(p, "neutral", 0, False, False)
        sheet.paste(s, (i * w, 5), s)
    for i, e in enumerate(exprs):
        s = ch.sprite("talk", e, 0, False, False)
        sheet.paste(s, (i * w, 240), s)
    buf = io.BytesIO()
    sheet.save(buf, "PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.get("/api/character-thumb")
def character_thumb():
    """One standing sprite for a cast member card (preset/outfit/accessory/kind as query args)."""
    choice = {k: request.args[k] for k in ("preset", "outfit", "accessory") if request.args.get(k)}
    try:
        ch = Character(resolve_character(read_json(CHANNEL_PATH, {})["host"], choice), 180)
    except (KeyError, ValueError) as e:
        abort(400, str(e))
    sprite = ch.sprite("idle", "neutral", 0, False, False)
    if request.args.get("kind") == "ghost":
        import numpy as np
        arr = np.asarray(sprite).astype(np.float32)
        arr[..., :3] = arr[..., :3] * 0.4 + np.array((205, 228, 238)) * 0.6
        arr[..., 3] *= 0.6
        sprite = Image.fromarray(arr.astype(np.uint8), "RGBA")
    buf = io.BytesIO()
    sprite.save(buf, "PNG")
    buf.seek(0)
    response = send_file(buf, mimetype="image/png")
    response.headers["Cache-Control"] = "max-age=3600"
    return response


@app.errorhandler(400)
@app.errorhandler(404)
@app.errorhandler(409)
def api_error(e):
    return jsonify(error=e.description), e.code


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    print(f"storyvid web UI: http://127.0.0.1:{port}")
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
