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
            "IMAGE_PROVIDER", "FAL_KEY", "TTS_PROVIDER", "ELEVENLABS_API_KEY", "ELEVENLABS_MODEL",
            "ELEVENLABS_NARRATOR_VOICE"]
SECRET_KEYS = {"LLM_API_KEY", "FAL_KEY", "ELEVENLABS_API_KEY"}

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.json.sort_keys = False  # keep channel.json and language lists in their written order
jobs: dict[str, subprocess.Popen] = {}
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
        "video_mtime": int(video.stat().st_mtime) if video.exists() else None,
        "updated": int(max((p.stat().st_mtime for p in d.iterdir()), default=d.stat().st_mtime)),
        "status": job_status(d.name, d),
    }


def start_job(pid: str, d: Path, kind: str, args: list[str]) -> None:
    with jobs_lock:
        proc = jobs.get(pid)
        if proc and proc.poll() is None:
            abort(409, "A job is already running for this project")
        log = open(d / "log.txt", "w", encoding="utf-8")
        log.write(f"$ storyvid {' '.join(args)}\n")
        log.flush()
        proc = subprocess.Popen([sys.executable, "-m", "storyvid.cli", *args], cwd=ROOT,
                                stdout=log, stderr=subprocess.STDOUT, env={**os.environ, "PYTHONUNBUFFERED": "1"})
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
                                 "minutes": float(body.get("minutes", 2)), "created": int(time.time())})
    return jsonify(summary(d))


@app.get("/api/projects/<pid>")
def get_project(pid):
    d = project_dir(pid)
    data = summary(d)
    data["meta"] = read_json(d / "meta.json", {})
    data["story"] = (d / "story.txt").read_text(encoding="utf-8") if (d / "story.txt").exists() else ""
    data["script"] = read_json(d / "scenes.json")
    if data["script"]:
        try:  # older scripts (one host per scene) open in the cast editor; the file changes only on save
            data["script"] = _normalize(data["script"])
        except (RuntimeError, ValueError):
            pass
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
    if "minutes" in body:
        meta["minutes"] = float(body["minutes"])
    write_json(d / "meta.json", meta)
    if "story" in body:
        (d / "story.txt").write_text(body["story"], encoding="utf-8")
    if "script" in body:
        try:
            write_json(d / "scenes.json", _normalize(body["script"]))
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


@app.post("/api/projects/<pid>/script")
def run_script(pid):
    d = project_dir(pid)
    body = request.get_json(silent=True) or {}
    meta = read_json(d / "meta.json", {})
    args = [str(d / "story.txt"), "--script-only", "--out", str(d), "--lang", meta.get("lang", "en"),
            "--minutes", str(meta.get("minutes", 2))]
    if body.get("provider"):
        args += ["--provider", body["provider"]]
    start_job(pid, d, "script", args)
    return jsonify(job_status(pid, d))


@app.post("/api/projects/<pid>/render")
def run_render(pid):
    d = project_dir(pid)
    if not (d / "scenes.json").exists():
        abort(400, "Write or create the script first")
    body = request.get_json(silent=True) or {}
    meta = read_json(d / "meta.json", {})
    res = body.get("res", "720") if body.get("res") in ("480", "720", "1080") else "720"
    start_job(pid, d, "render", ["--script", str(d / "scenes.json"), "--out", str(d),
                                 "--lang", meta.get("lang", "en"), "--res", res])
    return jsonify(job_status(pid, d))


@app.post("/api/projects/<pid>/stop")
def stop_job(pid):
    d = project_dir(pid)
    with jobs_lock:
        proc = jobs.get(pid)
    if proc and proc.poll() is None:
        proc.terminate()
    return jsonify(ok=True)


@app.get("/api/projects/<pid>/log")
def get_log(pid):
    d = project_dir(pid)
    log = (d / "log.txt").read_text(encoding="utf-8", errors="replace") if (d / "log.txt").exists() else ""
    return jsonify(status=job_status(pid, d), log=log[-20000:])


@app.get("/files/<pid>/video.mp4")
def video_file(pid):
    d = project_dir(pid)
    if not (d / "video.mp4").exists():
        abort(404)
    return send_file(d / "video.mp4", conditional=True)


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
