# Module: Timeline (Cấu trúc Storyline - Arc - Event)

> **Manual-first:** Writer tự tạo Storyline, Arc, gắn Event, đánh dấu turning/crossover.
> **AI-optional:** AI auto-detect Arc boundary, suggest turning/crossover là layer optional. Tool dùng được khi AI = OFF.
> **Schema canonical:** [06-data-model.md](06-data-model.md) — Storyline §3.2, Arc §3.3, Event §3.7. Khi conflict về schema → 06 thắng.
> Tham khảo [spec.md](spec.md) cho flow tổng và build order. View core là **Story Map text-tree**; Arc Map / Storyline Grid / DAG là enhancement.

## Mục đích

Là **giao diện visual flagship** của sản phẩm. Timeline biến chuỗi event rời rạc thành một bức tranh tổng thể có cấu trúc, giúp writer trả lời 3 câu hỏi cốt lõi:

1. **Cốt truyện đang hướng đi đâu?** (structure & direction)
2. **Event nào là điểm rẽ — vì sao truyện đi theo hướng này?** (turning points & causality)
3. **Nhân vật nào đang ở mục nào của truyện?** (presence map)

Đây là tính năng **screenshot-able**, **demo-able**, là cái khiến writer "ồ wow". UX phải mượt và đẹp.

## Triết lý design

### 1. Arc là đơn vị tổ chức chính
Web novel / tiên hiệp / kiếm hiệp / light novel có cấu trúc tự nhiên là **Arc (Hồi/Quyển)** — một đoạn truyện có:
- Bối cảnh/map riêng (làng tân thủ → tông môn → bí cảnh → ma giới)
- Cast riêng (overlap nhưng có nhân vật mới gia nhập, có người rời đi)
- Mục tiêu riêng (sống sót → bái sư → tỉ thí → tìm bảo vật)
- Climax/Turning event kết Arc → trigger Arc kế

Pattern này phù hợp với web novel / tiên hiệp / kiếm hiệp / light novel — không cần dạy lại metaphor mới.

### 2. Hierarchy 3 tầng cố định
```
Manuscript
└─ Storyline (Tuyến)         ← long-running thread, song song được
   └─ Arc (Hồi)               ← chunk có bối cảnh, sequential trong Storyline
      └─ Event                ← gắn đúng 1 Arc
```

Cố ý **phẳng**, không nested. Hierarchy phức tạp = complexity leak. Khi user yêu cầu sub-arc, refuse và hướng họ tách Arc to thành nhiều Arc nhỏ.

### 3. Parallel ở cấp Storyline, sequential ở cấp Arc
- Storyline: có thể chạy song song (Main / Triều đình / Ma giáo)
- Arc trong cùng 1 Storyline: **luôn sequential**, không overlap chapter
- Nếu thực sự cần 2 đoạn cùng map nhưng song song → đó là 2 Storyline, không phải 2 Arc

Constraint cứng này giúp tránh quay lại bài toán "20 branches" cũ.

### 4. Không có "merge". Crossover qua characters.
Khi nhân vật từ Storyline A xuất hiện ở Arc của Storyline B → đó là **crossover event**. Storyline không kết thúc, không gộp. Mỗi nhân vật giữ nguyên Storyline gốc của mình. Kết nối tự nhiên qua character, không qua structure.

### 5. Turning event là pivot, không phải fork
Turning event đánh dấu **kết thúc 1 Arc và bắt đầu Arc kế** trong cùng Storyline. Nó là điểm quyết định *tại sao* truyện đi theo hướng tiếp theo. KHÔNG phải nơi truyện tách làm 2 đường song song.

### 6. Vertical, top-down (giữ nguyên triết lý cũ)
- Đọc Việt/Anh top-down trong context dài
- Vertical scroll quen thuộc (Twitter feed, document)
- Arc Map có thể horizontal (như reading manga panel), Storyline Grid horizontal cho time, vertical cho storyline

### 7. Editable, không chỉ readable
Writer phải tạo/sửa Arc, gán Event vào Arc, đánh dấu turning, đánh dấu crossover bằng thao tác trực tiếp trên view (drag, click, inline form).

## User stories

### Story 1: Nhìn tổng thể truyện qua Arc Map
> Là writer, tôi mở timeline → thấy chuỗi Arc nối tiếp ("Làng tân thủ → Tông môn → Bí cảnh → Ma giới"), mỗi Arc hiện vắn tắt cast + chapter range + số event.

### Story 2: Thấy nhiều Storyline song song
> Là writer truyện multi-tuyến, tôi muốn thấy Main (LTV), Triều đình (Tô Ngọc), Ma giáo (Huyết Tổ) cùng xuất hiện như 3 hàng song song trên timeline, mỗi hàng có chuỗi Arc riêng.

### Story 3: Đánh dấu turning event
> Là writer, tôi muốn đánh dấu event "Đánh boss Sói" là turning event kết Arc "Làng tân thủ", từ đó Arc "Tông môn" bắt đầu.

### Story 4: Theo dõi nhân vật trong Arc
> Là writer, tôi mở Arc "Tông môn tu tiên" → thấy grid character × chapter — biết LTV xuất hiện xuyên suốt, sư huynh A chỉ Ch.7-15, Trần Như Hoa xuất hiện từ Ch.15.

