"""VieNeu-TTS (https://github.com/pnnbao97/VieNeu-TTS): Vietnamese voices that run on this machine's CPU.

pip install vieneu. The model (~0.5 GB) downloads on first use into cache/vieneu/. Every synthesized line is
cached by (voice, text), so re-rendering a video does not synthesize again. VieNeu gives no word timings, so
subtitle timings are estimated by spreading each line's length over its words.
"""
import hashlib
import json
import os
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "cache" / "vieneu"
CACHE_DIR = ROOT / "cache" / "vieneu" / "lines"
DEFAULT_NARRATOR = "Thiện Minh"  # northern male, storytelling style
# character voices by gender, used in order and never the narrator's
POOL = {"male": ["Thanh Bình", "Phạm Tuyên", "Quốc Tuấn", "Minh Đức", "Xuân Vĩnh", "Hải Đăng"],
        "female": ["Ngọc Linh", "Quỳnh Anh", "Đoan Trang", "Ngọc Huyền", "Trúc Ly"]}

_engine = None


def engine():
    """Load the model once. Its files go to real folders under cache/vieneu: recent onnxruntime refuses ONNX
    external data reached through the symlinks of the shared Hugging Face cache."""
    global _engine
    if _engine is None:
        import huggingface_hub

        def into(fn):
            def call(repo_id, *a, **kw):
                kw.pop("cache_dir", None)
                kw["local_dir"] = str(MODEL_DIR / repo_id.replace("/", "__"))
                return fn(repo_id, *a, **kw)
            return call

        huggingface_hub.hf_hub_download = into(huggingface_hub.hf_hub_download)
        huggingface_hub.snapshot_download = into(huggingface_hub.snapshot_download)
        try:
            from vieneu import Vieneu
        except ImportError:
            raise RuntimeError("VieNeu-TTS is not installed: .venv/bin/pip install vieneu") from None
        print("  loading VieNeu-TTS (first run downloads the model)...")
        _engine = Vieneu()
    return _engine


def narrator_voice() -> str:
    return os.environ.get("VIENEU_NARRATOR_VOICE", "").strip() or DEFAULT_NARRATOR


def cast_voices(script: dict) -> dict:
    """{speaker id: voice name}; narrator first, then one distinct voice per cast member by gender."""
    from .character_catalog import PRESETS
    voices = {"narrator": narrator_voice()}
    used = {voices["narrator"]}
    for c in script.get("cast", []):
        gender = "female" if PRESETS.get(c.get("preset"), {}).get("female") else "male"
        pool = [v for v in POOL[gender] if v not in used] or POOL[gender]
        voices[c["id"]] = pool[0]
        used.add(pool[0])
    return voices


def word_timings(text: str, seconds: float) -> list[tuple[float, float, str]]:
    """Spread a line's duration over its words, weighted by length (VieNeu has no timestamps)."""
    words = text.split()
    if not words:
        return []
    weights = np.array([len(w) + 1 for w in words], dtype=float)
    edges = np.concatenate([[0.0], np.cumsum(weights / weights.sum() * seconds)])
    return [(float(edges[i]), float(edges[i + 1]), w) for i, w in enumerate(words)]


def synthesize(text: str, voice: str, out_path: Path) -> list:
    """Write the line as a WAV file to out_path and return estimated word timings."""
    digest = hashlib.sha256(json.dumps(["v3turbo", voice, text]).encode()).hexdigest()[:24]
    cached = CACHE_DIR / f"{digest}.wav"
    if not cached.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        tts = engine()
        audio = np.asarray(tts.infer(text, voice=voice), dtype=np.float32)
        part = cached.with_suffix(".part")
        with wave.open(str(part), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(tts.sample_rate)
            w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
        part.replace(cached)
    out_path.write_bytes(cached.read_bytes())
    with wave.open(str(cached), "rb") as w:
        seconds = w.getnframes() / w.getframerate()
    return word_timings(text, seconds)
