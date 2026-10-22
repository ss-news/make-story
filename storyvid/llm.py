"""LLM backends that return the script as JSON text.

- openai: any OpenAI-compatible /chat/completions endpoint (OpenAI, DeepSeek, Gemini, OpenRouter...)
- codex:  the Codex CLI (`codex exec`), billed to your ChatGPT plan, no API key needed
"""
import json
import os
import re
import subprocess
import urllib.error
import urllib.request


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} is not set (see .env.example)")
    return value


def extract_json(text: str) -> dict:
    """Take the first {...} block, tolerating ```json fences or chatter around it."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError(f"LLM did not return JSON:\n{text[:500]}")
    return json.loads(text[start:end + 1])


def openai_compatible(system: str, user: str, schema: dict) -> dict:
    base = _env("LLM_BASE_URL").rstrip("/")
    body = {
        "model": _env("LLM_MODEL"),
        "messages": [
            {"role": "system", "content": system + "\n\nReply with only a JSON object matching this schema:\n"
                                             + json.dumps(schema)},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {_env('LLM_API_KEY')}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"LLM API error {e.code}: {e.read().decode(errors='replace')[:500]}") from None
    choice = data["choices"][0]
    if choice.get("finish_reason") == "length":
        raise RuntimeError("Script was cut off by the model's output limit; lower --minutes")
    return extract_json(choice["message"]["content"])


def codex(system: str, user: str, schema: dict) -> dict:
    prompt = (f"{system}\n\nReply with only a JSON object matching this schema, no other text:\n"
              f"{json.dumps(schema)}\n\nSTORY:\n{user}")
    cmd = [os.environ.get("CODEX_BIN", "codex"), "exec", "--skip-git-repo-check", prompt]
    if os.environ.get("CODEX_MODEL"):
        cmd[2:2] = ["-m", os.environ["CODEX_MODEL"]]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        raise RuntimeError(f"codex exec failed:\n{result.stderr[-1500:]}")
    # codex prints the final answer last; search from the end for the JSON object
    out = result.stdout
    for m in reversed(list(re.finditer(r"^\{", out, flags=re.M))):
        try:
            return extract_json(out[m.start():])
        except (json.JSONDecodeError, RuntimeError):
            continue
    return extract_json(out)
