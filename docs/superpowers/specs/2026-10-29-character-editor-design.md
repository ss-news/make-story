# Web 2D chỉnh nhân vật

User approved: web 2D chỉnh và lưu vị trí, sau đó AI dùng cấu hình để tối ưu Blender.

Local web app using existing Narrator PNG layers, Vietnamese UI. Canvas supports selecting, dragging, zooming, pivot editing, layer ordering, expression swapping and numeric position/size/rotation. Undo/redo, browser autosave, named disk saves, JSON import/export and transparent PNG snapshot. Pose presets are editable 2D layout references, not Blender simulation. Preview uses the real source PNGs.

Versioned JSON stores canvas dimensions, source-pack identity and each part's source ID, absolute pivot coordinates, normalized pivot, dimensions, rotation, visibility and order. No filesystem paths accepted from imports. Server validates bounded finite values and exact part/source IDs before saving into output/stung_treng/character-editor; never overwrites source images or scenes. Invalid imports leave the current document intact.

A standalone Blender importer reads saved JSON and builds an editable, packed-image layout matching web transforms. AI uses the approved JSON/layout as reference when retargeting the existing articulated rig; this task does not automatically overwrite that rig or promise identical skeletal animation. Bound localhost only; local same-origin writes. No changes to storyvid/ or review.json.

Validation: persistence roundtrip, malformed/oversized/path-traversal rejection, browser drag/pivot/undo/expression/save/load/import/export, small-screen layout, screenshot inspection, Blender coordinate smoke check, project unit tests and asset validator.
