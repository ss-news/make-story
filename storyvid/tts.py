"""Step 2: narrate each scene (edge-tts or ElevenLabs) and build subtitle cues from word timings."""
import os
import subprocess
import wave
from pathlib import Path

import edge_tts
import numpy as np

from . import elevenlabs
from .ffmpeg import ffmpeg_exe

SAMPLE_RATE = 24000
SCENE_PAD = 0.35  # seconds of silence after each scene
LINE_PAD = 0.2    # pause between two lines inside a scene
MAX_WORDS_PER_CUE = 8

# Character voices per language, by gender. Narration keeps the channel voice.
VOICE_POOL = {
    "en": {"male": ["en-US-GuyNeural", "en-US-ChristopherNeural", "en-US-RogerNeural", "en-US-EricNeural"],
           "female": ["en-US-AvaNeural", "en-US-JennyNeural", "en-US-MichelleNeural", "en-US-EmmaNeural"],
           "child": ["en-US-AnaNeural"]},
    "vi": {"male": ["vi-VN-NamMinhNeural"], "female": ["vi-VN-HoaiMyNeural"]},
    "de": {"male": ["de-DE-KillianNeural", "de-DE-FlorianMultilingualNeural"],
           "female": ["de-DE-KatjaNeural", "de-DE-AmalaNeural", "de-DE-SeraphinaMultilingualNeural"]},
    "fr": {"male": ["fr-FR-RemyMultilingualNeural", "fr-FR-HenriNeural"],
           "female": ["fr-FR-DeniseNeural", "fr-FR-VivienneMultilingualNeural"], "child": ["fr-FR-EloiseNeural"]},
    "es": {"male": ["es-ES-AlvaroNeural"], "female": ["es-ES-ElviraNeural", "es-ES-XimenaNeural"]},
}
# (rate %, pitch Hz) by age, so characters sharing a base voice still sound different
AGE_TONE = {"child": (8, 28), "young": (0, 0), "middle": (-4, -6), "elder": (-12, -14)}
GHOST_TONE = (-16, -22)


def tts_provider() -> str:
    """edge (free, unofficial) or elevenlabs, from TTS_PROVIDER in .env."""
    provider = os.environ.get("TTS_PROVIDER", "").strip() or "edge"
    if provider not in ("edge", "elevenlabs"):
        raise RuntimeError(f"Unknown TTS_PROVIDER '{provider}': use edge or elevenlabs")
    return provider


def cast_voices_elevenlabs(script: dict) -> dict:
    """Same shape as cast_voices, with ElevenLabs voice ids. ElevenLabs has no pitch control,
    so every character gets its own voice and age only changes the speed."""
    from .character_catalog import PRESETS
    voices_available = elevenlabs.list_voices()
    taken: set = set()
    voices = {"narrator": (elevenlabs.resolve_narrator(voices_available, taken), "+0%", "+0Hz")}
    for c in script.get("cast", []):
        info = PRESETS.get(c.get("preset"), {})
        gender = "female" if info.get("female") else "male"
        voice_id = elevenlabs.pick_voice(voices_available, gender, info.get("age", "young"), taken)
        rate, _ = GHOST_TONE if c.get("kind") == "ghost" else AGE_TONE.get(info.get("age"), (0, 0))
        voices[c["id"]] = (voice_id, f"{rate:+d}%", "+0Hz")
    return voices


