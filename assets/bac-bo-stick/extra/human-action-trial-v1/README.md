# Narrator: articulated 2D action pilot

This trial uses the approved cream-shirt narrator, prepared as a 20-cell transparent drawing atlas. The body is animated by an actual **Blender armature**, not whole-body pose swapping. The .blend contains 16 deform bones, four two-bone IK constraints, named hand/foot/pole controls, 18 skinned image meshes and a weighted shirt mesh.

## Action sequence (12 seconds)

- 0–4 s: walk in with alternating swing and planted-foot intervals.
- 4–6.25 s: stop, turn the head, raise the right hand and aim a flashlight.
- 6.25–7.5 s: startle, raise the arms and recoil.
- 7.5–10.7 s: step backward.
- 10.7–12 s: stop and recover.

The source drawing's sleeves follow upper-arm bones, forearms and hands have their own bones, and trouser legs articulate at hips/knees/ankles. Four complete head drawings provide front/three-quarter/scared/blink states; head rotation is also animated on its bone. The head drawings are substituted for facial/angle changes; the body action is continuous skeletal motion.

## Reproduce

Run from the repository root:

```sh
.venv/bin/python assets/bac-bo-stick/extra/human-action-trial-v1/extract.py
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python assets/bac-bo-stick/extra/human-action-trial-v1/build_blender.py -- --render
/Applications/Blender.app/Contents/MacOS/Blender --background \
  output/stung_treng/human-action-blender/narrator-action-rig.blend \
  --python assets/bac-bo-stick/extra/human-action-trial-v1/verify_blender.py
.venv/bin/python assets/bac-bo-stick/extra/human-action-trial-v1/encode.py
```

Blender 5.1.2 was used. Extraction uses Pillow/NumPy; encoding uses the project's FFmpeg helper. Rebuilds use the committed atlas and PNG layers and make no image-generation or speech requests.

## Editing the rig

The saved .blend opens at the flashlight pose in camera/material view. Enable viewport overlays to see the skeleton and controls. Collections separate the painted background, armature, drawing layers, IK controls, flashlight and camera. Select `Narrator_ROOT` and use Pose Mode for bones, or select `CTRL_hand_l/r`, `CTRL_foot_l/r` and corresponding `POLE_*` objects to edit targets. `Narrator_ROOT` object location controls travel. Timeline markers label each action. The dense authored keys may be simplified for further manual animation.

All 19 used textures are packed. `rig-verification.json` records build-time measurements. `saved-rig-verification.json` comes from reopening the file and evaluating all 288 frames; it checks foot-target error, planted-foot frame pairs, root travel, arm movement and texture packing. `render-verification.json` checks all rendered images and decodes the complete MP4/GIF.

## Scope and limits

This is a **2D cutout rig in Blender**, not a fully modeled 3D character or motion-capture system. Arms are thin graphic lines as approved. Feet use world-space IK targets, not terrain collision/physics. The turnaround is a small head rotation plus a three-quarter drawing, not a 360-degree turn. Sleeve/shoulder and knee seams can still be polished; the trial is meant to judge whether this action approach fits the project.

The flashlight cone is a composited graphic that follows the hand; it does not physically relight the painted backdrop. The review MP4 is 960×540 at 24 fps, and the GIF is 640×360 at 12 fps; neither is the final 1080p publication render. There is no voice/audio track.

No changes are made to storyvid/, scenes.json, review.json, existing rigs, or the whole-ghost source pack. This standalone human trial needs a separately authorized integration pass before Storyvid can use its clips or rig. Final checklist sections 1–7 (story, shot timing, subtitles/audio and Short composition) remain production-review work; user publication/analytics checks remain sections 8–9.
