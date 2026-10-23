"""Music, ambience and sound effects mixed under the narration.

Sounds live in assets/audio/ and are listed in assets/audio/manifest.json with their source and licence,
so every file in a video can be traced back if YouTube's Content ID ever claims it. A script refers to
them by id (see contract.py): a "music" bed for the whole video, an "ambience" loop per scene and "sfx"
one-shots at the start of a line. The voice stays in front: the music ducks while someone speaks.
"""
import json
import subprocess
import wave
from functools import lru_cache
from pathlib import Path

import numpy as np

from .ffmpeg import ffmpeg_exe
from .tts import SAMPLE_RATE

AUDIO = Path(__file__).resolve().parents[1] / "assets" / "audio"
KINDS = ("sfx", "ambience", "music")
LICENSES = ("CC0", "CC-BY-4.0", "YouTube Audio Library", "Mixkit Free License")
TARGET_RMS = 0.1    # every sound is levelled to this average loudness (-20 dBFS) before its gain
# Gains relative to that level; the narration sits around -24 dBFS, so music stays ~10 dB under the voice
DEFAULT_GAIN_DB = {"sfx": -4.0, "ambience": -10.0, "music": -8.0}
DUCK_DB = -6.0      # extra music cut while the voice is speaking
FADE = 0.6          # seconds of fade at the edges of an ambience loop or the music bed


@lru_cache(maxsize=1)
def manifest() -> dict:
    path = AUDIO / "manifest.json"
    if not path.exists():
        return {"sounds": []}
    return json.loads(path.read_text())


def reload() -> None:
    manifest.cache_clear()
    _decoded.cache_clear()


def sounds(kind: str | None = None) -> list[dict]:
    return [s for s in manifest()["sounds"] if kind is None or s.get("kind") == kind]


def ids(kind: str | None = None) -> list[str]:
    return [s["id"] for s in sounds(kind)]


def entry(sound_id: str) -> dict:
    item = next((s for s in sounds() if s["id"] == sound_id), None)
    if item is None:
        raise KeyError(f"Unknown sound '{sound_id}'")
    return item


def attributions(script: dict) -> list[str]:
    """Credit lines a video using these sounds must carry in its description."""
    used = [script.get("music", {}).get("id")] if script.get("music") else []
    for s in script["scenes"]:
        used.append(s.get("ambience"))
        used += [x["id"] for x in s.get("sfx", [])]
    lines = []
    for sound_id in dict.fromkeys(u for u in used if u):
        credit = entry(sound_id).get("attribution")
        if credit and credit not in lines:
            lines.append(credit)
    return lines


@lru_cache(maxsize=64)
def _decoded(sound_id: str) -> np.ndarray:
    """Mono float32 samples at the narration sample rate, levelled to TARGET_RMS (music has a wide dynamic
    range, so levelling by peak would leave most of a track far too quiet)."""
    path = AUDIO / entry(sound_id)["file"]
    raw = subprocess.run(
        [ffmpeg_exe(), "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"],
        check=True, capture_output=True,
    ).stdout
    data = np.frombuffer(raw, dtype=np.float32).copy()
    rms = float(np.sqrt(np.mean(data ** 2))) if len(data) else 0.0
    return data * (TARGET_RMS / rms) if rms > 0 else data


def _gain(sound_id: str) -> float:
    item = entry(sound_id)
    return 10 ** (item.get("gain_db", DEFAULT_GAIN_DB[item["kind"]]) / 20)


def _loop(data: np.ndarray, length: int) -> np.ndarray:
    if not len(data):
        return np.zeros(length, dtype=np.float32)
    reps = int(np.ceil(length / len(data)))
    return np.tile(data, reps)[:length]


def _fade(data: np.ndarray, seconds: float = FADE) -> np.ndarray:
    n = min(int(seconds * SAMPLE_RATE), len(data) // 2)
    if n:
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        data[:n] *= ramp
        data[-n:] *= ramp[::-1]
    return data


def _voice_envelope(voice: np.ndarray) -> np.ndarray:
    """0..1 per sample: how much someone is speaking, smoothed so the music moves slowly."""
    hop = SAMPLE_RATE // 20
    frames = len(voice) // hop + 1
    padded = np.pad(np.abs(voice), (0, frames * hop - len(voice)))
    level = padded.reshape(frames, hop).mean(axis=1)
    speaking = (level > 0.02).astype(np.float32)
    kernel = np.ones(12, dtype=np.float32) / 12  # ~0.6 s of smoothing
    smooth = np.clip(np.convolve(speaking, kernel, mode="same") * 1.5, 0, 1)
    return np.repeat(smooth, hop)[:len(voice)]


def has_sound(script: dict) -> bool:
    return bool(script.get("music")) or any(s.get("ambience") or s.get("sfx") for s in script["scenes"])


def mix(script: dict, timeline: dict, out_path: Path) -> Path:
    """Write voice + music + ambience + sfx to out_path (16-bit mono WAV) and return it."""
    voice = timeline["samples"].astype(np.float32) / 32768.0
    total = len(voice)
    bed = np.zeros(total, dtype=np.float32)
    for scene, span in zip(script["scenes"], timeline["scenes"]):
        start, end = int(span["start"] * SAMPLE_RATE), min(total, int(span["end"] * SAMPLE_RATE))
        if scene.get("ambience") and end > start:
            bed[start:end] += _fade(_loop(_decoded(scene["ambience"]), end - start)) * _gain(scene["ambience"])
        for cue in scene.get("sfx", []):
            line = span["lines"][min(cue["line"], len(span["lines"]) - 1)] if span["lines"] else span
            at = int(line["start"] * SAMPLE_RATE)
            clip = _decoded(cue["id"])[: max(0, total - at)] * _gain(cue["id"])
            bed[at:at + len(clip)] += clip
    if script.get("music"):
        music_id = script["music"]["id"]
        duck = 10 ** (DUCK_DB / 20)
        music = _fade(_loop(_decoded(music_id), total), FADE * 3) * _gain(music_id)
        bed += music * (1 - (1 - duck) * _voice_envelope(voice))
    out = voice + bed
    peak = float(np.abs(out).max())
    if peak > 0.98:
        out *= 0.98 / peak
    with wave.open(str(out_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes((out * 32767).astype(np.int16).tobytes())
    return out_path
