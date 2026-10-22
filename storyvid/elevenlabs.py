"""ElevenLabs TTS: voice list, synthesis with character timings, and an on-disk cache.

Every synthesized line is cached by (model, voice, speed, text), so re-rendering a video
spends no credits. The free plan has ~10k characters a month and no commercial licence.
"""
import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.elevenlabs.io/v1"
CACHE_DIR = Path(__file__).resolve().parents[1] / "cache" / "tts"
DEFAULT_MODEL = "eleven_multilingual_v2"
# eleven_multilingual_v2 has no Vietnamese; the v2.5 models do
LANG_MODEL = {"vi": "eleven_flash_v2_5"}
# ElevenLabs age labels -> character_catalog ages
AGE_LABELS = {"child": ("young",), "young": ("young",), "middle": ("middle_aged", "middle aged"),
              "elder": ("old",)}


def api_key() -> str:
    key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set (see .env.example)")
    return key


def model_for(lang: str) -> str:
    return os.environ.get("ELEVENLABS_MODEL", "").strip() or LANG_MODEL.get(lang, DEFAULT_MODEL)


def _request(path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"xi-api-key": api_key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:400]
        if e.code == 401:
            raise RuntimeError(f"ElevenLabs rejected the API key (401): {detail}") from None
        if e.code in (402, 429) or "quota" in detail:
            raise RuntimeError(f"ElevenLabs quota or rate limit reached ({e.code}): {detail}") from None
        raise RuntimeError(f"ElevenLabs API error {e.code}: {detail}") from None


# ElevenLabs' default voices, used when the key lacks the voices_read permission
DEFAULT_VOICES = [
    ("nPczCjzI2devNBz1zQrb", "Brian", "male", "middle_aged"),
    ("JBFqnCBsd6RMkjVDRZzb", "George", "male", "middle_aged"),
    ("TX3LPaxmHKxFdv7VOQHJ", "Liam", "male", "young"),
    ("bIHbv24MWmeRgasZH58o", "Will", "male", "young"),
    ("onwK4e9ZLuTAKqWW03F9", "Daniel", "male", "middle_aged"),
    ("Xb7hH8MSUJpSbSDYk0k2", "Alice", "female", "middle_aged"),
    ("XrExE9yKIg1WjnnlVkGX", "Matilda", "female", "middle_aged"),
    ("EXAVITQu4vr4xnSDxMaL", "Sarah", "female", "young"),
    ("cgSgspJ2msm6clMCkdW9", "Jessica", "female", "young"),
    ("FGY2WhTYpPnrIDTdsKH5", "Laura", "female", "young"),
    ("pFZP5JQG7iQjIQuC4Bku", "Lily", "female", "middle_aged"),
]


def list_voices() -> list[dict]:
    """[{id, name, gender, age}] for every voice the account can use."""
    try:
        listed = _request("/voices").get("voices", [])
    except RuntimeError as e:
        if "voices_read" not in str(e):
            raise
        print("  ElevenLabs key cannot list voices (voices_read): using the default voices")
        return [{"id": i, "name": n, "gender": g, "age": a} for i, n, g, a in DEFAULT_VOICES]
    voices = []
    for v in listed:
        labels = v.get("labels") or {}
        voices.append({"id": v["voice_id"], "name": v.get("name", ""),
                       "gender": (labels.get("gender") or "").lower(),
                       "age": (labels.get("age") or "").lower().replace("-", "_")})
    if not voices:
        raise RuntimeError("ElevenLabs returned no voices for this account")
    return voices


def pick_voice(voices: list[dict], gender: str, age: str, taken: set) -> str:
    """Best unused voice for gender/age; falls back to reusing one rather than failing."""
    want_age = AGE_LABELS.get(age, ())
    ranked = sorted(voices, key=lambda v: (v["id"] in taken, v["gender"] != gender, v["age"] not in want_age))
    choice = ranked[0]["id"]
    taken.add(choice)
    return choice


def resolve_narrator(voices: list[dict], taken: set) -> str:
    wanted = os.environ.get("ELEVENLABS_NARRATOR_VOICE", "").strip()
    if wanted:
        for v in voices:
            if wanted in (v["id"], v["name"]):
                taken.add(v["id"])
                return v["id"]
        taken.add(wanted)
        return wanted  # an id the voice list does not show (e.g. a shared library voice)
    return pick_voice(voices, "male", "middle", taken)


def speed_from_rate(rate: str) -> float:
    """edge-tts style '+8%' -> ElevenLabs speed, clamped to its 0.7–1.2 range."""
    return round(min(1.2, max(0.7, 1 + int(rate.rstrip("%")) / 100)), 2)


def _words(alignment: dict) -> list:
    """Group character timings into (start, end, word) tuples."""
    words, chars, start, end = [], [], 0.0, 0.0
    for ch, s, e in zip(alignment["characters"], alignment["character_start_times_seconds"],
                        alignment["character_end_times_seconds"]):
        if ch.isspace():
            if chars:
                words.append((start, end, "".join(chars)))
                chars = []
            continue
        if not chars:
            start = s
        chars.append(ch)
        end = e
    if chars:
        words.append((start, end, "".join(chars)))
    return words


def synthesize(text: str, voice_id: str, mp3_path: Path, speed: float, model: str) -> list:
    """Write the line to mp3_path and return word timings, using the cache when possible."""
    digest = hashlib.sha256(json.dumps([model, voice_id, speed, text]).encode()).hexdigest()[:24]
    cached_mp3, cached_json = CACHE_DIR / f"{digest}.mp3", CACHE_DIR / f"{digest}.json"
    if not (cached_mp3.exists() and cached_json.exists()):
        data = _request(f"/text-to-speech/{voice_id}/with-timestamps?output_format=mp3_44100_128", {
            "text": text, "model_id": model,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "speed": speed},
        })
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cached_mp3.write_bytes(base64.b64decode(data["audio_base64"]))
        cached_json.write_text(json.dumps(_words(data["alignment"])))
        print(f"    elevenlabs: {len(text)} characters")
    mp3_path.write_bytes(cached_mp3.read_bytes())
    return [tuple(w) for w in json.loads(cached_json.read_text())]
