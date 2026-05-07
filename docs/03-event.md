# Module: Event (Sự kiện)

> **Manual-first:** Writer tự tạo, sửa, gắn event vào Arc và character.
> **AI-optional:** AI extract / classify / suggest causality là layer optional. Tool dùng được khi AI = OFF.
> **Schema canonical:** [06-data-model.md](06-data-model.md) — Event §3.7, CharacterEventLink §3.8. Khi conflict về schema → 06 thắng.
> Tham khảo [spec.md](spec.md) cho flow tổng và build order.

## Mục đích

Quản lý các sự kiện trong truyện. Event là **đơn vị logic của cốt truyện** — node trong Arc, kết nối nhân vật với thời gian và mạch nhân quả.

## Định nghĩa: Event là gì?

**Một Event là một sự việc xảy ra trong thế giới truyện, có:**
- Ít nhất 1 nhân vật tham gia (hoặc liên quan)
- Một thời điểm (story time) hoặc thứ tự
- Một mô tả ngắn về việc gì xảy ra
- Thuộc về một **Arc** (Arc thuộc về một Storyline — xem [04-timeline.md](04-timeline.md))

**Event KHÔNG phải:**
- Mỗi câu thoại
- Mô tả cảnh vật thuần túy
- Internal monologue (trừ khi là quyết định quan trọng)

**Granularity gợi ý:**
- ❌ Quá nhỏ: "Lý Thanh Vân uống một ngụm trà"
- ✅ Vừa: "Lý Thanh Vân gặp sư phụ lần đầu"
- ✅ Vừa: "Trận chiến giữa Lý Thanh Vân và Ma vương"
- ❌ Quá to: "Hành trình tu luyện 10 năm" → nên chia thành nhiều event

→ Khi writer manual tạo, có guideline trên UI để giúp họ chọn đúng granularity.

## User stories

### Story 1: Tạo event nhanh khi đang viết
> Là một writer vừa viết xong cảnh quan trọng, tôi muốn một shortcut để tạo event ngay tại đoạn đó (đánh dấu trong bản thảo + tạo entry).

### Story 2: Tạo event planning trước
> Là một writer đang outline, tôi muốn tạo event "tương lai" — chưa có trong bản thảo — để vẽ kế hoạch trên timeline.

### Story 3: Sắp xếp event trong Arc
> Là một writer, tôi muốn drag event lên/xuống trong Arc để đổi thứ tự (story chronology mode).

### Story 4: Gắn nhân vật vào event
> Là một writer khi tạo/sửa event, tôi muốn drag avatar nhân vật vào để đánh dấu họ tham gia, kèm role.

### Story 5: Liên kết causality
> Là một writer, tôi muốn đánh dấu event A "dẫn đến" event B, để khi review thấy mạch logic.

### Story 6: Phân loại theo Arc
> Là một writer, tôi muốn gắn event vào Arc ("Tu luyện ở Thanh Vân Sơn") để timeline group rõ.

### Story 7: Đánh dấu turning event
> Là một writer, tôi muốn đánh dấu event "Đột phá Trúc Cơ" là turning event của Arc "Tông môn tu tiên" — nó kết Arc và mở Arc kế.

### Story 8: Crossover giữa Storyline
> Là một writer, tôi muốn event "Lý Thanh Vân gặp Tô Ngọc" được auto-detect là crossover giữa Storyline Main và Storyline Triều đình (vì Tô Ngọc thuộc Triều đình), không cần đánh dấu thủ công.

## Cấu trúc dữ liệu

### Event entity

