# Web Story — Tài liệu nghiệp vụ

Personal AI co-writing tool cho cá nhân — single-user, local-first. Tool giúp một người viết được truyện dài (50k–200k chữ) bằng cách quản lý Storyline / Arc / Event / Character / World, **mọi tác vụ đều có thể làm thủ công 100%**, AI là layer optional.

## Định hướng sản phẩm

- **Personal tool** — không bán, không marketing, không multi-user
- **Manual-first, AI-optional** — mọi feature work khi tắt AI
- **Single phase** — không chia phase. Build theo critical path tới khi đạt Done criteria
- **Long-form first-class** — UX phải work ở 100k+ chữ

## Cấu trúc tài liệu

| File | Phạm vi | Nội dung |
|---|---|---|
| **[spec.md](spec.md)** | **Master spec** | Triết lý, flow, data model, build order, Done criteria — đọc đầu tiên |
| [00-overview.md](00-overview.md) | Sản phẩm | Triết lý, đối tượng, thuật ngữ, mối quan hệ giữa modules |
| [01-editor.md](01-editor.md) | Module | Editor: viết chương, link Event/Character, context panel |
| [02-character.md](02-character.md) | Module | Character: tạo manual, alias, AttributeHistory, Trait, filter timeline |
| [03-event.md](03-event.md) | Module | Event: tạo manual, gắn Arc, turning event, crossover, causality |
| [04-timeline.md](04-timeline.md) | Module | Timeline: Storyline → Arc → Event; Story Map view |
| [05-site-architecture.md](05-site-architecture.md) | Toàn site | Sitemap, navigation, settings, tech stack |
| **[06-data-model.md](06-data-model.md)** | **Canonical schema** | Entity định nghĩa, invariant, indexes, decisions chốt — đọc trước khi build |

## Cách đọc

**Lần đầu:**
1. **[spec.md](spec.md)** — Master spec, biết build cái gì
2. [00-overview.md](00-overview.md) — Hiểu triết lý và thuật ngữ
3. **[06-data-model.md](06-data-model.md)** — Canonical schema, đọc trước khi viết code DB
4. [05-site-architecture.md](05-site-architecture.md) — Big picture toàn site
5. [01-editor.md](01-editor.md) → [02-character.md](02-character.md) → [03-event.md](03-event.md) → [04-timeline.md](04-timeline.md) — Đi sâu từng module

**Khi cần build:**
- Quyết định flow tổng / build order → đọc spec.md
- Chi tiết module → đọc module doc
- Site-wide (settings, navigation) → đọc 05

## Quan hệ giữa spec.md và các module doc

- **spec.md** = source of truth cho flow, Done criteria, build order
- **06-data-model.md** = canonical schema (entity, field, invariant, indexes, conflict warning rules). Khi conflict về **data** → 06 thắng.
- **Module docs (01-04)** = chi tiết business logic, edge case, UI wireframe. Khi conflict về **flow** → spec.md thắng; về **schema** → 06 thắng.

## Quyết định kiến trúc đã chốt

### Sản phẩm
- **Personal tool** — single-user, local-first
- **Manual-first**, AI là toggle optional toàn cục
- **Source of truth**: bản thảo + codex (lưu local)
- **AI không bao giờ tự ghi vào DB** — mọi output AI qua user approval

### Site-wide
- **Tauri + Next.js + TypeScript + Tailwind + TipTap** (rich text editor) — đã chốt
- **Local storage**: SQLite (better-sqlite3) + FTS5 cho search, không cloud, không auth
- **3-cột layout** trong workspace (story map / editor / context panel)
- **i18n** từ đầu (vi / en), default vi
- Word count default = "chữ" (token tách bởi space) cho VN
- Toàn bộ decisions chốt: [06 §8](06-data-model.md#8-decisions-đã-chốt)

### Timeline
- **Storyline → Arc → Event** hierarchy 3 tầng cố định
- **Storyline (Tuyến):** dòng dài, song song được (max 5; default 1 "Main")
- **Arc (Hồi):** đoạn có bối cảnh + cast + mục tiêu, sequential trong Storyline
- **Turning event:** kết Arc, mở Arc kế (đúng 1 per Arc)
- **Crossover event:** event có character từ Storyline khác (auto-detect)
- **Story Map view** (text-tree, dùng được ở mọi scale) — Arc Map / Storyline Grid / DAG là enhancement sau này
- **Character KHÔNG có swimlane riêng** — tích hợp vào event như participant
- **Filter character** = cách chính theo dõi journey

### Character
- **Entity độc lập**, được Event tham chiếu
- **AttributeHistory** track thay đổi theo thời gian truyện
- **Trait** track item / skill / ability / status có vòng đời

### Event
- **Đơn vị logic của cốt truyện** — thuộc đúng 1 Arc
- **`is_turning_event`** và **`is_crossover`** là metadata flag
- **Story time vs Narrative order** — 2 trục độc lập

### Editor
- **Source of truth là bản thảo** — entity khác link qua chapter_id
- **Context panel bên phải** với Event/Character/AI tabs
- Tool **không tự sửa bản thảo** kể cả khi có AI

### AI layer (optional)
- Toggle ON/OFF toàn cục — OFF = tool dùng được như Plottr/Notion
- 4 action: Suggest next beat / Continue writing / Rewrite selection / Ask about story
- Sync diff modal khi finalize chapter — user approve từng item
- API key local, never leave device

## Status

- ✅ Master spec ([spec.md](spec.md)) — Done
- ✅ Canonical schema ([06-data-model.md](06-data-model.md)) — Done (resolve conflicts spec ↔ module docs)
- ✅ Tài liệu module (01-04) — Done, fields canonical theo 06
- ✅ Tài liệu site-wide (05) — Đã giản lược cho personal tool
- ⏳ Wireframe / Figma — Chưa làm
- ⏳ AI prompt template / Context Builder — Chưa làm

## Bước tiếp theo

Theo [spec.md → mục 14 Build order](spec.md#14-build-order-gợi-ý-1-phase-ưu-tiên-critical-path):

1. Story + Chapter editor + manual save
2. Character CRUD + Codex
3. Storyline + Arc + Event CRUD + Story Map
4. Link Chapter ↔ Event ↔ Character
5. AttributeHistory + Trait + filter timeline
6. World Bible markdown
7. Refactor operations
8. Manual finalize + manual summary
9. Manual conflict warning rule
10. Export JSON/Markdown
11. Settings + AI toggle (OFF default)
12. AI: 4 action + context tier
13. AI: sync diff modal
14. AI: skeleton generator
15. Polish

Sau bước 4 → tự ép viết 5 chương trước khi build tiếp (xem [spec.md → mục 15 Risk](spec.md#15-risk--decision-points)).
