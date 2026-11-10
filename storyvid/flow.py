"""Where a project stands, step by step, for the progress diagram (MuseFlow tab Canvas, GET /api/projects/<id>/flow).

Each step: {"key", "label", "state": done|running|todo|wait|error, "detail", "tab"}. "wait" means a person has to
act (approve the script or the characters); "tab" is the storyvid web UI tab that handles the step.
"""
import json
from pathlib import Path

from .visuals import cast_ready, is_approved, is_cast_approved, load

# job kinds (web UI job.json) -> the step they work on; "auto" and visuals_scenes go to the first unfinished step
JOB_STEP = {"script": "script", "script_review": "script", "script_revise": "script", "script_auto": "script",
            "script_polish": "story", "style_samples": "style", "visuals_prompts": "prompts", "visuals_cast": "cast",
            "render": "video", "finish_check": "check", "finish_loudnorm": "check", "finish_review": "review",
            "finish_publish": "publish"}


def _json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def steps(project: Path, job: dict | None = None) -> list[dict]:
    meta = _json(project / "meta.json", {})
    script = _json(project / "scenes.json")
    story = (project / "story.txt").read_text(encoding="utf-8").strip() if (project / "story.txt").exists() else ""
    visuals = load(project)[1] if script else None
    n = len((script or {}).get("scenes", []))
    has = lambda key: sum(1 for s in (visuals or {}).get("scenes", [])  # noqa: E731
                          if s[key] and (project / s[key]).is_file())
    errors = sum(1 for s in (visuals or {}).get("scenes", []) if s.get("error"))
    cast = (visuals or {}).get("cast", [])
    sheets = sum(1 for c in cast if c["sheet"] and (project / c["sheet"]).is_file())
    finish = _json(project / "finish.json", {})
    check, review = finish.get("check_video") or {}, finish.get("review") or {}
    approved, cast_ok = is_approved(project), is_cast_approved(project, visuals)
    from . import continuity
    locks_ok = continuity.status(project)["approved"] if visuals else False

    def step(key, label, done, detail="", tab="", wait=False):
        return {"key": key, "label": label, "state": "done" if done else "wait" if wait else "todo",
                "detail": detail, "tab": tab}

    out = [
        step("style", "Phong cách", bool(meta.get("style")), (meta.get("style") or {}).get("preset", ""), "style"),
        step("story", "Truyện", bool(story), f"{len(story.split())} từ" if story else "", "story"),
        step("script", "Kịch bản", bool(script), f"{n} cảnh" if script else "", "script"),
        step("approve", "Duyệt kịch bản", approved, "người duyệt" if approved else "chờ bạn đọc và duyệt",
             "script", wait=bool(script)),
        step("prompts", "Prompt hình", bool(visuals), f"{n} cảnh" if visuals else "", "muse"),
        step("cast", "Ảnh nhân vật", cast_ready(project, visuals), f"{sheets}/{len(cast)}" if visuals else "", "muse"),
        step("approve_cast", "Duyệt nhân vật", cast_ok, "người duyệt" if cast_ok else "chờ bạn xem và duyệt",
             "muse", wait=cast_ready(project, visuals)),
        step("approve_references", "Duyệt bộ mẫu", locks_ok,
             "đã khóa" if locks_ok else "mở Khóa hình ảnh, xem và duyệt bộ mẫu", "muse", wait=cast_ok),
        step("images", "Ảnh cảnh", bool(n) and has("image") == n, f"{has('image')}/{n}" if visuals else "", "muse"),
        step("clips", "Clip cảnh", bool(n) and has("clip") == n, f"{has('clip')}/{n}" if visuals else "", "muse"),
        step("video", "Dựng video", (project / "video.mp4").exists(),
             "video.mp4" if (project / "video.mp4").exists() else "", "video"),
        step("check", "Máy kiểm tra", bool(check.get("ok")),
             "đạt" if check.get("ok") else "chưa đạt" if check else "", "finish"),
        step("review", "AI kiểm định", review.get("verdict") == "pass", review.get("verdict", ""), "finish"),
        step("publish", "Gói đăng", (project / "publish" / "publish.json").exists(), "", "finish"),
        step("published", "Đã đăng", bool(meta.get("published")), "", "finish"),
    ]
    if errors:
        for s in out:
            if s["key"] in ("images", "clips") and s["state"] != "done":
                s["state"], s["detail"] = "error", f"{s['detail']} · {errors} lỗi"
                break
    gate = out[[s["key"] for s in out].index("approve_cast")]
    if gate["state"] != "done" and n and has("image") == n:  # made before the character gate existed
        gate["state"], gate["detail"] = "done", "làm trước khi có bước duyệt"
    if review.get("verdict") not in (None, "pass"):
        out[[s["key"] for s in out].index("review")]["state"] = "error"
    if check and not check.get("ok"):
        out[[s["key"] for s in out].index("check")]["state"] = "error"
    if job and job.get("state") == "running":
        key = JOB_STEP.get(job.get("kind", ""))
        target = next((s for s in out if s["key"] == key), None) if key else \
            next((s for s in out if s["state"] != "done" and s["state"] != "wait"), None)
        if target:
            target["state"] = "running"
    return out
