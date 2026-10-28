# Trial: approved ghost artwork split and animated

`character-actions.gif` is a 12-second loop at 800×760. It tests appearance, blinking, looking left/right, bringing the hands together, bowing, crying, changing to a shy smile, lowering the hands and fading away.

## Source and method

- `model-sheet.png`: approved single-character model sheet.
- `atlas-transparent.png`: background extracted with built-in ImageGen, retaining the atlas layout.
- `animate.py`: crops the separate artwork parts, extracts facial ink/color, assembles the character and animates it using Pillow/NumPy and two-bone inverse kinematics.
- `parts/`: 48 nonempty transparent PNG layers, including face-expression combinations, separate eyebrow/eye/mouth overlays, hair, head, torso, arms, hands and wisps. The count includes expression derivatives; it is not 48 independent body bones.
- `rig.json`: explicit source crop boxes, canvas and limb lengths.
- `separated-parts.jpg`, `contact-sheet.jpg`: actual layer/animation review boards.
- `verification.json`: decoded GIF timing and layer checks.

## Run

Use Python with Pillow and NumPy. From this repository:

```sh
.venv/bin/python assets/bac-bo-stick/extra/experiments/legless-raster-trial/animate.py --out output/stung_treng/character-trial
```

Optional output folder:

```sh
.venv/bin/python output/stung_treng/character-trial/animate.py --out output/stung_treng/character-trial-rerun
```

The script reads the transparent atlas next to itself. It makes no external generation or TTS calls. On another operating system, set `FONT` in the script to a Unicode TrueType font installed there.

## Limits shown by the trial

The approved artwork was cut out rather than redrawn as geometric SVG. Arm segments rotate separately and head layers share a neck pivot. The sleeves still belong to the torso, so their silhouette does not articulate with the arms. The head performs a 2D tilt, not a true front/side turn; looking sideways shifts facial features. Some antialiasing and edge alignment still need cleanup for final production. The palette GIF is for visual review, not final video delivery.

This prototype does not change scenes.json, any existing runtime rig, storyvid code, or review.json. It is not yet integrated into Storyvid. The raster artwork is independent of the earlier SVG source pack.
