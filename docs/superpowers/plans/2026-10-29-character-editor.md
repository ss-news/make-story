# Character Editor Implementation Plan

> Execute inline in this session. User requires main; no worktree or subagents.

**Goal:** Let the user approve and save a 2D character layout for later AI refinement in Blender.

**Architecture:** Dependency-free browser Canvas editor with a localhost Python server and bounded JSON contract. Source PNGs remain in the existing human-action-trial-v1 pack. A separate Blender importer builds an editable layout reference.

**Tech Stack:** HTML/CSS/ES modules, Python stdlib, Blender Python.

- [x] Define persistence/security tests in assets/bac-bo-stick/extra/character-editor/tests/test_server.py. Run unittest and confirm failure before implementation.
- [x] Implement model.js (defaults, validation, transforms), app.js (interaction/history/files), index.html/style.css (Vietnamese responsive interface), serve.py (static allowlist and named saves).
- [x] Implement import_blender.py consuming the same absolute pivot/top-left coordinate convention; pack images and preserve layer order, visibility and head choice.
- [x] Exercise real browser interactions and disk saves; inspect desktop/mobile screenshots. Validate Blender corner coordinates from saved JSON. Run .venv/bin/python -m unittest discover -s tests and .venv/bin/python -m storyvid.check --assets.
- [x] Document launch/recovery/import commands, open the working local web, and commit only this editor and its design/plan files on main.

Validation completed: 4 editor Python tests, JS model roundtrip/pivot tests, real Chrome desktop/mobile interaction suite (including resize/rotation), Blender reopen check (17 parts, max corner error 0.0000611 px), 46 project unit tests, asset checker OK (134 assets / 22 extra characters). Local server on 127.0.0.1:8766.
