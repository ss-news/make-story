"""Story text -> LLM script -> narration -> backgrounds -> video with the channel host.

    python -m storyvid.cli examples/ma_da.txt --lang en
    python -m storyvid.cli --script output/ma_da/scenes.json      # re-render an edited script
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from .backgrounds import make_backgrounds
from .render import Renderer
from .script import write_script
from .tts import narrate, tts_provider

ROOT = Path(__file__).resolve().parent.parent
RESOLUTIONS = {"480": (854, 480), "720": (1280, 720), "1080": (1920, 1080)}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40] or "video"


def load_env(path: Path) -> None:
    """Minimal .env reader: KEY=value lines; real environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.split(" #", 1)[0].strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


def main():
    load_env(ROOT / ".env")
    sys.stdout.reconfigure(line_buffering=True)  # the web UI tails this output live
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story", nargs="?", help="text file with the raw story (any language)")
    ap.add_argument("--script", help="skip the LLM and render an existing scenes.json")
    ap.add_argument("--lang", default="en", help="narration language: en, vi, de, fr, es")
    ap.add_argument("--minutes", type=float, default=2.0, help="target narration length")
    ap.add_argument("--provider", choices=["auto", "openai", "codex", "claude", "offline"], default="auto",
                    help="auto = LLM_PROVIDER from .env; openai = any OpenAI-compatible API; codex = Codex CLI; "
                         "claude = Anthropic API; offline = split the text as-is")
    ap.add_argument("--channel", default=str(ROOT / "channel.json"))
    ap.add_argument("--res", choices=RESOLUTIONS, default="720")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", help="output folder (default: output/<story name>)")
    ap.add_argument("--script-only", action="store_true", help="stop after writing scenes.json")
    args = ap.parse_args()
    if not args.story and not args.script:
        ap.error("give a story file or --script")

    channel = json.loads(Path(args.channel).read_text(encoding="utf-8"))
    started = time.time()

    if args.script:
        script = json.loads(Path(args.script).read_text(encoding="utf-8"))
        out_dir = Path(args.out) if args.out else Path(args.script).parent
    else:
        provider = args.provider
        if provider == "auto":
            provider = os.environ.get("LLM_PROVIDER", "").strip() or "offline"
            if provider == "offline":
                print("LLM_PROVIDER not set in .env: using offline mode (story is split, not rewritten).")
        story = Path(args.story).read_text(encoding="utf-8")
        out_dir = Path(args.out) if args.out else ROOT / "output" / _slug(Path(args.story).stem)
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"[1/4] Writing script ({provider})...")
        previous_path = out_dir / "scenes.json"
        previous = json.loads(previous_path.read_text(encoding="utf-8")) if previous_path.exists() else {}
        script = write_script(story, channel, args.lang, args.minutes, provider, previous.get("character"))
        if "character" in previous:
            from .character_catalog import validate_selection
            script["character"] = validate_selection(previous["character"])
        (out_dir / "scenes.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {len(script['scenes'])} scenes -> {out_dir / 'scenes.json'}")
        if args.script_only:
            print(f"Done in {time.time() - started:.0f}s")
            return

    out_dir.mkdir(parents=True, exist_ok=True)
    voice = channel["voices"].get(args.lang)
    if not voice:
        raise SystemExit(f"No voice configured for '{args.lang}' in {args.channel}")

    provider = tts_provider()
    print(f"[2/4] Narrating with {voice if provider == 'edge' else provider}...")
    timeline = narrate(script, voice, out_dir, args.lang)

    size = RESOLUTIONS[args.res]
    print("[3/4] Backgrounds...")
    bg_paths = make_backgrounds(script, channel["style_prompt"], (int(size[0] * 1.15), int(size[1] * 1.15)),
                                ROOT / "cache" / "backgrounds")
    (out_dir / "backgrounds.json").write_text(
        json.dumps({k: str(v) for k, v in bg_paths.items()}, indent=2), encoding="utf-8")

    print(f"[4/4] Rendering {timeline['duration']:.1f}s at {size[0]}x{size[1]}...")
    video = out_dir / "video.mp4"
    Renderer(channel, size, args.fps).render(script, timeline, bg_paths, video)
    print(f"Done in {time.time() - started:.0f}s -> {video}")


if __name__ == "__main__":
    main()
