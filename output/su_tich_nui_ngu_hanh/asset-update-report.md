# Asset and staging update

The script remains in English. Scene numbers below are zero-based.

## Changes

- Split 15 scenes into 31 shorter visual beats; updated short.scenes to [0, 2, 6, 7].
- Added the claw handover and pre-transformation shot; replaced the unrelated rice bundle in the child-care scene.
- Added separate egg growth, cracked shell, milk rock, bird and silk, archery setup/hit, pirate landing, colored stones/flowers, and sunset farewell scenes.
- Separated the turtle departure, mountain origin explanation, and closing invitation.

## New assets

- `props/magical_claw.svg` — Móng thần Kim Quy
- `props/cracked_egg.svg` — Vỏ trứng thần nứt
- `props/milk_rock.svg` — Đá rỉ sữa
- `animals/silk_bird.svg` — Chim mang tơ
- `props/bow_arrow.svg` — Cung và tên
- `props/archery_target.svg` — Bia tập bắn
- `props/archery_target_hit.svg` — Bia trúng tên
- `props/pirate_boat.svg` — Thuyền cướp biển
- `props/colored_stones.svg` — Đá ngũ sắc
- `backgrounds/egg_mound_day.svg` — Trứng đội cát và lều · ngày
- `backgrounds/marble_sunset_day.svg` — Núi Ngũ Hành · hoàng hôn

## Remaining renderer limitations (owner: tool)

- Scenes 0, 2–7, 10–13, 16–20, 25–28: storyvid/render.py uses PROP_DEFAULT = 0.13 for every new prop/animal, with no per-scene scale field. The giant egg, tiger, palanquin, boat and rideable turtle therefore render too small relative to actors. Changing SVG canvas padding cannot correct this because the renderer trims and rescales the visible pixels. These assets are complete, but production sizing requires a tool change.
- Scenes 4, 6, 16, 27: there are no hand attachment points for props, so the claw and bow are presented beside the actors rather than held.
- Scene 28: there is no rider attachment or independent vertical placement. The old man exits during narration of the turtle journey; this is a narrated transition, not an animation of him riding the turtle.
- Scenes 8–11 and 22–23: growth, hatching and flower appearance are represented by cuts between still compositions, not continuous object animation.
- No storyvid code, original base assets or review.json was changed. These tool issues are reported here rather than silently patched.

## Verification

- storyvid.check --assets: exit 0.
- storyvid.check output/su_tich_nui_ngu_hanh/scenes.json: exit 0; asset_requests.json automatically removed.
- unittest discover -s tests: 43 passed.
- assets-added-preview.png: rasterized all 11 new SVGs using the project asset loader.
- storyboard-preview.png: static placement sheet using the real renderer sprites, positions and prop sizing.
- qa/storyboard-smoke.mp4: silent, one second per scene runtime smoke render; not a narrated final video.