> **Canonical schema:** [06 §3.7 Event](06-data-model.md#37-event--đơn-vị-logic-của-cốt-truyện) và [06 §3.8 CharacterEventLink](06-data-model.md#38-charactereventlink--junction-character-event). Outline dưới chỉ điểm key field; field đầy đủ + invariants ở 06.

```ts
type Event = {
  id: UUID
  story_id: UUID
  arc_id: UUID                       // bắt buộc — Event thuộc đúng 1 Arc

  title: string                      // 5–15 từ
  description: string                // 1–3 câu
  source_quote?: string              // trích đoạn gốc

  // Vị trí trong bản thảo
  chapter_id?: UUID                  // null khi is_planned
  paragraph_range?: { start: int; end: int }
  is_planned: boolean

  // Trục thời gian (06 D7: story_time có structured)
  narrative_order: int               // auto từ chapter + paragraph
  story_time: StoryTime              // { type, absolute|relative, sortable_value, duration }

  // Flags (06 D8: đổi tên — KHÔNG còn `is_turning_event`)
  is_turning: boolean                // đồng bộ Arc.closing_event_id
  is_crossover: boolean              // auto-detect từ home_storyline_id của characters
  crossover_override?: 'force_on' | 'force_off'  // user override, mặc định auto

  // Quan hệ
  characters: CharacterEventLink[]   // junction table
  location_id?: UUID
  location_text?: string
  causality: { caused_by: UUID[]; leads_to: UUID[]; foreshadows?: UUID[] }

  // Phân loại
  type: 'plot' | 'character' | 'world' | 'subplot' | 'flashback' | 'other'
  importance: 'major' | 'minor' | 'background'
  tone?: 'tense' | 'romantic' | 'comedic' | 'tragic' | 'mysterious'

  // Visual + meta
  color?: string
  icon?: string
  user_notes?: string
  tags: string[]
  source: 'user' | 'ai_suggested' | 'imported'  // 06 D3 — thay user_edited
  created_at: ISODateTime
  updated_at: ISODateTime
  deleted_at?: ISODateTime           // soft delete
}

type CharacterEventLink = {
  character_id: UUID
  event_id: UUID
  role_in_event: 'main' | 'supporting' | 'witness' | 'mentioned' | 'affected'
  notes?: string
}
```

> **Arc & Storyline entity:** xem [04-timeline.md](04-timeline.md). Arc thuộc đúng 1 Storyline; mỗi Event thuộc đúng 1 Arc.
> **Crossover detection:** dựa vào `Character.home_storyline_id` (06 D5). Nếu event có character với `home_storyline_id` khác Arc.storyline_id → `is_crossover = true` (trừ khi `crossover_override = 'force_off'`).

### Story time vs Narrative order

**Narrative order:** thứ tự kể trong bản thảo. Auto-tính từ position của event trong chapter.
**Story time:** thời gian thực sự trong thế giới truyện. User nhập hoặc relative tới event khác.

**Vd:**
- Event A (Chương 1, narrative_order=1): nhân vật chính 30 tuổi nhìn mộ cha
- Event B (Chương 2, narrative_order=2): flashback 20 năm trước, cha bị giết
  - story_time: relative_to A, offset = "-20 năm"
  - vẫn thuộc Arc đang kể (vd: Arc "Báo thù"); flashback là thuộc tính narrative, không tách Arc
- Event C (Chương 3, narrative_order=3): bắt đầu báo thù

→ Story chronology: B → A → C
→ Narrative order: A → B → C

## Tính năng chi tiết

### 3.1 Event creation

**Quick create từ timeline:**
- Click `+` giữa 2 event hoặc cuối Arc
- Modal tối thiểu: title, description, Arc
- Save → event xuất hiện trên timeline ngay

**Quick create từ editor:**
- Đang viết bản thảo, highlight đoạn → right-click → "Tạo event từ đoạn này"
- Tự động fill: source_quote, chapter_id, paragraph_range
- Modal: title, characters, Arc (default = Arc của chapter hiện tại)
- Source quote hiện như preview, có thể sửa

**Full create:**
- Tab "Event" → "Tạo mới"
- Form đầy đủ: tất cả field
- Có wizard cho người mới: hỏi từng bước

**Planning mode (event chưa viết):**
- `is_planned = true`
- Không có chapter_id
- Render dashed border trên timeline
- Khi viết tới, có thể "convert to actual" + link vào chapter

### 3.2 Event list view

```
┌──────────────────────────────────────────────────────┐
│ [Search] [Filter] [Sort: Narrative ▼] [Group: Arc ▼]│
├──────────────────────────────────────────────────────┤
│ ARC: Làng tân thủ · Storyline: Main                 │
│ ┌──────────────────────────────────────────────────┐ │
│ │ #1 Lý Thanh Vân rời nhà                         │ │
│ │ Chương 1 · plot · major                          │ │
│ │ 👥 Lý Thanh Vân, Mẹ                              │ │
│ │ 📍 Thôn Thanh Khê                                │ │
│ │ ↓ dẫn đến: #3 Gặp sư phụ                        │ │
│ └──────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────────────────────┐ │
│ │ #2 Bị truy sát trên đường                       │ │
│ │ Chương 2 · plot · major                          │ │
│ │ 👥 Lý Thanh Vân, Sát thủ                         │ │
│ └──────────────────────────────────────────────────┘ │
│                                                       │
│ ARC: Tu luyện ở Thanh Vân Sơn                       │
│ ...                                                   │
└──────────────────────────────────────────────────────┘
```

**Sort:**
- Narrative order (default)
- Story chronology
- Importance
- By Arc
- By chapter

**Group:**
- By Arc (default)
- By Storyline
- By chapter
- By type
- Flat

**Filter:**
- Storyline
- Arc
- Character (multi-select)
- Type
- Importance
- Chapter range
- Only turning events
- Only crossover events
- Tag

### 3.3 Event detail panel

```
┌────────────────────────────────────────────────────┐
│ [Sửa] Lý Thanh Vân gặp sư phụ lần đầu             │
│ Chương 5 · Đoạn 12-18 · ⭐ Major · Plot           │
│ Arc: Tông môn tu tiên · Storyline: Main           │
├────────────────────────────────────────────────────┤
│ Mô tả:                                             │
│ Trên đường chạy trốn khỏi sát thủ, Lý Thanh Vân  │
│ ngất xỉu trong rừng. Tỉnh dậy đã thấy mình ở     │
│ Thanh Vân Sơn, được lão nhân áo trắng cứu.       │
│                                                    │
│ Trích từ bản thảo:                                 │
│ ┌────────────────────────────────────────────┐   │
│ │ "Khi tỉnh dậy, hắn thấy một lão nhân áo    │   │
│ │  trắng ngồi cạnh giường, ánh mắt trầm tĩnh"│   │
│ └────────────────────────────────────────────┘   │
│ [Mở chương 5 →]                                   │
│                                                    │
│ Nhân vật:                                          │
│  - Lý Thanh Vân (main)              [×]           │
│  - Lão nhân áo trắng (main)         [×]           │
│ [+ Thêm nhân vật]                                 │
│                                                    │
│ Địa điểm: Thanh Vân Sơn                           │
│                                                    │
│ Thời gian:                                         │
│   Story time: 3 ngày sau #2 (Bị truy sát)        │
│   Duration: 1 ngày                                │
│                                                    │
│ Arc: Tông môn tu tiên              [Đổi]         │
│ Storyline: Main (suy ra từ Arc)                    │
│ □ Là turning event của Arc này                   │
│ ✦ Crossover (auto): không                          │
│                                                    │
│ Quan hệ nhân quả:                                  │
│  Bắt nguồn từ:                                    │
│   ← #2 Bị truy sát trên đường        [×]          │
│   [+ Thêm]                                         │
│  Dẫn đến:                                          │
│   → #6 Bắt đầu học kiếm              [×]          │
│   → #15 Khám phá thân thế thực sự    [×]          │
│   [+ Thêm]                                         │
│                                                    │
│ Tags: [gặp gỡ] [sư đồ] [ngoặt rẽ]   [+]          │
│ Tone: mysterious                     [Đổi]        │
│                                                    │
│ Ghi chú của bạn:                                  │
│ "Quan trọng: cần làm rõ tại sao sư phụ lại cứu"  │
└────────────────────────────────────────────────────┘
```

### 3.4 Inline edit mọi field

- Click vào field → edit ngay
- Auto-save sau 1 giây
- ESC để hủy
- Drag character/event vào causality section để add link

### 3.5 Causality linking

**Manual flow:**
1. Mở event → "Liên kết nhân quả"
2. Search và chọn event khác
3. Chọn loại quan hệ:
   - "Sự kiện này dẫn đến..." (forward)
   - "Sự kiện này bắt nguồn từ..." (backward)
4. Optional: thêm note giải thích

**Drag flow (trên timeline):**
- Drag từ event A xuống event B với phím `Shift` → tạo "A leads to B"

**Visual:**
- Trong event card, indicator nhỏ ←→ với số lượng causality
- Trên timeline, có thể bật "show causality lines" — vẽ line nối các event

### 3.6 Arc & Storyline management (tham chiếu)

Tạo/sửa Arc, Storyline, đánh dấu turning event — **chi tiết ở [04-timeline.md](04-timeline.md)**. Tóm tắt phần liên quan Event:

**Gán Event vào Arc:**
- Trong Event detail → field "Arc" (dropdown)
- Bulk: chọn nhiều Event trên list → set Arc
- Quick create từ chapter: default Arc = Arc của chapter hiện tại

**Đánh dấu turning event:**
- Trong Event detail → checkbox "Là turning event của Arc này"
- Mỗi Arc có đúng 1 turning event (set lại sẽ clear cái cũ)
- Visual: viền sao ⭐, hiện ở Arc Map giữa Arc này và Arc kế

**Crossover detection (auto):**
- System tự set `is_crossover = true` khi event có character của Storyline khác
- `crossover_storyline_ids` auto-tính từ `pov_character_ids` của các Storyline khác
- Writer có thể manual override (vd: tắt cờ nếu không muốn coi là crossover)

### 3.7 Bulk actions

Trên list view, chọn nhiều events:
- Set Arc (kéo theo Storyline)
- Set type / importance
- Add tag
- Delete (soft)
- Export

### 3.8 Convert planned → actual

Khi writer viết tới event đã planned:
1. Vào event đã planned → "Liên kết với chương"
2. Chọn chapter, highlight đoạn liên quan
3. System update: `is_planned = false`, có chapter_id, source_quote
4. Visual trên timeline đổi từ dashed → solid

### 3.9 Soft delete & restore

- Xóa event → archived 30 ngày
- Archive view list events đã xóa
- Restore: đưa event về timeline, các link causality cũ được khôi phục nếu các event link còn tồn tại

### 3.10 Search & navigation

- Quick search Cmd+K → tìm event by title, description, tag
- Click event trong search → mở detail
- Hoặc "Show on timeline" → timeline scroll tới event

### 3.11 Export

- Event list as Markdown (cho writer note ngoài)
- JSON (full data)
- CSV (subset for analysis)

## Quy tắc nghiệp vụ then chốt

### R1. Event phải thuộc đúng 1 Arc
Arc bắt buộc, không null. Khi tạo manuscript có Arc default "Arc 1" trong Storyline "Main".

### R2. Turning event và Crossover là metadata của event
Không có entity "turning point" / "crossover" riêng. Là flag trên event:
- `is_turning` — manual, đúng 1 turning per Arc (đồng bộ với `Arc.closing_event_id`); 06 D8 đã đổi tên từ `is_turning_event`
- `is_crossover` — auto-detect từ `home_storyline_id` của characters tham gia (06 D5); user có thể `crossover_override` = force_on/force_off

### R3. Causality không bidirectional auto
Nếu A "leads to" B, không tự động thiết lập B "caused by" A. User phải set rõ (hoặc UI auto suggest reciprocal).

→ AI optional: AI auto-suggest reciprocal causality khi bật.

### R4. Soft delete only
Mọi delete đều soft. Hard delete chỉ qua archive page.

### R5. Importance là dynamic
User có thể đổi importance. Một event tưởng minor có thể trở major khi truyện phát triển.

### R6. Order rule
- `narrative_order` = auto-calculated từ chapter + paragraph position
- `story_time.sortable_value` = user nhập hoặc relative tới event khác
- 2 trục độc lập, không sync

### R7. Performance gate
- Event list mượt với 500+ events
- Filter < 200ms
- Detail panel load < 200ms

## Edge cases

1. **Event xảy ra trong nhiều chương** ("Trận chiến kéo dài 5 chương")
   - 1 event với `chapter_range: [start, end]` (extension của paragraph_range)
   - Hoặc chia nhỏ thành multiple events liên kết causality
   - User chọn

2. **Event song song**
   - 2 event xảy ra cùng story_time, khác location, thuộc 2 Storyline khác nhau
   - Hiện cùng vị trí trên trục thời gian, ở 2 hàng Storyline khác nhau (Storyline Grid view)

3. **Event mơ hồ thời gian**
   - story_time.type = 'unknown'
   - Render ở "no-time zone" cuối timeline hoặc đặt cạnh chương kể

4. **Event tương lai/giả định**
   - "Nếu... thì...", giấc mơ, dự đoán
   - Type = 'other' với tag `hypothetical` hoặc `dream`
   - Vẫn thuộc Arc đang kể (không tách Arc/Storyline riêng)

5. **Cùng event kể từ nhiều POV**
   - 1 event entity
   - Multiple `narrative_references`
   - Hiện trên timeline nơi POV chính, có marker "cũng được kể ở chương X"

6. **Mass event** (50+ characters tham gia)
   - Chỉ link character major
   - Note: "+ nhiều nhân vật khác"
   - Có thể liệt kê trong description

7. **Event không có character** (vd: "thiên tai", "núi lở")
   - Cho phép, nhưng cảnh báo "Event không có nhân vật, có chắc không?"
   - Hữu ích cho world events

## Metric đo lường (personal)

- **Event creation rate:** Trung bình events/manuscript ≥ 30 (đo độ dùng)
- **Event-character link rate:** % event có ≥ 1 character link ≥ 90%
- **Arc coverage:** % event được gán Arc = 100% (bắt buộc theo R1)
- **Turning event coverage:** % Arc có turning event được set ≥ 70%
- **Causality usage:** % event có ≥ 1 causality link ≥ 30%
- **Planning usage:** % event được tạo planned trước (write-ahead) ≥ 20%

## Open questions

1. Sub-event (event con của event lớn) — phase 1 hay phase 2?
2. Multi-chapter event — UI render thế nào trên timeline?
3. Khi xóa chương, các event của chương đó: orphan hay xóa cũng?
4. Event template (Hero's Journey, Save the Cat) — có giá trị không?
5. Khi user đổi `narrative_order` (di chuyển chương), event tự update?

---

## AI assist (optional layer)

> Toggle ON/OFF toàn cục trong Settings. Khi OFF, mọi nút AI biến mất.

**Khi AI ON, các tính năng thêm vào module Event:**

- **Auto-extract events** từ chương: tự liệt kê events khi user import/viết xong chương (suggest, không tự ghi)
- **Granularity tuning:** AI chia event đúng độ lớn
- **Auto-classify:** type, importance, Arc
- **Suggest causality:** scan "vì... nên...", đề xuất causal links
- **Detect Arc boundary:** khi setting/cast/time-skip đổi → đề xuất tạo Arc mới
- **Detect turning event:** event có causality density cao trong Arc → suggest đánh dấu turning
- **Plot hole detection:** event sau cần tiền đề chưa có
- **Tone analysis:** auto-detect tone từ ngôn ngữ
- **Source quote extraction:** trích đúng đoạn

**Hard rules:**
- AI suggestions luôn qua sync diff modal, user confirm từng item
- User-edited events không bị overwrite
- AI không bao giờ tự ghi/xóa event

Xem chi tiết AI behavior contract trong [spec.md mục 11](spec.md#11-ai-integration-spec-optional-layer).
