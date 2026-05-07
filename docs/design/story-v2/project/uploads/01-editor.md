# Module: Editor (Bản thảo)

> **Manual-first:** Toàn bộ chức năng editor + link Event/Character làm thủ công.
> **AI-optional:** AI extract / suggest / continue là layer optional, có toggle ON/OFF toàn cục. Tool dùng được hoàn chỉnh khi AI = OFF.
> **Schema canonical:** [06-data-model.md](06-data-model.md) — Chapter ở §3.4, ChapterSnapshot ở §3.10.
> Tham khảo [spec.md](spec.md) cho flow tổng và build order.

## Mục đích

Là nơi writer **đưa bản thảo vào hệ thống** và **chỉnh sửa khi cần**. Đây KHÔNG phải editor cạnh tranh với Word/Scrivener — chỉ đủ dùng để:
1. Import bản thảo từ nguồn khác
2. Parse thành chương/cảnh có cấu trúc
3. Cho phép sửa chữa nhỏ và viết tiếp trực tiếp
4. Cung cấp text source cho phân tích AI khi bật (optional)

## User stories

### Story 1: Import lần đầu
> Là một writer đã viết được 30 chương trên Word, tôi muốn upload file .docx vào hệ thống và thấy nó tự động chia thành các chương riêng biệt, để tôi không phải copy-paste từng chương.

### Story 2: Viết tiếp trong app
> Là một writer đang viết chương 31, tôi muốn viết trực tiếp trong app, đồng thời tạo event/gắn character ngay trên timeline mà không cần thoát ra tool khác.

### Story 3: Edit chỉnh sửa
> Là một writer phát hiện sai chính tả ở chương 5, tôi muốn click vào đoạn đó và sửa ngay, không cần download → sửa Word → upload lại.

### Story 4: Sync ngược về Word
> Là một writer dùng Word làm bản chính, tôi muốn export lại bản thảo (kể cả những chương tôi viết trong app) ra .docx để giữ Word là source of truth.

## Tính năng chi tiết

### 1.1 Import bản thảo

**Định dạng hỗ trợ (core):**
- `.docx` (Microsoft Word)
- `.txt` (plain text)
- `.md` (Markdown)
- Paste trực tiếp từ clipboard

**Định dạng nâng cao (optional, build sau khi core ổn):**
- `.epub`
- Google Docs (qua API)
- Scrivener `.scriv` (phức tạp, không ưu tiên)

**Quy trình import:**
1. User upload/paste
2. Hệ thống parse → detect chương → preview cấu trúc
3. User xác nhận cấu trúc (có thể merge/split chương nếu parser sai)
4. Hệ thống lưu, trigger AI extract pipeline ở background

**Edge case cần xử lý:**
- File không có heading rõ ràng (toàn text liền) → fallback: chia theo độ dài hoặc dòng trống
- File có nhiều style heading lẫn lộn → ưu tiên Heading 1, fallback Heading 2
- File có image / table → core: bỏ qua image, giữ text. Cảnh báo user.
- File có comment / track changes → bỏ qua, chỉ lấy clean text
- File quá lớn (>500k chữ) → cảnh báo, gợi ý chia nhỏ

### 1.2 Chapter parser

**Quy tắc nhận diện chương (priority order):**
1. Style "Heading 1" trong .docx
2. Dòng có pattern: `Chương\s+\d+`, `Chapter\s+\d+`, `第\d+章`, `第\s*\w+\s*章`
3. Dòng đầu có format đặc biệt: in đậm + đứng riêng + dài < 50 ký tự
4. Dòng phân cách (---, ***, ===) ngăn cách các đoạn

