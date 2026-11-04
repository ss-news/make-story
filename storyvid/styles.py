"""Visual styles a project can pick before the script is written, and Muse-made samples of them.

    python -m storyvid.styles sample                      every preset without a sample (cache/styles/)
    python -m storyvid.styles sample --preset stick --redo
    python -m storyvid.styles sample --project output/<id>   the project's own custom style

A project stores its choice in meta.json: "style": {"preset": "<id>", "text": "..."} (text only for custom).
The prompts step of storyvid.visuals copies the style text into visuals.json and the preset's reference
images into the project (style_refs), so every character sheet and scene image is drawn the same way.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "cache" / "styles"
SAMPLE_SUBJECT = ("A young woman standing in a small room at night, holding a glowing phone, a lamp on a table "
                  "beside her, a window behind her.")
NO_TEXT = "No text, subtitles, logos or watermark in frame."

PRESETS = {
    "stick": {
        "label": "Người que của kênh",
        "about": "Mặt tròn trắng, mắt chấm, tay chân que, màu phẳng. Gửi kèm nhân vật và cảnh mẫu của bộ người que.",
        "text": ("Flat 2D hand-drawn stick-figure cartoon, the same style as the attached reference images: characters "
                 "have big round white heads with black dot eyes and a simple outlined mouth, thin black stick arms "
                 "and legs, small flat-colour clothing shapes; clean even black outlines, flat muted colours, simple "
                 "flat backgrounds with few details, warm cream tones by day and deep blue tones at night. Any other "
                 "people are drawn as the same kind of stick figures. No shading gradients, no realism, no 3D. "
                 + NO_TEXT),
        "refs": ["assets/styles/stick/character.png", "assets/styles/stick/scene.png"],
    },
    "cartoon3d": {
        "label": "Hoạt hình 3D",
        "about": "Kiểu phim hoạt hình 3D: khối mềm, mắt to, ánh sáng ấm. Giữ nhân vật đều nhất, ít bị từ chối.",
        "text": ("Stylized 3D animated feature film look, soft rounded shapes, big expressive eyes, warm cinematic "
                 "lighting, clean textures, gentle depth of field. Not photorealistic. " + NO_TEXT),
        "refs": [],
    },
    "chibi": {
        "label": "Hoạt hình chibi",
        "about": "Đầu to, thân nhỏ, mắt long lanh, màu pastel. Dễ thương, hợp video kiến thức dài.",
        "text": ("Chibi anime style: characters with oversized round heads about one third of their height, big "
                 "sparkling eyes, tiny rounded bodies and short limbs, cute expressive faces, clean lineart, soft cel "
                 "shading, soft pastel colours, simple bright uncluttered backgrounds. Any other people are drawn as "
                 "the same kind of chibi characters. Not realistic. " + NO_TEXT),
        "refs": [],
    },
    "flat2d": {
        "label": "Hoạt hình 2D phẳng",
        "about": "Minh họa vector phẳng, màu tươi, hợp video giải thích kiến thức.",
        "text": ("Flat 2D vector illustration in a modern explainer-video style, simple geometric shapes, bold clean "
                 "colours, soft flat shadows, uncluttered backgrounds. " + NO_TEXT),
        "refs": [],
    },
    "painterly2d": {
        "label": "Tranh vẽ 2D nắng ấm",
        "about": "Tranh vẽ tay vệt cọ, nắng vàng, dáng người thật, như phim ngắn hoạt hình. Hợp truyện đời thường, cảm động.",
        "text": ("Painterly 2D animated short film look, hand-painted brush textures, bold flat colour shapes with soft "
                 "painted shading, warm natural light with gentle bloom, slightly stylised realistic proportions, "
                 "expressive faces, dynamic poses, cinematic framing. Not 3D, not photorealistic. " + NO_TEXT),
        "refs": [],
    },
    "dark2d": {
        "label": "Truyện ma 2D tối màu",
        "about": "Tranh vẽ tay tối, nét mực, bóng đổ sâu, hợp truyện ma của kênh.",
        "text": ("Dark hand-painted 2D illustration for a ghost story, ink outlines, muted desaturated palette with "
                 "one cold accent colour, deep shadows, fog and dim lamplight, eerie but not gory. " + NO_TEXT),
        "refs": [],
    },
    "cinematic": {
        "label": "Điện ảnh chân thực",
        "about": "Như cảnh phim thật. Đẹp nhưng dễ bị từ chối với nội dung nhạy cảm và khó giữ mặt nhân vật.",
        "text": ("Cinematic photorealistic film still, natural soft light, shallow depth of field, rich detail, "
                 "35mm lens. " + NO_TEXT),
        "refs": [],
    },
}
CUSTOM = "custom"


def resolve(choice: dict | None) -> dict:
    """{"preset", "label", "text", "refs": [absolute paths]} for a project's meta.json style choice."""
    choice = choice or {}
    preset = choice.get("preset") if choice.get("preset") in PRESETS or choice.get("preset") == CUSTOM else None
    if preset == CUSTOM and str(choice.get("text", "")).strip():
        return {"preset": CUSTOM, "label": "Tự viết", "text": choice["text"].strip(), "refs": []}
    if preset in PRESETS:
        p = PRESETS[preset]
        return {"preset": preset, "label": p["label"], "text": p["text"], "refs": [ROOT / r for r in p["refs"]]}
    return {}