def cast_voices(script: dict, narrator_voice: str, lang: str) -> dict:
    """{speaker id: (voice, rate, pitch)} for the narrator and every cast member."""
    from .character_catalog import PRESETS
    pool = VOICE_POOL.get(lang, {})
    used: dict[str, int] = {}
    voices = {"narrator": (narrator_voice, "+0%", "+0Hz")}
    for c in script.get("cast", []):
        info = PRESETS.get(c.get("preset"), {})
        group = "child" if info.get("age") == "child" and pool.get("child") else (
            "female" if info.get("female") else "male")
        options = pool.get(group) or [narrator_voice]
        n = used.get(group, 0)
        used[group] = n + 1
        rate, pitch = GHOST_TONE if c.get("kind") == "ghost" else AGE_TONE.get(info.get("age"), (0, 0))
        pitch += (n // len(options)) * 6 * (-1) ** n  # reused base voice: nudge pitch so it differs
        voices[c["id"]] = (options[n % len(options)], f"{rate:+d}%", f"{pitch:+d}Hz")
    return voices


def _synthesize(text: str, voice: str, mp3_path: Path, rate: str = "+0%", pitch: str = "+0Hz") -> list:
    words = []
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    with open(mp3_path, "wb") as f:
        for chunk in communicate.stream_sync():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offsets are in 100-nanosecond units
                start = chunk["offset"] / 1e7
                words.append((start, start + chunk["duration"] / 1e7, chunk["text"]))
    return words


def _decode(mp3_path: Path) -> np.ndarray:
    raw = subprocess.run(
        [ffmpeg_exe(), "-v", "error", "-i", str(mp3_path), "-f", "s16le", "-ac", "1", "-ar", str(SAMPLE_RATE), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.int16)


def _norm(s: str) -> str:
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _restore_punctuation(words: list, narration: str) -> list:
    """edge-tts drops punctuation from word timings; put the original spelling back."""
    tokens, out, j = narration.split(), [], 0
    for start, end, text in words:
        key = _norm(text)
        k = j
        while k < len(tokens) and key and key not in _norm(tokens[k]):
            k += 1
        if k < len(tokens) and key:
            # a token can hold several spoken words (e.g. "twenty-one"): print it once, on its last word
            nxt = words[len(out) + 1][2] if len(out) + 1 < len(words) else ""
            same_token = _norm(nxt) and _norm(nxt) in _norm(tokens[k]) and _norm(tokens[k]) != key
            out.append((start, end, "" if same_token else tokens[k]))
            j = k if same_token else k + 1
        else:
            out.append((start, end, text))
    return out


def _cues(words: list, offset: float) -> list[dict]:
    """Group word timings into short subtitle lines, breaking at punctuation."""
    cues, current = [], []
    for w in words:
        current.append(w)
        if len(current) >= MAX_WORDS_PER_CUE or w[2].endswith((".", "!", "?", ",", "…", ":", ";")):
            cues.append(current)
            current = []
    if current:
        cues.append(current)
    return [
        {"start": offset + c[0][0], "end": offset + c[-1][1], "text": " ".join(w[2] for w in c if w[2])}
        for c in cues
    ]


def narrate(script: dict, voice: str, work_dir: Path, lang: str = "") -> dict:
    """Voice every line of every scene.

    Returns {"audio", "samples", "duration", "scenes": [{start, end, lines: [{start, end, speaker}]}], "cues": [...]}
    """
    provider = tts_provider()
    if provider == "elevenlabs":
        voices = cast_voices_elevenlabs(script)
        model = elevenlabs.model_for(lang)
        synthesize = lambda text, v, mp3, rate, pitch: elevenlabs.synthesize(  # noqa: E731
            text, v, mp3, elevenlabs.speed_from_rate(rate), model)
    else:
        voices = cast_voices(script, voice, lang)
        synthesize = _synthesize
    names = {c["id"]: c["name"] for c in script.get("cast", [])}
    audio_dir = work_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)
    silence = lambda sec: np.zeros(int(sec * SAMPLE_RATE), dtype=np.int16)  # noqa: E731
    pieces, timeline, cues, t = [], [], [], 0.0
    for i, scene in enumerate(script["scenes"]):
        scene_start, spans = t, []
        for j, line in enumerate(scene["lines"]):
            speaker = line["speaker"] if line["speaker"] in voices else "narrator"
            v, rate, pitch = voices[speaker]
            mp3 = audio_dir / f"scene_{i:02d}_{j:02d}.mp3"
            words = _restore_punctuation(synthesize(line["text"], v, mp3, rate, pitch), line["text"])
            samples = _decode(mp3)
            length = len(samples) / SAMPLE_RATE
            new = _cues(words, t) if words else [{"start": t, "end": t + length, "text": line["text"]}]
            for c in new:
                c["speaker"] = names.get(speaker, "")
            cues += new
            spans.append({"start": t, "end": t + length, "speaker": speaker})
            pieces.append(samples)
            t += length
            if j < len(scene["lines"]) - 1:
                pieces.append(silence(LINE_PAD))
                t += LINE_PAD
        pieces.append(silence(SCENE_PAD))
        t += SCENE_PAD
        timeline.append({"start": scene_start, "end": t, "lines": spans})
        print(f"  voice {i + 1}/{len(script['scenes'])}: {t - scene_start:.1f}s, {len(spans)} line(s)")

    audio = np.concatenate(pieces)
    wav_path = work_dir / "narration.wav"
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(audio.tobytes())
    return {"audio": wav_path, "samples": audio, "duration": t, "scenes": timeline, "cues": cues}
