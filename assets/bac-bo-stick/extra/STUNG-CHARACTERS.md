# Stung Treng stick-character source pack

Approved direction: detailed painted environments with simple white-faced, black-outline stick characters. These are newly authored editable SVG interpretations of the approved model sheets, not raster crops or pixel-identical tracings.

## Contents

- 13 story-character rigs and 8 distinct NPC rigs. The existing base characters and `small_boy` are unchanged.
- Each rig has separate head, front/back hair, neck, torso, upper arm, forearm, hand, thigh, shin, foot, bag, scarf and flashlight SVGs. Shared limb definitions are instanced separately for left/right by the renderer. All original joint anchors, part names and limb lengths are retained.
- Each character has 22 sets of eyes, eyebrows and mouth, plus closed and half-closed eyes, half/open speaking mouths and five source phonemes (A/E/O/M/F).
- 12 independent effect SVGs: blush cheeks, embarrassment hatching, teardrop, tear streams, sweat drop, sparkle, anger, shaded eyes, shock lines, trembling, heart, laughing tears.
- NPCs differ in head shape, eye spacing, nose detail, hair, age and clothing. Neutral NPC faces alternate between sparse, shaded and ordinary eyes. All have the additional blank/shadowed expression sources.
- `assembled.svg` is an editable layered assembly; the individual SVGs and `rig.json` are the source of truth. `face-library.json` indexes facial parts.

## Runtime versus source-only states

The unchanged renderer supports exactly `neutral`, `happy`, `scared`, `surprised`, `sad`, `angry`, `smirk`, with automatic blinking and three speaking-mouth states.

The 15 additional source expressions are `worried`, `terrified`, `crying`, `pleading`, `suspicious`, `exhausted`, `determined`, `embarrassed`, `blushing`, `shy_happy`, `sad_blush`, `relieved`, `laughing`, `blank`, `shadowed`. Their full-body SVG/transparent PNG previews are exported separately. **Do not put these values in `scenes.json`: the current contract rejects them.** The extra effects are registered source assets, but the current renderer does not provide arbitrary effect overlays. Phoneme selection is also source-only.

`poses/prayer.svg` and its placement metadata provide an authored pose with separately transformed arm segments. `prayer` is not a supported scene enum. The low kneeling silhouette retains a compatible runtime torso with fixed bent limbs, plus separate arm source SVGs under `poses/` for further editing; it does not yet have independently animated kneeling joints. This is a renderer limitation, not a fully animated kneeling rig.

Ghost tint/fade is still imposed by `storyvid/render.py`, so runtime ghosts will not retain the pure black/white source palette. Camera zoom currently affects the background, not actor scale. The Short renderer uses a square stage inside the vertical frame. No core code, scene narration, or review.json is changed by this character pass.

## Rebuild and previews

From the repository root:

```sh
.venv/bin/python assets/bac-bo-stick/extra/tools/build_stung_characters.py
.venv/bin/python -m storyvid.check --assets
.venv/bin/python assets/bac-bo-stick/extra/tools/export_stung_characters.py
.venv/bin/python assets/bac-bo-stick/extra/tools/export_stung_poses.py
.venv/bin/python -m unittest discover -s tests
```

Previews and transparent exports go to `output/stung_treng/characters/` (ignored by Git). No paid image-generation or speech request is needed to rebuild these SVG assets. Each character folder includes an expression contact sheet. The source archive contains a subset extra manifest; merge its entries when installing into an existing extra pack instead of replacing the whole manifest.

The story cast has not yet been switched to the new `stung_*` human presets. Final video, audio, subtitle, shot-duration and full-frame Short checklist items still require the production integration/review pass. Before publication, complete user checklist sections 8–9.
