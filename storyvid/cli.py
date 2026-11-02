"""Story text -> LLM script -> narration -> backgrounds -> video with the channel host.

    python -m storyvid.cli examples/ma_da.txt --lang en
    python -m storyvid.cli --script output/ma_da/scenes.json      # re-render an edited script
    python -m storyvid.cli --script output/ma_da/scenes.json --short   # 9:16 Short -> video_short.mp4
    python -m storyvid.cli --script output/ma_da/scenes.json --visuals  # Muse clips from visuals.json
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from .backgrounds import make_backgrounds
from .check import check_script
from .contract import FORMAT
from .render import Renderer, ShortRenderer
from .script import write_script
from .tts import narrate, tts_provider, write_srt

ROOT = Path(__file__).resolve().parent.parent
RESOLUTIONS = {"480": (854, 480), "720": (1280, 720), "1080": (1920, 1080)}
SHORT_TARGET = 55.0  # seconds; YouTube allows up to 3 minutes but 30-60 s works best
WORDS_PER_SECOND = 2.6


def short_scenes(script: dict) -> list[int]:
    """The scenes of the Short: script["short"]["scenes"], else the opening scenes up to about SHORT_TARGET."""
    if script.get("short"):
        return script["short"]["scenes"]
    picked, seconds = [], 0.0
    for i, scene in enumerate(script["scenes"]):
        words = sum(len(line["text"].split()) for line in scene["lines"])
        seconds += words / WORDS_PER_SECOND + 0.4 * len(scene["lines"])
        if picked and seconds > SHORT_TARGET:
            break
        picked.append(i)
    return picked


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
    ap.add_argument("--lang", help="narration language: en, vi, de, fr, es (default: the script's lang, else en)")
    ap.add_argument("--minutes", type=float, default=2.0, help="target narration length")
    ap.add_argument("--genre", choices=["story", "explainer"], default="story",
                    help="story = ghost/folklore story; explainer = science or psychology explainer")
    ap.add_argument("--keep-text", action="store_true",
                    help="the text is already the narration: split it into scenes without rewriting it")
    ap.add_argument("--provider", choices=["auto", "muse", "openai", "codex", "claude", "offline"], default="auto",
                    help="auto = LLM_PROVIDER from .env; muse = Muse through MuseFlow (no key); openai = any "
                         "OpenAI-compatible API; codex = Codex CLI; claude = Anthropic API; offline = split the text as-is")
    ap.add_argument("--channel", default=str(ROOT / "channel.json"))
    ap.add_argument("--res", choices=RESOLUTIONS, default="720")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--out", help="output folder (default: output/<story name>)")
    ap.add_argument("--script-only", action="store_true", help="stop after writing scenes.json")
    ap.add_argument("--short", action="store_true",
                    help="render the 9:16 Short (script's short.scenes, else the opening ~55 s) as video_short.mp4")
    ap.add_argument("--fallback", action="store_true",
                    help="render even when assets are missing: nearest pack background, missing props skipped")
    ap.add_argument("--visuals", action="store_true",
                    help="use the Muse clips in visuals.json (python -m storyvid.visuals) instead of the stage")
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
        script = write_script(story, channel, args.lang or "en", args.minutes, provider, previous.get("character"),
                              args.genre, args.keep_text)
        if "character" in previous:
            from .character_catalog import validate_selection
            script["character"] = validate_selection(previous["character"])
        (out_dir / "scenes.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  {len(script['scenes'])} scenes -> {out_dir / 'scenes.json'}")

    # every script, whoever wrote it, must follow the contract before anything is rendered
    scenes_path = Path(args.script) if args.script else out_dir / "scenes.json"
    code = check_script(scenes_path)
    if code == 1:
        raise SystemExit(f"{scenes_path} does not follow {FORMAT} (see docs/pipeline.md)")
    if args.script_only:
        print(f"Done in {time.time() - started:.0f}s")
        return
    visuals = load_visuals(scenes_path, script, args.fallback) if args.visuals else None
    if code == 2 and not args.fallback and not visuals:
        raise SystemExit(f"Assets missing: hand {scenes_path.parent / 'asset_requests.json'} to the asset agent, "
                         "or rerun with --fallback")
    args.lang = args.lang or script["lang"]

    out_dir.mkdir(parents=True, exist_ok=True)
    voice = channel["voices"].get(args.lang)
    if not voice:
        raise SystemExit(f"No voice configured for '{args.lang}' in {args.channel}")

    if args.short:
        render_short(script, channel, voice, out_dir, args, visuals)
        print(f"Done in {time.time() - started:.0f}s -> {out_dir / 'video_short.mp4'}")
        return

    provider = tts_provider()
    print(f"[2/4] Narrating with {voice if provider == 'edge' else provider}...")
    timeline = narrate(script, voice, out_dir, args.lang)
    print(f"  subtitles -> {write_srt(timeline['cues'], out_dir / 'video.srt')}")
    add_sound(script, timeline, out_dir)

    size = RESOLUTIONS[args.res]
    if visuals:
        from .render_clips import ClipRenderer, scene_media
        if visuals["ratio"] == "9:16":
            size = (size[1], size[0])
        video = out_dir / "video.mp4"
        print(f"[3/3] Rendering {timeline['duration']:.1f}s from Muse clips at {size[0]}x{size[1]}...")
        media = scene_media(scenes_path.parent, visuals, list(range(len(script["scenes"]))))
        ClipRenderer(channel, size, args.fps).render_clips(timeline, media, video)
        print(f"Done in {time.time() - started:.0f}s -> {video}")
        return
    print("[3/4] Backgrounds...")
    bg_paths = make_backgrounds(script, (int(size[0] * 1.15), int(size[1] * 1.15)),
                                ROOT / "cache" / "backgrounds")
    (out_dir / "backgrounds.json").write_text(
        json.dumps({k: str(v) for k, v in bg_paths.items()}, indent=2), encoding="utf-8")

    print(f"[4/4] Rendering {timeline['duration']:.1f}s at {size[0]}x{size[1]}...")
    video = out_dir / "video.mp4"
    Renderer(channel, size, args.fps).render(script, timeline, bg_paths, video)
    print(f"Done in {time.time() - started:.0f}s -> {video}")


def add_sound(script: dict, timeline: dict, work_dir: Path) -> None:
    """Mix music, ambience and sfx under the voice; the renderer still lip-syncs to the voice alone."""
    from . import audio
    if not audio.has_sound(script):
        return
    print("  mixing music and sound effects")
    timeline["audio"] = audio.mix(script, timeline, work_dir / "mix.wav")
    credits = audio.attributions(script)
    if credits:
        (work_dir / "credits.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")
        print(f"  credits for the description -> {work_dir / 'credits.txt'}")


def load_visuals(scenes_path: Path, script: dict, fallback: bool) -> dict:
    """visuals.json next to the script, checked; every scene needs a clip or image unless --fallback."""
    from .contract import validate_visuals
    path = scenes_path.parent / "visuals.json"
    if not path.exists():
        raise SystemExit(f"No {path}: run python -m storyvid.visuals prompts {scenes_path.parent}")
    visuals = json.loads(path.read_text(encoding="utf-8"))
    errors = validate_visuals(visuals, script, scenes_path.parent)
    if errors:
        raise SystemExit("\n".join(f"ERROR {e}" for e in errors))
    missing = [i + 1 for i, s in enumerate(visuals["scenes"]) if not s["clip"] and not s["image"]]
    if missing and not fallback:
        raise SystemExit(f"Scenes without a clip or image: {missing}. Run python -m storyvid.visuals scenes "
                         f"{scenes_path.parent}, or rerun with --fallback (black frames)")
    return visuals


def render_short(script: dict, channel: dict, voice: str, out_dir: Path, args, visuals: dict | None = None) -> None:
    picked = short_scenes(script)
    short = {**script, "scenes": [script["scenes"][i] for i in picked]}
    print(f"[short] scenes {picked}")
    provider = tts_provider()
    print(f"[2/4] Narrating with {voice if provider == 'edge' else provider}...")
    timeline = narrate(short, voice, out_dir / "short", args.lang)
    print(f"  subtitles -> {write_srt(timeline['cues'], out_dir / 'video_short.srt')}")
    add_sound(short, timeline, out_dir / "short")
    if timeline["duration"] > 60:
        print(f"  warning: {timeline['duration']:.0f}s is longer than 60 s; pick fewer scenes in short.scenes")
    width = RESOLUTIONS[args.res][1]  # 720 -> a 720x1280 Short
    if visuals:
        from .render_clips import ShortClipRenderer, scene_media
        renderer = ShortClipRenderer(channel, width, args.fps, script["title"], args.lang)
        print(f"[3/3] Rendering {timeline['duration']:.1f}s from Muse clips at "
              f"{renderer.out_size[0]}x{renderer.out_size[1]}...")
        renderer.render_clips(timeline, scene_media(out_dir, visuals, picked), out_dir / "video_short.mp4")
        return
    print("[3/4] Backgrounds...")
    renderer = ShortRenderer(channel, width, args.fps, script["title"], args.lang)
    stage = int(renderer.H * 1.15)  # the vertical stage is cover-filled from a background this tall
    bg_paths = make_backgrounds(short, (stage, stage), ROOT / "cache" / "backgrounds")
    print(f"[4/4] Rendering {timeline['duration']:.1f}s at {renderer.out_size[0]}x{renderer.out_size[1]}...")
    renderer.render(short, timeline, bg_paths, out_dir / "video_short.mp4")


if __name__ == "__main__":
    main()
