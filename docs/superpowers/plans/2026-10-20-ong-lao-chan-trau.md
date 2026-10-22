# Low-poly buffalo herder implementation plan

**Goal:** Create the approved low-poly Vietnamese elderly buffalo herder as an editable Blender diorama.

**Architecture:** A new scene preserves the existing scene. Separate collections contain the herder, buffalo, environment and studio. Named meshes with flat shading and simple materials provide editable geometry without external assets.

**Tech Stack:** Blender Python via connected Blender MCP.

- [x] Build the elderly man with conical hat, silver facial hair, brown shirt, rolled trousers, sandals and a rope-holding hand.
- [x] Build water buffalo with broad muzzle, swept horns, four cloven hooves, ears, eyes, tail and rope halter.
- [x] Add a faceted grass base, small grass clumps, studio lights and a camera.
- [x] Save a separate blend file, render and inspect the actual model; repair visible issues.
- [x] Verify scene geometry, materials and file paths, then deliver the blend and preview.
