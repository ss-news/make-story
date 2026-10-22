# Modular Vietnamese Characters Implementation Plan

> Execute inline using executing-plans; user authorized implementation in this chat.

**Goal:** Eight editable modular characters with a persistent variant per video.
**Architecture:** SVG parts and JSON rig manifests feed cached SVG-to-PNG composition. Script owns video variant; channel supplies defaults. Web editor uses the same resolver and preview.
**Tech Stack:** Python, Pillow, resvg-py, Flask, vanilla JavaScript.

- [x] Add behavior tests in `tests/test_characters.py`: persistence, invalid choices, per-video independence, full pose matrix, layer exports and API validation. Run `.venv/bin/python -m unittest discover -s tests -v` and confirm missing-feature failures.
- [x] Implement `storyvid/character_catalog.py` with presets and validated variant resolution. Preserve `character` in `storyvid/script.py`; apply it in `storyvid/render.py`.
- [x] Create editable SVG parts and rig manifests under `assets/characters` using `tools/build_character_assets.py`. Replace `storyvid/character.py` with rig compositor, retaining Character.sprite interface.
- [x] Extend options/preview API in `storyvid/web/__main__.py`; add selectors and saved preview in `storyvid/web/static/index.html` and `app.js`. Validate before saving settings or projects.
- [x] Export gallery and exploded parts with `tools/preview_characters.py`. Inspect PNGs, render a short offline video, exercise browser selection/save/reload, run unittest and syntax checks.
- [x] Update README with SVG replacement contract, per-video fields, dependency and verification commands. Record actual results; no Git repository exists.

## Verification record
- 13 unittest cases passed, including actual ffmpeg render, script regeneration and Flask project persistence.
- JS syntax and Python compilation passed.
- Eight independent motion clips rendered and concatenated; full ffmpeg decode passed. Gallery, parts sheet and a video frame visually inspected.
- Browser UI automation blocked: the Codex in-app webview repeatedly failed to attach, and Chrome provider is unavailable. API and static syntax verified; direct click/save/reload browser verification remains unverified.
- Preview server started at http://127.0.0.1:8766 because an existing server owns 8765. No existing project MP4 was overwritten. Repository has no Git metadata; no commit or push.
