"""Runs the rest of a project in one go, stopping only where a person has to look.

    python -m storyvid.auto output/<id> [--res 720|1080] [--provider muse|offline|openai|codex]

Steps, each skipped when its output is already there:
    1. picture prompts (visuals.json)          storyvid.visuals prompts
    2. character sheets                        storyvid.visuals cast
       -> stops until a person approves the sheets (web UI "Duyệt nhân vật", meta.json "approved_cast")
    3. scene images and clips (failed scenes get one more try)
                                               storyvid.visuals scenes
    4. the video with voice and subtitles      storyvid.cli --visuals
    5. loudness to YouTube level, then the machine checks
                                               storyvid.finish loudnorm, storyvid.finish check
The AI review and the publish kit (tab Hoàn thành) stay manual: a person watches the video first.
The script must already be approved (meta.json "approved_script").
"""
import argparse
import os
import signal
import subprocess
import sys
from pathlib import Path

from .visuals import cast_ready, is_approved, is_cast_approved, load, meta

ROOT = Path(__file__).resolve().parents[1]
WAITING_CAST = "WAITING: xem và bấm “Duyệt nhân vật” ở tab Hình Muse, rồi bấm “Chạy tự động” lần nữa."
child: subprocess.Popen | None = None


def step(title: str, module: str, *args: str) -> int:
    global child
    print(f"\n=== {title} ===\n$ {module} {' '.join(args)}", flush=True)
    child = subprocess.Popen([sys.executable, "-m", module, *args], cwd=ROOT)
    code = child.wait()
    child = None
    return code


def stop(_signum, _frame) -> None:
    """The web UI's Stop button terminates this process: take the running step down with it and leave at once
    (raising SystemExit from here left the process hanging until a second Stop)."""
    if child and child.poll() is None:
        child.terminate()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
    print("Stopped", flush=True)
    os._exit(1)


def scenes_left(project: Path) -> int:
    _, visuals = load(project)
    return sum(1 for s in visuals["scenes"] if not (s["clip"] and (project / s["clip"]).is_file()))


def run(project: Path, res: str, provider: str) -> int:
    if not is_approved(project):
        print("The script is not approved yet: read it and press “Duyệt kịch bản” in tab Kịch bản first.")
        return 1
    p = str(project)
    if load(project)[1] is None:
        if step("1/5 Viết prompt hình", "storyvid.visuals", "prompts", p, "--provider", provider):
            return 1
    else:
        print("1/5 prompt hình: đã có")
    if not cast_ready(project, load(project)[1]):
        if step("2/5 Ảnh mẫu nhân vật", "storyvid.visuals", "cast", p):
            return 1
    else:
        print("2/5 ảnh mẫu nhân vật: đã có")
    if not is_cast_approved(project):
        print("\n" + WAITING_CAST)
        return 0
    for attempt in (1, 2):
        if not scenes_left(project):
            print("3/5 ảnh và clip các cảnh: đã đủ")
            break
        code = step(f"3/5 Ảnh và clip các cảnh (lần {attempt})", "storyvid.visuals", "scenes", p)
        if code and attempt == 2:
            print(f"{scenes_left(project)} cảnh vẫn lỗi: xem ô lỗi từng cảnh ở tab Hình Muse, sửa prompt rồi chạy lại.")
            return 1
    info = meta(project)
    if step("4/5 Dựng video", "storyvid.cli", "--script", str(project / "scenes.json"), "--out", p,
            "--lang", info.get("lang", "en"), "--res", res, "--visuals"):
        return 1
    if step("5/5 Chuẩn hóa âm lượng", "storyvid.finish", "loudnorm", p):
        return 1
    code = step("5/5 Máy kiểm tra", "storyvid.finish", "check", p)
    print("\nXong: xem video ở tab Video, rồi làm tiếp AI kiểm định và gói đăng ở tab Hoàn thành.")
    return code


def main() -> None:
    sys.stdout.reconfigure(line_buffering=True)
    signal.signal(signal.SIGTERM, stop)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project")
    ap.add_argument("--res", choices=["480", "720", "1080"], default="1080")
    ap.add_argument("--provider", choices=["muse", "offline", "openai", "codex"], default="muse",
                    help="who writes the picture prompts")
    args = ap.parse_args()
    raise SystemExit(run(Path(args.project).resolve(), args.res, args.provider))


if __name__ == "__main__":
    main()
