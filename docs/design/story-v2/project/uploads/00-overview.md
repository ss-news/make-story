# Tổng quan nghiệp vụ — Web Story Tool

> **Tài liệu master:** [spec.md](spec.md). File này bổ sung phần triết lý, đối tượng, thuật ngữ.

## Định hướng

**Personal AI co-writing tool** cho cá nhân — single-user, local-first. Không bán, không marketing, không multi-user.

**Mục tiêu:** Một người (chính bạn) chưa nắm hệ thống viết tiểu thuyết vẫn viết được truyện dài (50k–200k chữ) nhờ:
- Khung sườn Storyline / Arc / Event để tổ chức cốt truyện
- Codex Character / World Bible để giữ nhất quán
- AI là layer optional hỗ trợ brainstorm và đỡ block — **mọi tác vụ đều có thể làm thủ công 100%**

**Phasing:** Không chia phase. Một spec, build theo critical path đến khi đạt Done criteria.

## Đối tượng sử dụng

**Primary user:** Chính bạn (dev + writer cá nhân).

**Đặc điểm:**
- Có thể là người mới hoặc đã quen viết
- Viết web novel dài, đa thể loại (kiếm hiệp / tiên hiệp / ngôn tình / sci-fi / đô thị / fanfiction)
- Comfortable với tool có nhiều knob/setting
- Có khả năng tự viết khung sườn, dùng AI khi muốn brainstorm

## Triết lý sản phẩm

### 1. Manual-first, AI-optional
- Mọi tính năng phải dùng được hoàn chỉnh **không cần AI**
- AI là toggle ON/OFF toàn cục — OFF = tool hoạt động như Plottr/Notion
- AI không bao giờ tự ghi vào DB — mọi output qua user approval

### 2. Đây là analysis & planning tool, viết trong-app cũng được
- User có thể viết hoàn toàn trong app (TipTap editor)
- Hoặc dùng tool ngoài (Word/Scrivener) và import
- Source of truth là bản thảo + codex, lưu local

### 3. Visual hơn form khi cần — text-tree dùng được mọi scale
- Story Map text-tree (Storyline → Arc → Event) là core navigation
- Arc Map / Storyline Grid / DAG là enhancement, không phải core
- Mục tiêu: user "nhìn" được toàn bộ truyện trong 30 giây

### 4. Cấu trúc Storyline → Arc → Event là metaphor chính
- **Storyline (Tuyến):** dòng dài chạy xuyên truyện, song song được (Main / phe / nhóm)
- **Arc (Hồi):** đoạn có bối cảnh + cast + mục tiêu, sequential trong Storyline
- **Turning event:** điểm kết Arc, mở Arc kế trong cùng Storyline
- **Crossover event:** event có nhân vật từ Storyline khác — kết nối qua characters, không qua structure
- Pattern này khớp tự nhiên với web novel/tiên hiệp/light novel

### 5. Character gắn vào event, không tách lane
- Bỏ character swimlane riêng
- Character = participant tại mỗi event node
- Filter timeline để xem journey của 1 nhân vật

### 6. AI tôn trọng manual edit
- Mọi field có flag `user_edited`
- AI không override `user_edited=true` mà không hỏi
- Mọi suggestion vào diff modal để user accept / edit / reject

## Modules chính

| Module | Mục đích | File chi tiết |
|---|---|---|
| **Editor** | Viết chương, link Event/Character | [01-editor.md](01-editor.md) |
| **Character** | Quản lý nhân vật, alias, AttributeHistory, Trait | [02-character.md](02-character.md) |
| **Event** | Sự kiện trong Arc, gắn nhân vật + thời gian | [03-event.md](03-event.md) |
| **Timeline (Storyline/Arc)** | Story Map, navigation cấu trúc | [04-timeline.md](04-timeline.md) |
| **World Bible** | Setting, magic, faction, glossary | mục 4.6 trong [spec.md](spec.md) |

## Mối quan hệ giữa các module

```
        ┌──────────┐
        │  Editor  │  ← Bản thảo (source of truth)
        └────┬─────┘
             │ link manual + (AI optional)
             ▼
   ┌─────────────────────┐         ┌─────────────────┐
   │      Character      │◀────────│      Event      │
   │  (gắn vào event)    │ tham gia│  (thuộc Arc)    │
   └─────────────────────┘         └────────┬────────┘
                                            │ thuộc
                                            ▼
                                     ┌──────────────┐
                                     │     Arc      │
                                     │  (thuộc      │
                                     │  Storyline)  │
                                     └──────┬───────┘
                                            │ visualize
                                            ▼
                                     ┌──────────────┐
                                     │  Story Map   │
                                     └──────────────┘
```

- **Editor** lưu bản thảo
- **Character** là entity độc lập, được tham chiếu bởi Event
- **Event** thuộc đúng 1 **Arc**, có nhiều Character tham gia
- **Arc** thuộc đúng 1 **Storyline**, sequential trong Storyline
- **Storyline** có thể chạy song song (max 5)
- **Story Map** visualize Storyline + Arc + Event qua tree view (default) + các view nâng cao (sau này)
- Filter character trên Story Map = cách xem journey của 1 character

## Nguyên tắc quyết định scope

Khi cân nhắc thêm tính năng, hỏi 4 câu:

1. **Có giúp viết được truyện dài 50k+ chữ không?** Nếu chỉ giúp flash fiction → bỏ.
2. **Có làm được hoàn chỉnh không cần AI không?** Nếu phụ thuộc AI để dùng được → không build, hoặc thêm fallback manual.
3. **Có thuộc critical path để self-host viết truyện không?** Nếu không → hoãn (xem [spec.md mục 14 Build order](spec.md#14-build-order-gợi-ý-1-phase-ưu-tiên-critical-path)).
4. **Có làm tool phức tạp hơn cần thiết không?** Personal tool — đơn giản thắng đẹp.

## Thuật ngữ thống nhất

- **Bản thảo (Manuscript) / Story (Project):** Toàn bộ tác phẩm
- **Chương (Chapter):** Đơn vị chính của bản thảo
- **Sự kiện (Event):** Một biến cố/hành động quan trọng — thuộc đúng 1 Arc
- **Nhân vật (Character):** Một thực thể trong truyện
- **Storyline (Tuyến):** Một dòng dài chạy xuyên truyện, song song được
- **Arc (Hồi):** Một đoạn truyện có bối cảnh + cast + mục tiêu, sequential trong Storyline
- **Turning event:** Event đánh dấu kết Arc, mở Arc kế
- **Crossover event:** Event có nhân vật từ Storyline khác (auto-detect)
- **Story time:** Thời gian xảy ra trong thế giới truyện
- **Narrative order:** Thứ tự kể trong bản thảo
- **POV character:** Nhân vật mà chương/scene đang kể từ góc nhìn
- **AttributeHistory:** Lịch sử thay đổi của một thuộc tính (appearance/personality/...) theo event
- **Trait:** Đặc tính có vòng đời (item/skill/ability/status) — acquired/lost theo event
- **User-edited:** Flag trên field, AI tôn trọng khi sync
- **Codex:** Tổng hợp Character + World Bible — context layer cho AI

## Status

- ✅ Master spec ([spec.md](spec.md)) — Done
- ✅ Canonical schema ([06-data-model.md](06-data-model.md)) — Done (resolve conflict spec ↔ module docs)
- ✅ Module docs (01-04) — Done, fields canonical theo 06
- ⏳ AI prompt template / Context Builder — Chưa làm
- ⏳ Bắt đầu build theo Build order trong spec.md