**Cấu trúc chương:** xem [06 §3.4 Chapter](06-data-model.md#34-chapter) cho schema đầy đủ. Parser fill các field chính:

```ts
{
  title           // extract từ heading
  content         // rich text (TipTap JSON)
  content_hash    // dùng cho incremental AI extract
  word_count      // theo word_count_unit hiện tại ("chữ" cho VN)
  order           // thứ tự trong story (narrative order)
  status: 'draft' // default
  is_finalized: false
}
```

Auto-save tạo `ChapterSnapshot` (06 §3.10) — giữ 50 snapshot gần nhất, manual checkpoint không bị rotation.

**Preview cấu trúc trước khi confirm:**
- Hiện list chương: số chương, tiêu đề, số chữ
- Cho phép: rename, merge với chương trước, split tại vị trí, delete
- Cho phép thêm chương trống

### 1.3 In-app editor

**Tech baseline:** TipTap hoặc Lexical (rich text, extensible).

**Tính năng tối thiểu (core):**
- Bold, italic, underline
- Heading (H1 = chương, H2 = scene, H3 = sub-section)
- Bullet/numbered list
- Blockquote
- Spell check (browser native, đủ cho VN)
- Undo/redo (Ctrl+Z, Ctrl+Shift+Z)
- Word count realtime (chương hiện tại + toàn bản thảo)
- Auto-save mỗi 5 giây hoặc khi user dừng gõ 2 giây

**KHÔNG có trong scope:**
- ❌ Track changes (writer muốn → dùng Word)
- ❌ Comment/annotation (không có collaboration ở personal tool)
- ❌ Custom font / color
- ❌ Table, image
- ❌ Footnote
- ❌ Multiple cursor / collaborative editing

**Layout đề xuất (3 cột):**
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [Sidebar trái:        │  [Editor]                  │ [Sidebar phải:      │
│  Chapter list]        │                            │  Context panel]     │
│                       │                            │                     │
│  Chương 1 ✓          │  ## Chương 5: Gặp gỡ      │ [Event] [Character] │
│  Chương 2 ✓          │                            │ ──────────────────  │
│  Chương 3 ✓          │  Lý Thanh Vân bước vào... │ Tab: Event          │
│  Chương 4 ✓          │  ↑ (highlight tên nhân    │                     │
│ ▶ Chương 5 (đang sửa)│     vật khi hover)         │ Events ở chương 5:  │
│  Chương 6            │                            │  ● #5 Gặp sư phụ    │
│  + Thêm chương        │  [auto-save ✓]            │    👥 LTV, Sư phụ   │
│                       │                            │    🌳 main          │
│                       │                            │  ○ #6 Học kiếm     │
│                       │                            │    👥 LTV, Sư phụ   │
│                       │                            │                     │
│                       │                            │ [+ Tạo event mới]   │
│                       │                            │                     │
└──────────────────────────────────────────────────────────────────────────┘
```

**Layout responsive:**
- Mỗi sidebar có thể collapse riêng (icon chevron)
- Có thể resize bằng drag border
- Mặc định: chapter list 240px, editor flexible, context panel 320px
- Khi màn hình hẹp (< 1280px): right sidebar ẩn mặc định, có toggle nhanh

### 1.4 Context panel (sidebar phải) — Event & Character tabs

Đây là **không gian làm việc song song với editor**: trong khi viết bản thảo ở giữa, writer thấy ngay events và characters liên quan đến chương hiện tại ở bên phải. Mục đích: giảm context switching, link nhanh khi viết.

**Cấu trúc:**

```
┌─────────────────────────────┐
│ [Event] [Character]         │ ← Tab switcher
├─────────────────────────────┤
│  ... nội dung tab ...       │
└─────────────────────────────┘
```

#### Tab "Event"

**Hiển thị mặc định:** Events thuộc chương đang mở.

```
┌─────────────────────────────┐
│ [Event] [Character]         │
├─────────────────────────────┤
│ Lọc: [Chương này ▼]         │
│ ─────────────────────────── │
│ Events ở Chương 5:          │
│                              │
│ ● #5 Gặp sư phụ            │
│   👥 LTV, Sư phụ             │
│   🌳 main · ⭐ Major         │
│   📍 Thanh Vân Sơn           │
│   "Khi tỉnh dậy, hắn..."    │
│   [Mở] [Đến đoạn]           │
│                              │
│ ○ #6 Học kiếm cơ bản       │
│   👥 LTV, Sư phụ             │
│   🌳 main · Minor            │
│                              │
│ ─────────────────────────── │
│ [+ Tạo event mới từ vùng]  │
│                              │
│ Gợi ý nhanh:                 │
│ • Đoạn vừa highlight có      │
│   thể là event mới?          │
│   [Tạo từ đoạn này →]       │
└─────────────────────────────┘
```

**Tính năng tab Event:**
- **Lọc dropdown:** Chương này / Toàn bản thảo / Storyline X / Arc X / Character Y
- **Mỗi event card:** title, characters tham gia, Arc, importance, source quote ngắn
- **Click "Đến đoạn":** editor auto-scroll tới paragraph_range của event
- **Click "Mở":** event detail modal/panel
- **Drag event card sang editor:** insert reference link `[Event #5]` vào text (optional, phase 2)
- **Tạo event nhanh:**
  - Khi có đoạn highlight trong editor → button "Tạo từ đoạn này"
  - Khi không có highlight → button "Tạo event mới" mở form trống với chapter_id pre-fill
- **Sort:** theo paragraph_index (đúng thứ tự trong chương)
- **Indicator:** chấm filled/hollow theo importance, color theo Storyline (Arc badge bên cạnh)

#### Tab "Character"

**Hiển thị mặc định:** Characters xuất hiện trong chương đang mở.

```
┌─────────────────────────────┐
│ [Event] [Character]         │
├─────────────────────────────┤
│ Lọc: [Chương này ▼]         │
│ ─────────────────────────── │
│ Trong chương 5:              │
│                              │
│ 👤 Lý Thanh Vân              │
│    Protagonist · 47 events   │
│    Aka: tiểu tử, Vân nhi    │
│    "tóc đen, mắt sáng,      │
│     16 tuổi, vết sẹo má"    │
│    [Mở] [Highlight trong CH]│
│                              │
│ 👤 Lão nhân áo trắng         │
│    Sư phụ · 12 events        │
│    "trầm tĩnh, áo trắng,    │
│     râu bạc"                 │
│    [Mở] [Highlight trong CH]│
│                              │
│ ─────────────────────────── │
│ [+ Tạo character mới]       │
│                              │
│ Drag avatar vào event để    │
│ gắn nhân vật vào event      │
└─────────────────────────────┘
```

**Tính năng tab Character:**
- **Hiển thị:** avatar, tên, role, alias, current appearance description
- **Click "Highlight trong CH":** đánh dấu mọi vị trí tên/alias xuất hiện trong editor
- **Click "Mở":** character detail panel
- **Drag avatar:**
  - Vào đoạn text trong editor → insert tên nhân vật
  - Vào event card (tab Event) → gắn character vào event đó
- **Tạo character nhanh:**
  - Highlight tên trong editor → right-click → "Tạo character" → form pre-fill name
  - Hoặc button "Tạo character mới"
- **Lọc dropdown:** Chương này / Toàn bản thảo / Theo role / Theo faction
- **Sort:** theo importance score, hoặc tần suất xuất hiện trong chương

#### Tương tác giữa editor và context panel

Đây là điểm cốt lõi tạo nên trải nghiệm "viết + quản lý cùng lúc":

**Editor → Panel:**
- Cursor đang ở paragraph X → events có paragraph_range chứa X được highlight trong panel
- Highlight đoạn text → "Tạo event từ đoạn này" enabled trong panel
- Click vào tên nhân vật trong editor → tab Character tự switch + scroll tới character đó

**Panel → Editor:**
- Click "Đến đoạn" trên event → editor scroll + highlight đoạn
- Click "Highlight trong CH" trên character → mọi instance tên/alias trong editor được mark
- Drag event/character từ panel → editor: insert reference

**Sync khi sửa:**
- User sửa text trong editor → events có paragraph_range overlap được mark "needs review"
- User xóa đoạn → cảnh báo nếu có event đang link vào đoạn đó

#### Settings cho context panel

- Toggle visibility (Cmd+\ hoặc nút chevron)
- Default tab: Event hoặc Character (user preference)
- Auto-switch tab theo cursor position (off by default)
- Compact mode (giảm chi tiết mỗi card)
- Keyboard shortcuts:
  - `Cmd+E` → switch sang tab Event
  - `Cmd+Shift+E` → tạo event từ selection
  - `Cmd+P` → switch sang tab Character (P = person)
  - `Cmd+Shift+P` → tạo character từ selection

### 1.5 Highlight & cross-reference (manual mapping)

Khi writer đang viết, app phải làm bản thảo "sống":

**Inline highlight (manual):**
- Tên nhân vật xuất hiện trong text → underline nhẹ (match dựa primary_name + aliases user đã nhập trong Character module)
- Sự kiện đã link vào chương → margin marker bên trái dòng (writer thấy "đoạn này có Event #5")
- Hover tên nhân vật → mini-card

**Click-through navigation:**
- Click vào tên nhân vật → mở character detail panel ở sidebar phải
- Click vào event marker → mở event detail / scroll trên timeline
- Bấm `Ctrl+K` (hoặc `Cmd+K`) → quick search nhân vật/event/chương

**Right-click trên đoạn text:**
- "Tạo event từ đoạn này" → modal tạo event, source_quote tự fill
- "Gắn vào event đã có..." → search và link
- "Tạo character mới từ tên..." → tạo character với tên này

**Quan trọng:** Highlight phải **không cản trở việc viết**. Toggle on/off trong settings.

### 1.6 Liên kết bản thảo với Event/Character (manual)

Đây là phần cốt lõi (manual flow) — writer chủ động link:

**Workflow điển hình:**
1. Writer viết xong 1 đoạn quan trọng trong chương 5
2. Highlight đoạn đó → right-click → "Tạo event từ đoạn này"
3. Modal: title, characters (search/select), Arc (chọn từ Storyline đang active), importance, flag turning/crossover
4. Save → event xuất hiện trên timeline với source_quote

**Cập nhật khi sửa bản thảo:**
- Nếu user sửa text mà đã link vào event → giữ link, cập nhật source_quote
- Nếu user xóa hẳn đoạn link → cảnh báo "Event #5 đang tham chiếu đoạn này, bạn muốn xóa link không?"

**AI-optional:** Khi bật AI, có thể đề xuất event từ chương mới — writer confirm hoặc bỏ qua. Xem mục "AI assist" cuối file.

### 1.7 Export

**Core:**
- `.docx` — full manuscript hoặc chọn chương
- `.txt` — plain text
- `.md` — markdown với frontmatter (chapter title, etc.)
- `.json` — dump toàn bộ data (chapter + codex) để backup

**Nâng cao (optional):**
- `.epub`
- PDF với layout đẹp

### 1.8 Versioning & history

**Core:**
- Mỗi chương lưu snapshot mỗi khi auto-save (giữ 50 snapshot gần nhất)
- User có thể xem lịch sử chương: "30 phút trước", "2 giờ trước"
- Restore chương về phiên bản cũ → tạo snapshot mới (không xóa hiện tại)

**Nâng cao (optional):**
- Diff view giữa 2 phiên bản
- Manual checkpoint với tên ("Bản nháp 1", "Trước khi sửa cốt truyện")
- Restore điểm bất kỳ trong lịch sử snapshot

## Quy tắc nghiệp vụ then chốt

### R1. Bản thảo là source of truth
Mọi thông tin Character/Event/Timeline đều **liên kết tới** bản thảo qua chapter_id + paragraph_range. Bản thảo thay đổi → cập nhật reference, không tự xóa metadata.

### R2. Tool tuyệt đối không tự ý sửa bản thảo
Hệ thống KHÔNG được sửa text trong bản thảo (kể cả khi AI ON). Mọi suggest sửa phải qua user confirm.

### R3. Auto-save không bao giờ mất dữ liệu
- Auto-save phải đảm bảo không mất quá 5 giây gõ phím
- Khi mất kết nối → lưu local (IndexedDB), sync lại khi có mạng
- Hiển thị rõ status: ✓ Đã lưu / ⏳ Đang lưu / ⚠️ Mất kết nối

### R4. Import phải reversible
User upload file rồi đổi ý → cho phép xóa toàn bộ trong 24h (soft delete + hard delete sau).

### R5. Performance gate
- Editor phải mượt với chương 20.000 chữ (không lag khi gõ)
- Sidebar chapter list phải scroll mượt với 200+ chương
- Auto-save không được block UI

## Metric đo lường (personal)

- **Import success rate:** Parse file thành công ≥ 95%
- **Editor performance:** Keystroke → hiển thị < 50ms ngay cả với chương 20k chữ
- **Auto-save reliability:** 0% data loss
- **Personal usability:** Bản thân viết được 50k+ chữ trong tool (xem [spec.md mục 12 Done criteria](spec.md#12-done-criteria-single-milestone))

## Open questions cần quyết định

1. Multiple manuscripts cùng lúc? (đang viết 2-3 truyện song song)
2. Word count theo character (TQ/Nhật) hay word (Anh)? Tiếng Việt mặc định nào?
3. Có cần "research notes" tách biệt với chapter không?
4. Khi user import lại file đã import → merge / tạo mới / thay thế?

---

## AI assist (optional layer)

> Toggle ON/OFF toàn cục trong Settings. Khi OFF, mọi nút AI biến mất khỏi UI. Tool dùng được hoàn chỉnh.

**Khi AI ON, các tính năng thêm vào editor:**

- **Auto-extract** Character + Event từ chương mới hoặc chương vừa sửa (suggest, không tự ghi)
- **Incremental sync:** dùng content_hash để chỉ extract phần thay đổi
- **Auto-highlight:** tên nhân vật được AI nhận diện xuất hiện trong text mà chưa có trong Character module → đề xuất tạo
- **Source quote auto-fill** khi writer tạo event từ đoạn highlight
- **Inconsistency warning** trên editor: gạch chân đỏ khi mô tả nhân vật mâu thuẫn với AttributeHistory
- **Smart cross-reference:** AI hiểu "hắn" trong context là ai → underline đúng
- **Continue writing:** AI viết tiếp 200-500 chữ từ cursor
- **Suggest next beat:** 3 option đoạn tiếp theo
- **Rewrite selection:** AI rewrite đoạn đã chọn theo prompt
- **Ask about story:** Q&A với context (vd: "tu vi nhân vật X ở chương 12?")
- **Trigger logic:** debounce 5 phút sau khi user dừng edit; manual button "Phân tích lại"

**Hard rules (không bao giờ vi phạm):**
- AI không bao giờ sửa bản thảo trực tiếp
- Mọi suggestion qua diff modal để user accept / edit / reject
- User-edited field được tôn trọng (không override khi không hỏi)
- API key lưu local, never leave device

Xem chi tiết AI behavior contract trong [spec.md mục 11](spec.md#11-ai-integration-spec-optional-layer).
