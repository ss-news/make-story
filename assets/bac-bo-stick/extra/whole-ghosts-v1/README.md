# Whole-ghost asset standard v1

Approved direction for the four Stung Treng ghosts: **whole-character pose images**, not sliced limb rigs. Each drawing keeps the approved white-faced stick-cartoon style. The set contains four poses for each of four ghosts, a clean painted Cambodian courtyard, source references and reproducible normalization/Blender scripts.

This is a **Blender source-pack standard**, independent of `storyvid.scenes/1`. It does not silently change Storyvid's existing SVG character contract or make new pose enums valid in scenes.json. Existing human/NPC rigs remain available. No story narration or review.json is modified.

## Files and conventions

- `characters/<id>/<pose>.png`: normalized **1024×1536 RGBA**, with transparent margins. All images share anchor **[512,1390]** at the visible lower edge. The image remains intact; only transparent borders/noise are trimmed and uniform scaling is applied.
- `source/<id>/<pose>.png`: original generated image, retained for rebuilding.
- `manifest.json`: character identity, default pose, relative filenames, anchor, bounding boxes, world-scale guidance and SHA-256 hashes.
- `manifest.schema.json`: documented source-pack structure. It is not a replacement for the Storyvid scene schema.
- `generation.json`: exact prompts, references and generation provenance. Built-in ImageGen was used; no rembg installation is required.
- `backgrounds/camp_yard_night.png`: clean background based on the approved cinematic painting, with the original fused character removed.
- `references/`: approved character references.

| Character | Poses |
|---|---|
| `legless_ghost_woman` | `float_neutral`, `plead`, `bow`, `raise_head` |
| `kneeling_ghost_woman` | `kneel`, `deep_bow`, `crawl`, `look_up` |
| `ghost_boy` | `stand`, `hold_hand`, `turn`, `lower_head` |
| `fanged_ghost_child` | `stand`, `lean`, `look_up`, `reach` |

The lead woman has no legs or feet in any pose. No skeletal remains, injuries, blood or corpses are depicted. The kneeling woman and the children retain their appropriate complete silhouettes. The identities and clothing are reference-conditioned; small drawn differences between poses remain and are visible in the contact sheet.

## Rebuild

From the repository root:

```sh
.venv/bin/python assets/bac-bo-stick/extra/whole-ghosts-v1/normalize.py
.venv/bin/python assets/bac-bo-stick/extra/whole-ghosts-v1/validate.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python assets/bac-bo-stick/extra/whole-ghosts-v1/build_blender.py -- \
  --out output/stung_treng/blender --render
.venv/bin/python assets/bac-bo-stick/extra/whole-ghosts-v1/encode_preview.py
```

Normalization needs Pillow/NumPy. Validation uses jsonschema when available, otherwise checks the documented fields and source invariants directly. Rebuilding consumes existing images and makes no further image-generation or voice requests.

## Blender delivery

`build_blender.py` creates a new scene in a **separate factory-startup process**, preserving any scene open in the desktop application. The result is `output/stung_treng/blender/stung-treng-whole-ghosts.blend` with all 17 images packed.

Collections separate background, ghosts, smoke and camera. Each character has a parent controller; the four whole-pose drawings have independent, animated material-opacity tracks. Timeline markers identify every pose. The 24-second showcase uses calm hovering, slight swaying, brief pose dissolves and procedural ground mist. A very mild optional mesh shape key affects outer lower silhouette regions while keeping the face centered. It is a **2.5D image-plane scene**, not a 3D modeled/armature-rigged character.

The .blend opens on the lead woman and retains the full timeline for editing. Preview renders are 960×540 at 12 fps; they are review copies, not the final 1080p video for publication. The MP4/GIF have no narration or soundtrack.

## Integration/review boundary

These full-pose PNGs are registered in their own manifest, **not disguised as Storyvid props or SVG rigs**. `storyvid/`, existing scenes.json, and review.json remain unchanged. A separate, explicitly authorized integration change is required for Storyvid to select whole PNG poses or consume Blender clips. Do not put `plead`, `bow`, etc. into the current `scenes/1` actor pose enum.

Checklist sections 1–7: assets and saved-scene integrity can be checked here. Final story pacing, 1080p long/Short layout, narration, subtitle timing and audio balance still require the final production/review pass. Sections 8–9 remain the user's publication and 48-hour analytics checks.