### Story 5: Phát hiện crossover
> Là writer, tôi muốn đánh dấu event Ch.18 "LTV gặp Tô Ngọc" là crossover giữa Storyline Main và Storyline Triều đình — visual hiện đường mảnh nối 2 hàng tại event đó.

### Story 6: Plan Arc tương lai
> Là writer chưa viết tới, tôi vẽ trước Arc "Bí cảnh" với mục tiêu, cast dự kiến, 3-5 event chưa có chapter — như outline.

### Story 7: Causality trong Arc
> Là writer, tôi muốn vẽ "E5 Bái sư → E6 Học kiếm → E8 Tỉ thí → E12 Đột phá Trúc Cơ (turning)" thấy mạch logic của Arc.

### Story 8: Filter character xuyên truyện
> Là writer, tôi click avatar LTV → toàn bộ timeline highlight Arc/Event LTV tham gia, các phần khác mờ đi, kèm "gap analysis" (LTV vắng mặt từ Ch.20-25).

## Cấu trúc dữ liệu

### Storyline / Arc / Event (outline)

> **Canonical schema:** [06 §3.2 Storyline](06-data-model.md#32-storyline--tuyến), [06 §3.3 Arc](06-data-model.md#33-arc--hồi), [06 §3.7 Event](06-data-model.md#37-event--đơn-vị-logic-của-cốt-truyện). Outline dưới chỉ điểm key field; field đầy đủ + invariants ở 06.

```ts
type Storyline = {
  id: UUID
  story_id: UUID
  name: string                       // "Main", "Triều đình", "Ma giáo"
  description?: string
  display_order: int
  color: string
  icon?: string
  is_main: boolean                   // đúng 1 Storyline có is_main = true (06 I3)
  is_active: boolean                 // false = đã kết trong story-time
  pov_character_ids: UUID[]          // POV chính (hint)
  source: 'user' | 'ai_suggested' | 'imported'
  created_at: ISODateTime; updated_at: ISODateTime
  deleted_at?: ISODateTime
}

type Arc = {
  id: UUID
  story_id: UUID
  storyline_id: UUID                 // thuộc đúng 1 Storyline
  name: string
  description?: string
  goal?: string
  setting?: string
  location_id?: UUID

  chapter_start?: int                // suy ra từ events, có thể override
  chapter_end?: int
  status: 'planned' | 'drafting' | 'completed'   // 06 D2 — thay is_planned

  arc_order: int                     // thứ tự sequential trong Storyline (06 I4)
  closing_event_id?: UUID            // turning event của Arc (06 I5)

  color?: string
  collapsed: boolean
  source: 'user' | 'ai_suggested' | 'imported'
  created_at: ISODateTime; updated_at: ISODateTime
  deleted_at?: ISODateTime
}

// Event (chi tiết ở 03-event.md / 06 §3.7) — các field then chốt cho timeline:
type EventTimelineFields = {
  arc_id: UUID                       // bắt buộc — Event thuộc đúng 1 Arc
  is_turning: boolean                // 06 D8 — đổi tên từ is_turning_event
  is_crossover: boolean              // auto-detect từ home_storyline_id của characters (06 D5)
  crossover_override?: 'force_on' | 'force_off'
  story_time: StoryTime
  narrative_order: int
}
```

**Invariants then chốt (xem 06):**
- I3: đúng 1 `Storyline.is_main = true` per Story.
- I4: `arc_order` unique trong cùng Storyline; Arc sequential, không overlap.
- I5: nếu `Arc.closing_event_id = E` → `E.is_turning = true` và `E.arc_id = Arc.id`.
- I6: max 5 Storyline per Story (default 1 "Main").

**Bỏ hoàn toàn:** `Branch`, `branch_id`, `branched_from_event`, `merged_into_event`, `merging_branch_ids`, `is_branch_point`, `is_merge_point`, `parent_branch_id`, `merged_into_branch_id`, mọi field liên quan tree position kiểu Git.

## Layout visual

### 4.1 View 1 — Arc Map (Overview)

Default landing khi mở Timeline. Trả lời câu **"Cốt truyện hướng đi đâu?"** trong 5 giây.

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Timeline · Truyện X · 4 storylines · 12 arcs · 87 events                 │
│ [Arc Map] [Storyline Grid] [Arc Detail]    [Filter] [Zoom] [+ Arc]       │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  STORYLINE: MAIN (Lý Thanh Vân)                                            │
│                                                                            │
│  ┌───────────┐ ⭐ Đánh ┌───────────┐ ⭐ Bí cảnh ┌──────────┐ ⭐...        │
│  │ LÀNG TÂN  │  boss   │ TÔNG MÔN  │   mở      │ BÍ CẢNH  │              │
│  │ THỦ       │ Sói     │ TU TIÊN   │           │ THƯỢNG   │  ...         │
│  │           │ ──────► │           │ ────────► │ CỔ       │              │
│  │ 📍Thanh   │         │ 📍Thanh   │           │ 📍Hư     │              │
│  │   Khê     │         │   Vân Sơn │           │   Cảnh   │              │
│  │ 👥 4 nv   │         │ 👥 7 nv   │           │ 👥 5 nv  │              │
│  │ 📖 Ch.1-5 │         │ 📖 Ch.6-15│           │ 📖 16-25 │              │
│  │ ● 4 events│         │ ● 8 events│           │ ● 6 ev   │              │
│  └───────────┘         └───────────┘           └──────────┘              │
│                                                                            │
│  STORYLINE: TRIỀU ĐÌNH (Tô Ngọc)                                          │
│                                                                            │
│                      ┌───────────┐ ⭐ Phế đế  ┌──────────┐                │
│                      │ ĐẠI LỄ    │           │ ÂM MƯU   │                │
│                      │ ──────────│ ────────► │ ──────── │                │
│                      │ 📖 Ch.10-14│          │ 📖 15-22 │                │
│                      └───────────┘           └──────────┘                │
│                                                                            │
│  STORYLINE: MA GIÁO (Huyết Tổ)                                             │
│                                                                            │
│                                              ┌──────────┐                 │
│                                              │ TRỖI DẬY │                 │
│                                              │ 📖 18-30 │                 │
│                                              └──────────┘                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**Quy ước:**
- Mỗi hàng = 1 Storyline (color-coded)
- Mỗi block trong hàng = 1 Arc, nối tiếp horizontal
- `⭐` giữa 2 Arc = turning event, có nhãn ngắn
- Arc có `📍 setting · 👥 cast · 📖 chapter range · ● event count`
- Storyline bắt đầu ở chapter khác nhau là OK — block căn theo chapter timeline phía trên (optional thước đo Ch.1...Ch.47)
- Click Arc → mở View 3 (Arc Detail)
- Click ⭐ → focus vào turning event đó, mở Event detail panel

### 4.2 View 2 — Storyline Grid (Chapter × Storyline)

Trả lời câu **"Storyline nào đang ở đâu trong narrative?"**.

```
                    Ch.1  Ch.5  Ch.10  Ch.15  Ch.20  Ch.30  Ch.47
                    ──────────────────────────────────────────────
 MAIN (LTV)         [Làng Tân──⭐──[Tông Môn ─────⭐───[Bí Cảnh ──...
                      Thủ]              tu tiên]             
                                            │                
                                            ╳ Ch.18           
                                            │ (LTV ⇋ Tô Ngọc)  
 TRIỀU ĐÌNH               [Đại lễ──⭐─[Âm mưu────────────────...
                                       Tô Ngọc]              
                                                              
 MA GIÁO                                          [Trỗi dậy──...
```

**Quy ước:**
- X-axis = chapter (narrative order) hoặc story-time (toggle)
- Y-axis = Storyline (drag để reorder)
- Block dài = Arc, dài theo chapter range
- `⭐` giữa 2 block cùng hàng = turning event
- `╳` đường mảnh nối 2 hàng = crossover event
- Hover crossover → tooltip: tên event, characters tham gia, chapter
- Click block → drill xuống View 3

**Toggle ở header:**
- `[Narrative ⇆ Story time]` — đổi X-axis
- `[Show crossovers: ☑]` — ẩn/hiện đường crossover
- `[Compact ⇆ Detailed]` — block hiện chỉ tên hoặc cả cast preview

### 4.3 View 3 — Arc Detail (Drill down)

Trả lời câu **"Trong Arc này, nhân vật nào, event gì, mạch nhân quả ra sao?"**.

```
ARC: TÔNG MÔN TU TIÊN  ·  Storyline: Main  ·  Ch.6-15  ·  8 events
─────────────────────────────────────────────────────────────────
Goal: LTV bái sư thành công, đột phá Trúc Cơ
Setting: Thanh Vân Sơn
Preceded by: Làng tân thủ  →  Followed by: Bí cảnh thượng cổ
─────────────────────────────────────────────────────────────────

PRESENCE GRID                Ch.6  Ch.7  Ch.8  Ch.10  Ch.12  Ch.15
LTV                            ●     ●     ●     ●      ●      ●  
Sư phụ                         ●     ●     ●            ●      ●  
Sư huynh A                           ●           ●             ●  
Trần Như Hoa                                                    ●  
Tô Ngọc      ✦ Triều đình                                       ● ← crossover

CAUSALITY (DAG)

  E5 Bái sư ──► E6 Học kiếm ──► E8 Tỉ thí nội môn ──┐
  (Ch.6)          (Ch.7)            (Ch.10)          │
                                                     ▼
                              ⭐ E12 Đột phá Trúc Cơ
                                  (Ch.15) [TURNING]
                                     │
                                     └─► (mở Arc kế: Bí cảnh)

CROSSOVER trong Arc:
  ╳ E11 (Ch.15) "LTV gặp Tô Ngọc" — Storyline Triều đình
```

**Quy ước:**
- Presence Grid: dot lớn = POV, dot nhỏ = phụ, ô trống = không xuất hiện
- ✦ icon = nhân vật đến từ Storyline khác (crossover)
- Causality DAG: tự layout, force-directed nhẹ, time chảy top-down
- ⭐ = turning event của Arc (đúng 1 cái, là `Arc.closing_event_id`)
- Click event node → mở Event Detail panel (sidebar phải)

### 4.4 Tạo & sửa (manual)

**Tạo Storyline:**
- Sidebar trái → "+ Storyline"
- Form: tên, description, color, POV character (optional), is_main toggle
- Default: 1 Storyline "Main" tự sinh khi tạo manuscript

**Tạo Arc:**
- Trong Arc Map view → click "+ Arc" trên hàng Storyline
- Form: tên, setting, goal, chapter_start/end (hoặc đánh dấu planned)
- Mặc định nối tiếp Arc cuối của Storyline đó
- Có thể insert giữa 2 Arc (right-click Arc → "Insert before/after")

**Gán Event vào Arc:**
- Trong Event detail → field `arc_id` (dropdown các Arc)
- Trong Arc Detail view → drag event từ "Unassigned events" panel vào Arc
- Khi tạo event mới từ Arc Detail → tự gán Arc đó

**Đánh dấu turning event:**
- Mở Event detail → checkbox "Là turning event của Arc này"
- Mỗi Arc có đúng 1 turning event (event này clear thì Arc chưa "đóng")
- Visual: event có viền sao ⭐, hiện ở Arc Map giữa 2 Arc

**Crossover được auto-detect, không cần đánh dấu thủ công:**
- Khi event có character từ Storyline khác (qua `pov_character_ids` hoặc characters của Arc khác cùng manuscript) → auto set `is_crossover: true`
- Writer có thể disable nếu muốn

### 4.5 Filter & focus

```
┌────────────────────────────┐
│ FILTER                      │
├────────────────────────────┤
│ Nhân vật:                   │
│  ☑ Lý Thanh Vân             │
│  ☑ Trần Như Hoa             │
│  ☐ Sư phụ                   │
│                              │
│ Storyline:                   │
│  ☑ Main                      │
│  ☑ Triều đình                │
│  ☐ Ma giáo                   │
│                              │
│ Chương: [1]──[──47]          │
│                              │
│ Type: ☑plot ☑char ☐world    │
│ Importance: ☑major ☑minor   │
│ ☑ Chỉ turning events         │
│ ☑ Chỉ crossover events       │
│                              │
│ Mode: ◉ Highlight ○ Hide   │
└────────────────────────────┘
```

**Smart filter — "Theo dõi nhân vật A":**
- Click character → highlight Arc/Event A tham gia ở cả 3 view
- Show "presence summary": "A xuất hiện trong 7/12 Arc, 34/87 events"
- Show "gap": "A vắng mặt từ Ch.20-25" (1 Arc liên tiếp)

### 4.6 Zoom levels

**Zoom 1 — Bird's-eye:** Arc Map cô đặc, mỗi Arc là 1 ô vuông nhỏ, toàn truyện 1 màn.
**Zoom 2 — Default:** Arc Map đầy đủ thông tin như §4.1.
**Zoom 3 — Storyline Grid:** chuyển sang View 2.
**Zoom 4 — Arc Detail:** vào View 3 cho 1 Arc cụ thể.

Zoom là **chuyển view**, không phải scale UI. Cmd/Ctrl + 1/2/3/4 để switch.

### 4.7 Drag & drop interactions

| Action | Hiệu quả |
|---|---|
| Drag Arc trong cùng Storyline | Đổi `arc_order` (sequential) |
| Drag Arc sang Storyline khác | Reassign `storyline_id` |
| Drag Storyline (handle bên trái) | Đổi `display_order` của Storyline |
| Drag Event sang Arc khác | Reassign `arc_id` |
| Drag character avatar vào Event | Add character |
| Drag character ra khỏi Event | Remove character |
| Drag ⭐ từ event này sang event khác | Đổi turning event của Arc |

**Không có:** drag tạo branch, drag merge, drag tách Arc làm 2 nhánh — vì các operation đó không tồn tại trong model.

### 4.8 Mode switch: Narrative ↔ Story chronology

**Narrative mode (default):**
- X-axis (Storyline Grid) hoặc thứ tự Arc (Arc Map) = thứ tự kể (narrative order)
- Flashback Arc/Event xuất hiện đúng vị trí được kể, có icon FB

**Story chronology mode:**
- X-axis = story time (`Event.story_time.sortable_value`)
- Flashback Arc nhảy lên đầu (đúng thời gian xảy ra trong thế giới truyện)
- Vẽ "narrative cross-reference" — đường mảnh chỉ "Arc/Event này được kể ở Ch.X"

**Switch animation:** event/arc "bay" về vị trí mới, giữ scroll position tương đối.

### 4.9 Mini-map & navigation

```
┌──────────┐
│ MINI-MAP │
│          │
│ MAIN     │
│ ▓▓░▓▓▓░░│  ← mỗi ô = 1 Arc
│ TRIỀU    │
│   ░▓▓░▓░│
│ MA GIÁO  │
│        ▓│
│          │
│ ▓▓▓ ←viewport│
└──────────┘
```

- Drag viewport → pan timeline
- Click Arc → jump tới đó

### 4.10 Keyboard shortcuts

| Phím | Hành động |
|---|---|
| `↑`/`↓` | Navigate giữa Storyline (Grid view) hoặc Arc (Arc Map) |
| `←`/`→` | Navigate giữa Arc (cùng Storyline) hoặc Event (cùng Arc) |
| `Enter` | Mở Arc Detail / Event Detail |
| `A` | Tạo Arc mới (Storyline đang focus) |
| `S` | Tạo Storyline mới |
| `T` | Toggle turning event cho event hiện tại |
| `F` | Mở filter |
| `Cmd/Ctrl + F` | Search |
| `Cmd/Ctrl + 1/2/3/4` | Switch view (Map / Grid / Detail / Bird-eye) |
| `Tab` | Switch narrative / story mode |
| `H` | Toggle highlight/hide filter mode |

### 4.11 Inline planning (Arc/Event chưa viết)

- Tạo Arc với `status: 'planned'` (06 D2), không có chapter — chỉ có goal, setting, cast dự kiến
- Tạo Event trong Arc planned (`Event.is_planned = true`), render dashed border + icon planning
- Khi viết tới chapter đó, manual link planned event với chapter (AI optional: auto-match)

→ App là nơi outline + viết, không chỉ phân tích bản thảo đã viết.

## 5. Sử dụng Arc — workflow

> **Mục tiêu mục này:** mô tả end-to-end cách writer dùng Arc — từ khi tạo, vận hành, đến đóng và refactor. Schema đầy đủ: [06 §3.3 Arc](06-data-model.md#33-arc--hồi).

### 5.1 Arc là gì trong workflow

Arc = **1 đoạn truyện có 4 yếu tố cố định**: **setting** (bối cảnh) + **cast** (nhân vật chính trong đoạn) + **goal** (mục tiêu trong đoạn) + **closing turning event** (sự kiện kết Arc).

Heuristic độ dài cho web novel:
- **Chapter:** 3–15 chương / Arc (sweet spot 5–10)
- **Event:** 5–15 events / Arc (sweet spot 7–12)
- **Word:** 8k–40k chữ / Arc

> Vượt 15 chương / 20 events / 50k chữ → tool gợi ý **split Arc** (xem [§5.6](#56-refactor-arc--split--merge--move-events)).

### 5.2 Arc lifecycle (status)

3 trạng thái cố định ([06 D2](06-data-model.md#8-decisions-đã-chốt)):

```
   ┌─────────┐  start writing first chapter   ┌──────────┐
   │ planned │ ──────────────────────────────▶│ drafting │
   └─────────┘                                 └────┬─────┘
        ▲                                           │ mark turning event
        │ rollback (rare)                           ▼
   ┌────┴──────┐                              ┌───────────┐
   │           │                              │ completed │
   └───────────┘                              └───────────┘
```

| Status | Khi nào | Visual | Edit |
|---|---|---|---|
| `planned` | Mới tạo, chưa có chapter nào thuộc Arc | Dashed border, màu nhạt | Tự do |
| `drafting` | Có ít nhất 1 chapter assigned (qua `Chapter.implicit_arc_id` từ events) | Solid border, màu đậm | Tự do |
| `completed` | `closing_event_id` đã set, turning event đã viết | Viền sao ⭐, header thu gọn | Vẫn edit được nhưng có warning |

**Auto-transition rule:**
- `planned` → `drafting`: khi event đầu tiên trong Arc có `chapter_id` (không còn `is_planned`)
- `drafting` → `completed`: khi `closing_event_id` được set **và** event đó đã có `chapter_id`
- Manual transition: writer override qua dropdown trong Arc detail (cảnh báo nếu vi phạm rule)

### 5.3 Khi nào tạo Arc mới

5 trigger gợi ý — UI có hint khi writer làm các thao tác này:

1. **Đổi setting/map** — "thôn → tông môn → bí cảnh → ma giới"
2. **Đổi mục tiêu chính** — "sống sót → bái sư → phá cảnh giới → trả thù"
3. **Time skip** ≥ vài tháng story-time
4. **Cast change ≥ 50%** — phần lớn nhân vật khác với Arc trước
5. **Climax/turning event vừa xảy ra** — Arc cũ kết, mở Arc kế

Nếu chỉ thay đổi nhẹ (đi vào hang sâu hơn, nhân vật mới phụ xuất hiện) → **vẫn cùng Arc**, không tách. Tool có guideline UI khi writer click "+ Arc" trong khi Arc hiện tại còn rất ngắn (< 3 chương) — cảnh báo "Arc trước mới mở, có chắc tạo Arc mới?"

### 5.4 Tạo Arc — entry points

**(a) Từ Story Map / Arc Map** (tổ chức trước):
- Click "+ Arc" trên hàng Storyline → modal: name, setting, goal, status (default `planned`)
- Nối tiếp Arc cuối của Storyline đó (auto-set `arc_order = max + 1`)
- Có thể "Insert before/after" giữa 2 Arc đã có (re-number `arc_order`)

**(b) Từ Editor** (đang viết, vừa nảy ý cần Arc mới):
- Trong chapter đang viết → right-click → **"Tạo Arc mới ở đây"**
- Modal pre-fill: `chapter_start = chapter hiện tại`, status = `drafting`
- Sau khi tạo, các event mới trong chapter này default vào Arc vừa tạo

**(c) Từ Event detail** (đã có event muốn tách Arc):
- Mở event → Arc dropdown → "+ Tạo Arc mới"
- Pre-fill setting/goal từ context xung quanh event

**(d) Bulk planning** (outline cả mùa truyện):
- Story Map view → "Plan multiple arcs"
- List entry rapid-fire: name + goal × N → tạo cùng lúc, status = `planned`

### 5.5 Vận hành Arc khi đang viết

**Loop hàng ngày:**
1. **Mở chapter cần viết** trong editor — Arc context hiện ở context panel phải (tab Event)
2. **Viết** — tạo event inline khi cần (`Cmd+Shift+E`); event auto-gán Arc của chapter (xem rule 5.5b)
3. **Review cuối chapter** — Arc detail view kiểm tra: events đầy đủ chưa, character coverage, turning đã đặt đúng chỗ chưa
4. **Lặp** sang chapter kế

**(b) Rule infer Arc của chapter** (xem [01-editor.md §3.4](01-editor.md) + [06 §3.4](06-data-model.md#34-chapter--mỗi-chương)):
1. Chapter có event nào có `arc_id` → lấy Arc đó (nếu nhiều, lấy Arc của event có importance cao nhất)
2. Nếu không, lấy Arc của chapter trước (`previous_chapter.implicit_arc_id`)
3. Nếu không, lấy Arc đang `drafting` cuối cùng trong Storyline `is_main`
4. Nếu vẫn không có, prompt writer chọn manual

→ Field `Chapter.implicit_arc_id` cache kết quả; invalidate khi events trong chapter thay đổi.

### 5.6 Đóng Arc — turning event

**Đánh dấu turning event:**
1. Mở event muốn dùng làm turning → checkbox **"Là turning event của Arc này"**
2. System set `Arc.closing_event_id = event.id` và `event.is_turning = true` ([06 I5](06-data-model.md))
3. Nếu Arc đã có turning khác → confirm "Thay turning event cũ?" → clear cờ cũ
4. Visual: event có viền sao ⭐, hiện ở Arc Map giữa Arc này và Arc kế

**Sau khi đóng:**
- Status auto chuyển `drafting` → `completed` (khi event đã có chapter)
- UI gợi ý: **"Tạo Arc kế tiếp?"** với pre-fill `preceded_by_arc_id`
- Story Map bật badge ⭐ tại boundary giữa 2 Arc

**Ép viết turning event:**
- Khi writer cố tạo Arc kế mà Arc hiện tại chưa có turning → cảnh báo "Arc X chưa có turning event, vẫn tiếp tục?"
- Không hard-block (writer có thể outline nhiều Arc trước)

### 5.7 Refactor Arc — split / merge / move events

**Split Arc** (Arc dài quá / có 2 mục tiêu rõ ràng):
1. Mở Arc detail → "Split Arc"
2. Chọn event làm "điểm split" → mọi event sau điểm này tách sang Arc mới
3. Form: name + goal cho Arc mới
4. System:
   - Tạo Arc mới với `arc_order = original.arc_order + 1`, dồn các Arc sau đó
   - Move events: update `arc_id`
   - Recompute `chapter_start/end` cho cả 2 Arc
   - Nếu Arc gốc có `closing_event_id` thuộc nửa sau → chuyển turning sang Arc mới

**Merge 2 Arc liền kề** (Arc quá ngắn, không xứng tách):
1. Chọn Arc A + Arc B (A.followed_by = B) → "Merge into A"
2. System:
   - Move events từ B → A
   - `A.chapter_end = B.chapter_end`
   - `A.closing_event_id` lấy từ B (nếu B có) hoặc clear (nếu A có turning trong nửa đầu, conflict → prompt user chọn)
   - Soft-delete B (restore được trong 30 ngày)

**Move events giữa các Arc:**
- Trong Event list / Arc Detail: select multiple → "Move to Arc..."
- Hoặc drag từ Arc này sang Arc khác trên Story Map
- Validate: `chapter_id` của event phải nằm trong `chapter_start..chapter_end` của Arc đích (nếu không, prompt mở rộng range)

**Đổi Storyline của Arc** (hiếm):
- Arc detail → "Move to Storyline..." → chọn Storyline đích
- Validate: chapter ranges của Arc đích không overlap (R3); recompute `arc_order`
- Cảnh báo: events thuộc Arc này có thể trở thành crossover sau khi đổi (do `home_storyline_id` của characters)

### 5.8 Validation & cảnh báo (rule warning, không block)

| ID | Rule | Trigger | Action gợi ý |
|---|---|---|---|
| W-ARC-LONG | Arc > 15 chương HOẶC > 20 events HOẶC > 50k chữ | Khi vừa add chapter/event vượt ngưỡng | Gợi ý split |
| W-ARC-SHORT | Arc `completed` < 3 chương HOẶC < 3 events | Khi mark turning | Hỏi "có chắc Arc đã xong?" |
| W-ARC-NO-TURNING | Arc `completed` không có `closing_event_id` | Khi user manual chuyển status | Block → yêu cầu set turning |
| W-ARC-OVERLAP | Arc cùng Storyline có chapter range overlap | Real-time khi edit chapter_start/end | [06 R-ARC-OVERLAP](06-data-model.md) |
| W-ARC-NO-GOAL | Arc `drafting`/`completed` thiếu `goal` | Khi mark drafting | Gợi ý điền goal |
| W-ARC-NO-EVENT | Arc `drafting` quá 3 chương mà chưa có event nào | Khi viết chapter thứ 4 | Nhắc "tạo event đánh dấu cảnh quan trọng" |
| W-ARC-CAST-DRIFT | ≥ 80% event trong Arc dùng characters mới so với Arc trước | Khi review Arc | Hỏi "đây có phải Arc mới chưa tách?" |

Tất cả là **warning** — writer có thể bỏ qua. Lưu ở Arc detail panel, badge ⚠️.

### 5.9 Tích hợp với các module khác

**Editor ([01](01-editor.md)):**
- Context panel phải hiện Arc hiện tại (name, goal, progress events) khi đang viết chapter
- Inline `[[arc:Tông môn]]` mention trong bản thảo → link

**Character ([02](02-character.md)):**
- Filter timeline / Relationship Graph theo Arc → chỉ hiện events trong Arc đó
- Character detail có "Tham gia Arc nào" — list Arc có ≥ 1 event mà character xuất hiện

**Event ([03](03-event.md)):**
- Mọi event bắt buộc có `arc_id` (R4); event mới default Arc của chapter (rule 5.5b)
- Bulk: chọn nhiều event → "Set Arc"

**Story Map / Story view:**
- Arc là node chính của Arc Map; expand để xem events
- Filter character vẫn dùng được — Arc nào không có character được filter sẽ mờ

**Export:**
- Export per Arc: markdown chapter content + event list + character list (cho writer chia sẻ "outline Arc X")
- Export full: nested theo Storyline → Arc → Event

### 5.10 Anti-pattern (đừng làm)

- **Arc-of-everything:** 1 Arc dài 100 chapter → tách
- **Sub-arc nested:** Tool không support; nếu thực sự cần, tách thành 2 Arc liên tiếp (Arc A.1, A.2) cùng Storyline
- **Arc dùng làm chương:** 1 Arc = 1 chapter → ngược lại, gộp nhiều "mini-Arc" thành 1 Arc lớn
- **Arc không có turning:** OK khi đang viết, không OK khi `completed`
- **Arc với cast hoàn toàn rời** với Arc trước & sau → có lẽ là Storyline khác

### 5.11 Best practices (gợi ý workflow)

1. **Outline 3 Arc đầu trước khi viết Arc 1** — đặt mục tiêu dài hơi
2. **Mỗi Arc 1 paragraph "premise"** trong field `description` — đọc lại trước mỗi session viết
3. **Cập nhật `goal` khi nhận ra Arc đang đi hướng khác** — đừng giữ goal cũ cho nhất quán giả tạo
4. **Mark turning event trong vòng 1 chương sau khi viết** — đừng để quên
5. **Review Arc đã `completed` mỗi 5 chương** — phát hiện inconsistency với Arc đang viết

## Quy tắc nghiệp vụ then chốt

### R1. Mỗi manuscript có ít nhất 1 Storyline "Main"
Tự sinh khi tạo manuscript. Không xóa được khi vẫn có Arc thuộc Main.

### R2. Storyline tối đa 5 (warning ở 4+)
Quá 5 là dấu hiệu thiết kế truyện sai, không phải tool sai. Hard cap có thể nâng nhưng phải explicit.

### R3. Arc trong cùng Storyline LUÔN sequential, không overlap chapter
Nếu chapter ranges overlap → validation error. Nếu thực sự cần "song song trong cùng map" → đó là 2 Storyline, không phải 2 Arc.

### R4. Event thuộc đúng 1 Arc
Không có event "đa Arc". Nếu event có characters từ Storyline khác → là crossover, vẫn thuộc 1 Arc của 1 Storyline duy nhất (Storyline mà event đó được kể chính).

### R5. Turning event là tùy chọn nhưng đúng 1
- Arc có thể chưa có turning event (đang viết, chưa quyết)
- Khi có thì đúng 1 event được đánh dấu (`Arc.closing_event_id`)
- Turning event phải thuộc chính Arc đó

### R6. Crossover qua characters, không qua structure
Storyline không tách/gộp. Nhân vật từ Storyline A xuất hiện ở Arc Storyline B = crossover event. Cả 2 Storyline tiếp tục độc lập sau đó.

### R7. Không có sub-arc / nested arc
Hierarchy phẳng 3 tầng. Khi user yêu cầu nested → hướng họ tách thành nhiều Arc anh em.

### R8. Performance gate
- 5 Storylines + 30 Arcs + 500 events render < 1.5s
- Pan/zoom 60fps
- Filter response < 200ms
- View switch (Map ↔ Grid ↔ Detail) < 300ms

### R9. Reading direction
Arc Map: top-to-bottom theo Storyline, left-to-right theo Arc order.
Storyline Grid: top-to-bottom Storyline, left-to-right time.
Arc Detail: top-to-bottom (presence grid trên, causality DAG dưới).

## Tech approach

**Render strategy:**
- Arc Map & Storyline Grid: SVG (block + connectors, dễ animate, accessible)
- Arc Detail Causality DAG: SVG + auto-layout (dagre.js hoặc elkjs)
- Presence Grid: HTML table (dễ accessible, performant)

**Layout:**
- Arc Map: flex/grid CSS — không cần custom layout engine
- Storyline Grid: scaled by chapter range — đơn giản hơn Sugiyama nhiều
- Causality DAG: dagre.js cho auto-layout DAG, constraint time-axis top-down

**Lib candidates:**
- **dagre + d3** — DAG layout cho causality view
- **shadcn + tailwind** — Arc/Storyline blocks, presence grid
- **framer-motion** — animation khi switch view, drag
- **react-dnd** — drag & drop Arc/Event

→ **Bỏ kế hoạch fork @gitgraph/react.** Lib đó model Git, không phù hợp model này. Build custom với primitive Tailwind/SVG nhanh hơn fork.

## Edge cases

1. **Truyện đơn tuyến (1 Storyline)**
   - Arc Map = 1 hàng ngang
   - Storyline Grid suy biến thành Arc list dọc
   - Vẫn dùng được, không có overhead

2. **5+ Storylines**
   - Warning, không hard block — writer có thể có lý do
   - Đề xuất gộp Storyline gần (vd: "Phe LTV" + "Phe Hoa" → "Phe chính")

3. **Arc rất dài (50+ events)**
   - Arc Detail render OK với virtualization
   - Đề xuất writer cân nhắc tách Arc — nhưng không force

4. **Crossover dày đặc**
   - Storyline Grid có thể rối nếu crossover quá nhiều
   - Toggle "Show crossovers" off, hoặc filter chỉ crossover liên quan character đang focus

5. **Flashback Arc**
   - Là Arc bình thường, có cờ `is_flashback: true` (optional, có thể infer từ story_time vs narrative_order)
   - Trong Storyline Grid narrative mode: hiện đúng vị trí được kể với border dashed
   - Trong story mode: nhảy lên đầu

6. **Storyline kết thúc giữa truyện**
   - `Storyline.is_active = false` + `ends_at_chapter` set
   - Arc Map: hàng Storyline đó kết ở Arc cuối, không có "next Arc"
   - Visual: hiện chữ "(kết)" hoặc icon

7. **Arc chưa có chapter (planned)**
   - Render dashed border ở mọi view
   - Không tham gia vào chapter range tính toán

## Metric đo lường

- **First meaningful paint:** Arc Map render đủ xem ≤ 1.5s cho 30 Arcs
- **View usage:** % session dùng cả 3 view ≥ 40%
- **Storyline usage:** % truyện có ≥ 2 Storylines ≥ 35% (đo độ hữu dụng của parallel feature; thấp cũng OK vì Main-only là valid pattern)
- **Arc usage:** Trung bình số Arc / truyện ≥ 5 (truyện 200k chữ điển hình)
- **Turning event usage:** % Arc có turning event được set ≥ 70%
- **Crossover detection:** % crossover events được auto-detect đúng ≥ 90% (validate manual)
- **Filter usage:** % session dùng filter character ≥ 50%
- **Plan-then-write:** % Arc/Event tạo `is_planned` trước khi viết ≥ 25%
- **Engagement:** Trung bình thời gian writer ở timeline view ≥ 5 phút/session

## Open questions

1. **Sub-arc nesting:** Khi nào cho phép? Có cần thiết không, hay tách Arc luôn đủ?
2. **Storyline merge / split:** Có scenario writer thực sự muốn 2 Storyline gộp lại thành 1 không? (Vd: 2 phe sáp nhập về cuối) — hiện tại chỉ giải bằng "Storyline cũ kết, Storyline mới bắt đầu", có đủ không?
3. **Crossover cấp Arc:** Có nên cho 1 Arc thuộc nhiều Storyline (vd: Arc "Đại chiến" có cả Main + Triều đình + Ma giáo)? Hay vẫn buộc thuộc 1 Storyline và crossover ở event level?
4. **Mobile:** Arc Map horizontal có ổn trên mobile, hay cần collapse thành accordion?
5. **Export:** Arc Map export PDF/PNG có giữ được structure horizontal không?
6. **What-if alternatives:** Có nên thêm "Sketch mode" cho writer thử kịch bản (Arc A vs Arc B alternative)? — out of scope, hoãn.

---

## AI assist (optional layer)

> Toggle ON/OFF toàn cục trong Settings. Khi OFF, mọi nút AI biến mất.

**Khi AI ON, các tính năng thêm vào module Timeline:**

- **Auto-detect Arc boundary:** Scan chapter sequence → đoán Arc boundary dựa vào setting change, cast change, time skip
- **Auto-suggest turning event:** Trong Arc, tìm event có causality density cao nhất → suggest đánh dấu turning
- **Auto-detect crossover:** Khi event có characters cross-Storyline → suggest đánh dấu với confidence score (manual rule-based đã làm core)
- **Auto-classify Arc setting:** Từ chapter content → suggest setting ("núi", "thành thị", "bí cảnh")
- **Arc health dashboard:** Phát hiện Arc loãng (ít event, ít causality), Arc lệch (cast không nhất quán)
- **Plot hole detection:** Event sau cần tiền đề chưa có ở Arc trước
- **Tone arc visualization:** Extract tone → vẽ emotional arc chart cho từng Storyline

**Hard rules:**
- Mọi AI suggestion có "Apply" / "Dismiss" — không bao giờ auto-apply structural changes
- AI không bao giờ tự reorder Arc/Event hay xóa structure

Xem chi tiết AI behavior contract trong [spec.md mục 11](spec.md#11-ai-integration-spec-optional-layer).