def sample_path(preset: str, project: Path | None = None) -> Path:
    if preset == CUSTOM and project is not None:
        return project / "muse" / "styles" / "custom.png"
    return SAMPLE_DIR / f"{preset}.png"


def existing_sample(preset: str, project: Path | None = None) -> Path | None:
    base = sample_path(preset, project)
    found = sorted(base.parent.glob(base.stem + ".*")) if base.parent.is_dir() else []
    return found[0] if found else None


def make_sample(preset: str, project: Path | None, ratio: str) -> Path:
    from .visuals import _generate
    style = resolve({"preset": preset, "text": _custom_text(project)} if preset == CUSTOM else {"preset": preset})
    if not style:
        raise RuntimeError("Write the custom style first")
    old = existing_sample(preset, project)
    if old:
        old.unlink()
    print(f"[style] {style['label']}")
    return _generate("image", f"{SAMPLE_SUBJECT}\n\nVisual style: {style['text']}", ratio,
                     sample_path(preset, project), style["refs"])


def _custom_text(project: Path | None) -> str:
    if project is None:
        return ""
    meta = json.loads((project / "meta.json").read_text(encoding="utf-8")) if (project / "meta.json").exists() else {}
    return (meta.get("style") or {}).get("text", "")


def main() -> None:
    from .cli import load_env
    load_env(ROOT / ".env")
    sys.stdout.reconfigure(line_buffering=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["sample"])
    ap.add_argument("--preset", choices=[*PRESETS, CUSTOM], help="one style (default: every preset without a sample)")
    ap.add_argument("--project", help="project folder, needed for the custom style")
    ap.add_argument("--ratio", choices=["16:9", "9:16"], default="9:16")
    ap.add_argument("--redo", action="store_true", help="make the sample again even if one exists")
    args = ap.parse_args()
    project = Path(args.project).resolve() if args.project else None
    presets = [p for p in ([args.preset] if args.preset else list(PRESETS))
               if args.redo or not existing_sample(p, project)]
    failed = []

    def one(preset: str) -> None:
        try:
            print(f"  -> {make_sample(preset, project, args.ratio).name}")
        except RuntimeError as e:
            failed.append(preset)
            print(f"  {preset} failed: {e}")

    # one sample per signed-in Muse account at a time
    from concurrent.futures import ThreadPoolExecutor
    from .visuals import ready_accounts
    with ThreadPoolExecutor(max_workers=max(1, min(ready_accounts(), len(presets) or 1))) as pool:
        list(pool.map(one, presets))
    if failed:
        raise SystemExit(f"{len(failed)} sample(s) failed: {', '.join(failed)}")
    print("Done")


if __name__ == "__main__":
    main()
