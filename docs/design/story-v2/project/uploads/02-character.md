# Module: Character (Nhân vật)

> **Manual-first:** Tất cả thao tác CRUD/link làm thủ công đầy đủ.
> **AI-optional:** AI auto-extract + co-reference + inconsistency là layer optional. Tool dùng được khi AI = OFF.
> **Schema canonical:** [06-data-model.md](06-data-model.md) — Character §3.5, Trait §3.6, AttributeHistory §3.11, CharacterSnapshot §4.1.
> Tham khảo [spec.md](spec.md) cho flow tổng và build order.

## Mục đích

Quản lý toàn bộ nhân vật trong bản thảo. Là **entity độc lập** được tham chiếu bởi Event. Writer có thể:
- Tạo / sửa / xóa nhân vật
- Quản lý alias (các cách gọi khác)
- Track sự xuất hiện qua các event/chương
- Theo dõi thay đổi thuộc tính (history)
- Filter timeline theo nhân vật

## Triết lý
- **Character không có lane riêng trên timeline.** Họ xuất hiện như participant của event.
- **Filter là cách chính để theo dõi 1 nhân vật.** Click avatar → timeline highlight events có họ.
- **Mọi thông tin nhân vật do writer tự nhập manual.** AI có thể đề xuất khi bật, nhưng never tự ghi.

## User stories

### Story 1: Tạo nhân vật mới
> Là một writer, tôi muốn tạo nhanh nhân vật mới với tên + role, sau đó bổ sung chi tiết dần khi viết.

### Story 2: Quản lý alias
> Là một writer truyện kiếm hiệp với 1 nhân vật có 5 cách gọi (tên thật, đạo hiệu, biệt hiệu, đại từ), tôi muốn lưu tất cả alias trong 1 entry để không nhầm.

### Story 3: Gắn nhân vật vào event
> Là một writer khi tạo event, tôi muốn drag avatar nhân vật vào event để đánh dấu họ tham gia, vai trò gì.

### Story 4: Theo dõi sự xuất hiện
> Là một writer, tôi muốn biết nhân vật A đã xuất hiện ở event/chương nào, lần đầu khi nào, đã bao lâu rồi không xuất hiện.

### Story 5: Tra cứu nhanh khi viết
> Là một writer đang viết chương 30, tôi quên màu mắt nhân vật phụ, tôi muốn `Cmd+K` gõ tên là ra ngay.

### Story 6: Filter timeline theo nhân vật
> Là một writer, tôi muốn click vào nhân vật → timeline tự động highlight tất cả event họ tham gia, các event khác mờ đi.

### Story 7: Theo dõi thuộc tính thay đổi
> Là một writer, tôi muốn ghi rõ "nhân vật A bị mất tay ở event 50" để các event sau đó khi mô tả tôi nhớ.

### Story 8: Mạng quan hệ quanh nhân vật chính
> Là một writer, tôi muốn mở Relationship Graph với Lý Thanh Vân ở giữa, thấy ngay cha/sư phụ/người yêu/đồng môn/kẻ thù xếp xung quanh, kèm tiến triển ("bạn → người yêu" qua các event). Kéo slider thời gian xem mạng quan hệ thay đổi qua từng chương.

### Story 9: Phát hiện quan hệ chưa nhập
> Là một writer, tôi muốn bật chế độ "Co-appearance" trên graph để thấy 2 nhân vật cùng xuất hiện nhiều event nhưng tôi quên nhập Relationship — tool gợi ý bổ sung.

## Cấu trúc dữ liệu

### Character entity

> **Schema canonical = [06 §3.5](06-data-model.md#35-character).** Tóm tắt dưới đây giữ outline cho context; field đầy đủ + invariant ở 06.

```ts
Character {
  id, story_id
  home_storyline_id              // default = Storyline Main; dùng cho crossover detection (06 D5)

  // Định danh
  primary_name, aliases[], pronouns[]    // "hắn", "nàng", "y"

  // Phân loại
  role          // free-form, autocomplete từ presets VN
  faction
  tags[]        // cross-cut, free-form

  // Mô tả với history (xem AttributeHistory §3.11)
  appearance:    AttributeHistory
  personality:   AttributeHistory
  background:    AttributeHistory
  life_status:   AttributeHistory   // alive / deceased / missing / imprisoned / transformed / sealed
                                    // (thay current_status string đơn — 06 D6)

  // Visual
  avatar_url
  color         // hex, unique trong story

  // Tracking (auto-cache từ CharacterEventLink)
  first_appearance_event_id
  last_appearance_event_id
  appearance_count

  notes
  source        // 'user' | 'ai_suggested' | 'imported'
}

CharacterEventLink {     // junction
  character_id, event_id
  role_in_event: 'main' | 'supporting' | 'witness' | 'mentioned' | 'affected'
  notes
}
```

**Role presets VN (autocomplete, custom string cho phép):** "Nam chính", "Nữ chính", "Nam phụ", "Nữ phụ", "Phản diện chính", "Phản diện phụ", "Hỗ trợ", "Cameo", "Quần chúng", "NPC".

**`AttributeHistory`** dùng chung cho appearance/personality/background/life_status — xem [06 §3.11](06-data-model.md#311-attributehistory-universal). Mỗi version có `effective_from_event_id`, `reason`, `source`.

**`CharacterSnapshot`** (computed at point T) — state nhân vật tại event/chapter bất kỳ; default ordering = `story_time`. Dùng cho timeline tooltip, editor sidebar khi cursor ở chapter N, AI context. Xem [06 §4.1](06-data-model.md#41-charactersnapshot--state-at-point-t).

### Role vs Tag — phân biệt

- **Role** = phân loại vai trò chính trong dàn diễn viên. Một character có **đúng 1 role**. Dùng để filter/group ở mức cao (Nam chính, Nữ phụ, Phản diện…).
- **Tag** = nhãn tự do user gán, **nhiều tag/character**. Dùng để cross-cut: `#kiếm sĩ`, `#có dị năng`, `#đến từ Phương Nam`, `#chưa lộ thân thế`. Tag được quản lý tập trung ở Manuscript settings (rename, merge, xóa hàng loạt).

Role có preset tiếng Việt nhưng **không cố định** — user có thể gõ custom (vd: thể loại huyền huyễn có "Đệ tử thánh địa", "Kiếm tu", "Đan tu"). Custom value sẽ được lưu lại làm gợi ý cho lần tạo sau trong cùng manuscript.

### Trait — đặc tính tích lũy

Khác với `appearance` / `personality` / `background` (mỗi field 1 mô tả với history), **trait** là **danh sách các thực thể** mà nhân vật sở hữu hoặc mang theo:

- **Item** (đồ vật): "Thanh Vân kiếm" — có từ event #20, mất ở event #45
- **Skill** (kỹ năng học được): "Cửu Dương thần công" — học từ event #15, lên cấp 2 ở event #30
- **Ability** (năng lực bẩm sinh): "Trí nhớ siêu phàm" — innate, không có acquired event
- **Status** (trạng thái): "Trúng độc Hắc Vương" — từ event #30, được giải ở event #50

Mỗi trait có vòng đời (acquire → lost) và **versions** (level up / nâng cấp / diễn tiến). Khi xem timeline, hover avatar nhân vật ở event N → tooltip hiển thị **các trait đang active tại event N**.

→ AI optional: AI scan bản thảo, đề xuất trait mới (vd: "Cửu Dương thần công xuất hiện lần đầu ở chương 8 — tạo trait?").

### Tại sao cần AttributeHistory?

Vì **nhân vật thay đổi theo thời gian truyện**:
- Event 1: "tóc đen, mắt sáng, 16 tuổi"
- Event 30: "tóc bạc một nửa sau biến cố"
- Event 80: "mất một mắt sau trận chiến"

Writer cần ghi lại: thuộc tính này có từ event nào, vì sao thay đổi. Khi đến event sau, có context để mô tả nhất quán.

**Manual:** writer tự thêm version khi muốn track thay đổi.
**AI optional:** khi bật, AI scan bản thảo gợi ý version mới — user accept/reject.

## Tính năng chi tiết

### 2.1 Character creation

**Quick create (tối thiểu):**
- Click "Thêm nhân vật" hoặc shortcut `N`
- Modal nhanh: tên, role
- Save → nhân vật đã có thể gắn vào event

**Full create (đầy đủ):**
- Tab "Character" → "Tạo mới"
- Form đầy đủ: tên, alias, pronoun, role, faction, tags, mô tả, avatar
- **Role:** dropdown preset (Nam chính, Nữ chính, Nam phụ, Nữ phụ, Phản diện chính, Phản diện phụ, Hỗ trợ, Cameo, Quần chúng, NPC) hoặc gõ custom. Custom value lưu thành gợi ý cho lần sau.
- **Tags:** chip input — gõ + Enter, autocomplete từ tag đã tồn tại trong manuscript.
- Có thể upload avatar (image, hoặc placeholder với initial)
- Chọn màu để dễ phân biệt trên timeline

### 2.2 Character list view (grid)

```
┌─────────────────────────────────────────────────┐
│ [Search] [Filter: All/Main/Side] [Sort] [+ Mới] │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌────┐  ┌────┐  ┌────┐  ┌────┐                │
│  │ 👤 │  │ 👤 │  │ 👤 │  │ 👤 │                │
│  │Lý  │  │Trần│  │Vương│  │Hoa │                │
│  │T.V.│  │N.H.│  │D.   │  │N.  │                │
│  │MAIN│  │ANTI│  │SIDE │  │SIDE│                │
│  │#47 │  │#12 │  │#8   │  │#5  │                │
│  └────┘  └────┘  └────┘  └────┘                │
│                                                  │
│  ┌────┐  ┌────┐  ┌────┐  [+ Mới]               │
│  │ 👤 │  │ 👤 │  │ 👤 │                        │
│  └────┘  └────┘  └────┘                        │
└─────────────────────────────────────────────────┘
```

**Card hiển thị:**
- Avatar (image hoặc initial)
- Tên chính
- Role badge (vd: "Nam chính" — màu khác nhau theo role)
- Tag hàng dưới (max 3, "+N" nếu nhiều hơn)
- `#N` = số event tham gia
- Border color = character color

**Sort options:**
- Tần suất xuất hiện (default)
- Alphabet
- Lần đầu xuất hiện
- Custom order (drag to reorder)
- Last edited

**Filter:**
- Theo role (multi-select, có cả preset + custom)
- Theo faction
- Theo chương xuất hiện (range)
- Theo tag (multi-select, AND/OR mode)
- Theo trait (vd: "có sở hữu Thanh Vân kiếm", "đã học Cửu Dương")

**Bulk actions:**
- Chọn nhiều → set role, faction, tag, color đồng loạt
- Add/remove tag hàng loạt
- Export character list ra Markdown/JSON

### 2.3 Character detail panel

Click card → mở panel ở phải hoặc full screen:

```
┌─────────────────────────────────────────────────┐
│ [Avatar] Lý Thanh Vân                  [Sửa]    │
│          aka: tiểu tử, Lý công tử, Vân nhi      │
│          Nam chính · 47 events                   │
│          🏷 #kiếm sĩ #protagonist #có dị năng    │
├─────────────────────────────────────────────────┤
│ [Tổng quan] [Ngoại hình] [Tính cách] [Quá khứ] │
│ [Đặc tính] [Quan hệ] [Lịch sử xuất hiện] [Note]│
├─────────────────────────────────────────────────┤
│                                                  │
│  Tab content                                     │
│                                                  │
└─────────────────────────────────────────────────┘
```

**Tab "Tổng quan":**
- Tên, alias, role, faction, tags
- Avatar, color
- Mô tả ngắn (one-liner)
- Stats: số event, lần đầu/cuối xuất hiện, gap dài nhất
- Tag editor: chip input với autocomplete

**Tab "Ngoại hình" (và các tab thuộc tính khác):**
- Current value (hiện tại)
- Lịch sử thay đổi: timeline mini hiện các version
  - Version 1 (Event 1): "tóc đen, mắt xanh"
  - Version 2 (Event 30): "tóc bạc một nửa" - "bị biến cố"
  - Version 3 (Event 80): "mất một mắt" - "trận chiến với Ma vương"
- Nút "+ Thêm version" — writer tự thêm khi nhân vật thay đổi

**Tab "Đặc tính" (Traits):**
- 4 sub-section: Items / Skills / Abilities / Status (+ Other nếu có)
- Mỗi item là 1 card với: icon, tên, kind, status (active/lost), acquired/lost event, level/version hiện tại
- Filter: Active only / Lost / All
- `[+ Thêm đặc tính]` → modal tạo trait
- Click trait → expand chi tiết: description, full version history, notes
- Drag để reorder
- Bulk: chọn nhiều → set tag, xóa

**Tab "Lịch sử xuất hiện":**
- Bar chart: chương x trục → cường độ xuất hiện
- List event tham gia, click để jump
- Phát hiện gap dài: "Không xuất hiện từ chương 30 đến 45"
- Nút "Xem trên Timeline" → mở Timeline với filter sẵn nhân vật này

**Tab "Quan hệ":**
- List quan hệ với nhân vật khác (manual writer định nghĩa)
  - Cha của: Lý Phụ
  - Sư phụ: Lão nhân áo trắng
  - Bạn thân: Vương Đại
- Mỗi quan hệ có note + có thể gắn event "khi quan hệ bắt đầu"

**Tab "Note":**
- Free-form rich text
- Writer ghi gì cũng được: ý tưởng tương lai, cảm hứng, reference

### 2.4 Edit inline

Mọi field trên detail panel đều có thể click để sửa inline:
- Click vào tên → editable
- Click vào tag → có thể add/remove
- Click vào version → sửa hoặc xóa

**Auto-save:** sau 1 giây dừng gõ.

### 2.5 Manage aliases

Trong character detail, section Alias:

```
Aliases:
  ┌─────────────────────────────────────┐
  │ tiểu tử                          [×]│
  │ Lý công tử                       [×]│
  │ Vân nhi                          [×]│
  │ [+ Thêm alias]                      │
  └─────────────────────────────────────┘
```

- Add: gõ tên + Enter
- Remove: click ×
- Mỗi alias có thể đánh dấu "primary in chapters X-Y" (phase 2)

**AI optional:** AI scan bản thảo, đề xuất alias dựa trên co-reference detection — user confirm.

### 2.6 Quick search (Cmd+K)

Bấm `Cmd+K` (Mac) / `Ctrl+K` (Win):

```
┌──────────────────────────────────────┐
│ 🔍 Tìm nhân vật, sự kiện, chương... │
├──────────────────────────────────────┤
│ Lý                                   │
├──────────────────────────────────────┤
│ 👤 Lý Thanh Vân (Protagonist)        │
│ 👤 Lý Mộ Bạch (Side)                 │
│ 📍 Lý gia trang (Location)           │
└──────────────────────────────────────┘
```

- Fuzzy search trên tên, alias, note
- Arrow + Enter
- Shortcut: `c:` → chỉ character, `e:` → event, `ch:` → chapter

### 2.7 Drag & drop integration với Timeline

Đây là điểm tích hợp **quan trọng nhất** giữa Character và Timeline:

**Drag character vào event (trên timeline):**
- Mở timeline + character sidebar
- Drag avatar từ sidebar vào event card
- Modal nhỏ: chọn role (main/supporting/witness/mentioned/affected)
- Save → character gắn vào event

**Drag character ra khỏi event:**
- Hover event → các avatar hiện
- Drag avatar ra khỏi card → remove

**Click avatar trong event:**
- Mở character detail panel

### 2.8 Filter timeline theo character (thay swimlane)

Đây là **cách chính** để theo dõi journey của 1 nhân vật:

**Cách 1: Từ character card**
- Right-click character → "Xem timeline của nhân vật này"
- Hoặc nút "Xem trên Timeline" trong detail panel

**Cách 2: Từ timeline filter**
- Mở timeline → filter sidebar → chọn character
- Các event có character → opacity 100%
- Event khác → opacity 30% (highlight mode)
- Hoặc ẩn hoàn toàn (hide mode)

**Multi-character filter:**
- Chọn 2+ nhân vật
- Mode "OR": event có ít nhất 1 trong số đó
- Mode "AND": event có cả nhóm cùng tham gia (rất hữu ích để tìm "khi nào A và B cùng xuất hiện")

**Visual indicator:**
- Trên timeline, mỗi event có row avatars các nhân vật tham gia
- Filter active → border highlight events match
- Status bar: "Đang xem: Lý Thanh Vân · 47 events · Gap: chương 30-32"

### 2.9 Track attribute changes

Khi nhân vật thay đổi (bị thương, già đi, đổi tên):

**Manual flow:**
1. Vào tab "Ngoại hình" (hoặc tab thuộc tính khác)
2. Click "+ Thêm version"
3. Form:
   - Mô tả mới
   - Có hiệu lực từ event nào (chọn từ dropdown)
   - Lý do thay đổi
4. Save → version được lưu

**Khi xem timeline:**
- Tooltip avatar nhân vật trong event sẽ show mô tả **đúng version tại thời điểm event đó**
- Vd: hover avatar ở event 50 → "tóc bạc một nửa, mất một mắt"

### 2.9b Manage traits (đặc tính: items / skills / abilities / status)

Trait quản lý các thực thể character **sở hữu hoặc mang theo** xuyên suốt truyện. Khác với attribute (mô tả thuần) — trait có vòng đời (acquire → lost) và versions (level up).

**Tạo trait:**
1. Tab "Đặc tính" → `[+ Thêm đặc tính]`
2. Modal:
   - Kind: ◉ Item ○ Skill ○ Ability ○ Status ○ Other
   - Name (required), description
   - Acquired at: chọn event (hoặc "innate / từ đầu truyện")
   - Icon (emoji picker), color, tags
3. Save → trait xuất hiện trong tab Đặc tính, status = Active

**Cập nhật trait theo thời gian (versions):**
- Vd: Skill "Cửu Dương thần công" lên cấp
  - Version 1: "Cấp 1" — từ event #15
  - Version 2: "Cấp 2 — chống được hỏa độc" — từ event #30
  - Version 3: "Đại thành" — từ event #65
- Click trait → "+ Thêm version" → form: value, effective_from event, reason

**Đánh dấu lost (mất):**
- Click trait → button "Mark as lost"
- Chọn event mà trait bị mất / được giải / bị tước đi
- Status đổi thành "Lost" — vẫn lưu lại để track lịch sử
- Có thể "Restore" nếu sau này lấy lại

**Kind-specific behaviors:**

| Kind | Đặc điểm | Ví dụ |
|---|---|---|
| **Item** | Có thể chuyển giao (transfer) cho character khác | Thanh Vân kiếm, Cửu Long ngọc, tín vật |
| **Skill** | Có thể level up (versions), không transfer (trừ truyền công) | Cửu Dương thần công, Lăng ba vi bộ |
| **Ability** | Innate, không có acquired event mặc định | Trí nhớ siêu phàm, máu thuần huyết tộc |
| **Status** | Tạm thời, thường có lost event | Trúng độc, mang thai, mất trí nhớ |
| **Other** | Custom — vd: "danh hiệu", "chức vụ" | Minh chủ võ lâm, đệ tử trưởng |

**Transfer item giữa characters (phase 1.5):**
- Trên trait kind=item: "Transfer to…" → chọn character khác + event transfer
- System tạo: lost_at_event cho character cũ, acquired_at_event cho character mới
- Item history giữ chuỗi sở hữu (ownership chain)

**Visual integration với timeline:**
- Hover avatar nhân vật ở event N → tooltip hiện **traits đang active tại event N** (theo acquired/lost time)
- Trên event detail, section "Đặc tính kích hoạt": list traits của các character tham gia tại event đó
- Filter timeline theo trait: "Events có character đang sở hữu Thanh Vân kiếm"

**Visual trên character grid:**
- Card character có 1 dòng nhỏ liệt kê tối đa 3 trait icon active (vd: 🗡 ⚡ 💀) + "+N"
- Hover → mini-list tất cả trait active

### 2.10 Manual relationship management

Trong tab "Quan hệ" của character:

```
┌─────────────────────────────────────────┐
│ Quan hệ với nhân vật khác               │
├─────────────────────────────────────────┤
│  👤 Lý Phụ (Cha)                        │
│     "Mất khi LTV 5 tuổi"                │
│     Bắt đầu: trước truyện               │
│                                          │
│  👤 Lão nhân áo trắng (Sư phụ)          │
│     "Cứu khi bị truy sát"               │
│     Bắt đầu: Event 5                    │
│                                          │
│  👤 Trần Như Hoa (Bạn → Người yêu)      │
│     Tiến triển:                         │
│      - Event 8: Gặp lần đầu             │
│      - Event 25: Trở thành bạn          │
│      - Event 47: Trở thành người yêu    │
│                                          │
│  [+ Thêm quan hệ]                       │
└─────────────────────────────────────────┘
```

**Tạo quan hệ:**
- Search character + chọn type (cha/mẹ/bạn/người yêu/sư phụ/kẻ thù/...)
- Optional: gắn event bắt đầu
- Optional: track tiến triển (multiple status changes)

**Visualization:** xem [§2.14 Relationship Graph view](#214-relationship-graph-view).

### 2.11 Merge & split character

**Merge:** 2 entry mà thực ra là 1 nhân vật (vd: bạn tạo nhầm 2 entry)
- Chọn 2 character → "Gộp"
- Chọn primary (giữ tên/avatar/note nào)
- Tất cả event link, attribute history merge
- Soft delete cái còn lại (undo trong 30 ngày)

**Split:** ngược lại

### 2.12 Soft delete & restore

- Xóa character → archived 30 ngày
- Trong archive: list các character đã xóa, có thể restore
- Sau 30 ngày → hard delete

### 2.13 Avatar handling

**Manual (core):**
- Upload image (jpg/png/webp, max 2MB)
- Crop tool đơn giản (square crop)
- Auto-resize 256x256
- Default: initial của tên trên background = character color

**AI optional (sau khi core ổn):**
- Generate avatar bằng AI (DALL-E/Midjourney) từ description
- Avatar variations theo version (vd: trẻ vs già)

### 2.14 Relationship Graph view

> **Mục đích:** Trả lời câu **"Nhân vật chính đứng giữa mạng quan hệ nào?"** trong 5 giây — visualize ai liên quan ai, vai trò gì, tiến triển ra sao.
> **Schema canonical:** dựa trên [06 §3.9 Relationship](06-data-model.md#39-relationship) (đã có `progressions[]` track tiến triển theo event).

#### A. Layout

Force-directed graph 2D, **trung tâm = nhân vật chính** (center node), các nhân vật liên quan xếp xung quanh theo vòng đồng tâm:

```
┌───────────────────────────────────────────────────────┐
│  [Center: Lý Thanh Vân ▼]   Storyline: Main ▼  ◷ Ch.50│
│  ┌─────────────────────────────────────────────┐      │
│  │           ●  Lý Phụ (cha, †)                │      │
│  │           │                                  │      │
│  │   Trần ●──┼──● LTV ──● Lão nhân (sư phụ)    │      │
│  │   Như Hoa │           │                      │      │
│  │  (người   │           ●  Sư huynh A         │      │
│  │   yêu)    │              (đồng môn)          │      │
│  │           ●  Tô Ngọc                         │      │
│  │              (đồng minh, crossover)          │      │
│  │                                              │      │
│  │   ◯ ring 1 (trực tiếp)  ◯ ring 2 (gián tiếp)│      │
│  └─────────────────────────────────────────────┘      │
│  Filter: [Type ▼] [Storyline ▼] [Status: Active ▼]   │
│  Mode: ● Relationship  ○ Co-appearance               │
│  [Export PNG] [Export SVG]                            │
└───────────────────────────────────────────────────────┘
```

**Quy tắc visual:**
- **Node size:** to dần theo số quan hệ (degree centrality); center node luôn lớn nhất
- **Node color:** theo `Character.home_storyline_id` — nhân vật khác Storyline = visual cue crossover
- **Avatar:** dùng `Character.avatar_url` hoặc initial trên background `Character.color`
- **Edge:**
  - Màu/style theo `Relationship.type` group: gia đình (xanh), tình cảm (hồng), sư đồ (vàng), bạn/đồng minh (xanh lá), kẻ thù (đỏ), khác (xám)
  - Độ dày = importance (custom field hoặc auto theo số progressions)
  - Nét đứt = quan hệ đã chấm dứt (có progression `status = 'broken' | 'ended'` hoặc `related_character.life_status` = chết tại thời điểm đang xem)
  - Label edge = `progressions[].status` mới nhất tại thời điểm đang xem (vd: "bạn → người yêu")

#### B. Center node — chọn ai làm trung tâm

- **Default:** POV character của Storyline `is_main = true`. Nếu Storyline có nhiều `pov_character_ids`, lấy phần tử đầu.
- **Manual:** dropdown "Center" cho user chọn bất kỳ character nào — graph re-render với center mới
- **Click node:** click 1 lần → highlight; double-click → set node đó làm center (truy hồi lịch sử qua nút "Back")

#### C. Time-aware (story_time slider)

Graph là **state at point T**, dựa trên [06 §4.1 CharacterSnapshot](06-data-model.md#41-charactersnapshot--state-at-point-t):

- **Slider thời gian** ở đầu view: chọn theo `chapter_id` hoặc `event_id`
- Khi slider thay đổi:
  - Edge ẩn nếu `Relationship.started_at_event_id` chưa xảy ra tại T
  - Edge label đổi theo `progressions[]` — lấy progression cuối có `changed_at_event` ≤ T
  - Node ẩn nếu character chưa xuất hiện tại T (`first_appearance_event_id` > T) hoặc đã chết và user toggle "Hide deceased" (tùy chọn)
- Default T = chapter cuối có nội dung (latest)
- Có nút "Theo dõi tiến triển" → animate slider từ Ch.1 → cuối, người dùng xem mạng quan hệ phát triển

#### D. Filter & Mode

**Filter:**
- **Storyline:** chỉ hiện character thuộc Storyline được chọn (multi-select). Default = mọi Storyline.
- **Type:** filter theo `Relationship.type` group (gia đình / tình cảm / sư đồ / bạn / kẻ thù / khác)
- **Hop depth:** 1 (trực tiếp), 2 (bạn-của-bạn), all
- **Status:** active / ended / all
- **Min importance:** ẩn các nhân vật `role = 'cameo' | 'walk-on'` để giảm noise

**Mode:**
1. **Relationship mode (default):** edges lấy từ `Relationship` entity — dữ liệu manual.
2. **Co-appearance mode:** edges auto-tính từ `CharacterEventLink` — 2 character cùng xuất hiện ở ≥ N events thì có edge (N tunable, default 3). Hữu ích phát hiện quan hệ chưa được nhập manual.
3. **Hybrid:** overlay cả 2 — edges manual đậm, edges co-appearance nhạt (gợi ý "có thể bạn cần nhập quan hệ ở đây").

#### E. Tương tác

| Hành động | Kết quả |
|---|---|
| Click node | Highlight node + edges trực tiếp; mờ phần còn lại |
| Double-click node | Set node làm center mới (push history) |
| Hover edge | Tooltip: type, started_at, progressions list, reason gần nhất |
| Right-click node | Menu: "Mở character detail", "Xem timeline filter", "Set as center" |
| Right-click edge | Menu: "Sửa quan hệ", "Thêm progression", "Xóa quan hệ" |
| Drag node | Reposition manual; pin nếu giữ Shift (force-layout không kéo về) |
| `Cmd/Ctrl + scroll` | Zoom |
| `Cmd/Ctrl + 0` | Reset view |
| `Back` button | Trở về center trước (history stack) |

#### F. Export

- **PNG / SVG:** snapshot graph hiện tại + filter + slider position
- **JSON:** node + edge structure để dùng tool ngoài (Gephi, …)

#### G. Performance gate

- Mượt với 100 character + 300 relationship
- Filter / slider re-render < 200ms
- Layout convergence < 1s với 50 nodes, < 3s với 100 nodes

#### H. AI assist (optional)

- **Suggest missing relationships:** Co-appearance mode phát hiện 2 character cùng xuất hiện ≥ 5 events nhưng chưa có Relationship → gợi ý "có thể đây là quan hệ X". User accept → tạo Relationship qua diff modal.
- **Suggest progression:** AI quét chapter content nơi 2 character tương tác → gợi ý progression mới (vd: "Ch.25: trở thành bạn"). Manual approval qua diff modal.

#### I. Edge case

1. **Character không có quan hệ nào:** hiện ở góc graph, ring xa nhất, nhãn "(chưa có quan hệ)". Không ẩn, để dễ phát hiện và bổ sung.
2. **Quan hệ self-referential:** không cho phép (validation tại tạo Relationship).
3. **Reciprocal mismatch** (vd: A là "cha" của B nhưng B chưa có "con" của A): hiện edge một chiều với icon mũi tên + warning "thiếu reciprocal". Click warning → quick add reciprocal.
4. **Disconnected graph:** nếu chọn center mà các character khác không kết nối tới → hiện thành các cluster rời, vẫn render.
5. **Mass character (50+):** auto bật filter `min importance ≥ supporting`, kèm gợi ý "Ẩn cameo để dễ nhìn".

## Quy tắc nghiệp vụ then chốt

### R1. Character tồn tại độc lập với Event
Có thể tạo character chưa gắn event nào (planning ahead). Có thể xóa event mà không xóa character.

### R2. Mọi thay đổi đều có history
Edit attribute → tạo version mới chứ không overwrite. User có thể rollback hoặc xem lịch sử.

### R3. Color phải unique trong manuscript
Tránh trùng màu giữa các character — gây rối khi xem timeline. Auto-suggest màu khác khi tạo mới.

### R4. Soft delete only
Không hard delete trong UI bình thường. Phải vào archive, click "Xóa vĩnh viễn".

### R5. Privacy & ownership
Bản thảo + character data là tài sản của writer. Không share, không train.

### R6. Role tự do nhưng được chuẩn hóa
Role cho phép custom string, nhưng UI phải gợi ý khớp value cũ (autocomplete) để tránh "Nam chính" vs "Nam Chính" tạo 2 group khác nhau. Settings tab → "Manage character roles" cho phép merge/rename role giống tag.

### R7. Trait phải có tham chiếu time-correct
Khi hover avatar trong event N, chỉ hiển thị trait có `acquired_at <= N` và (`lost_at == null` hoặc `lost_at > N`). Đây là invariant — vi phạm = bug.

### R8. Performance gate
- Character grid mượt với 200+ characters
- Search/filter response < 100ms
- Detail panel load < 200ms

## Edge cases

1. **Nhân vật vô danh** ("một người đàn ông lạ")
   - Vẫn tạo entry với placeholder name
   - Khi xuất hiện tên thật → rename hoặc merge

2. **Nhân vật cùng tên** (2 người tên "Tiểu Mai")
   - Lưu disambiguator: "Tiểu Mai (sư muội)" vs "Tiểu Mai (kỹ nữ)"
   - Quick search hiện cả 2 với context

3. **Nhân vật là animal/spirit** (linh thú, kiếm linh, AI)
   - Vẫn xử lý như character, có flag `non_human`
   - Tab "Ngoại hình" → đổi nhãn thành "Hình dạng"

4. **POV switching giữa nhân vật**
   - Mỗi chương có thể tag `pov_character_id`
   - POV là metadata của Chapter, không tạo Storyline mới
   - Filter timeline theo POV character = cách xem những chương kể từ góc nhìn nhân vật đó

5. **Massive cast** (200+ nhân vật)
   - UI scale với virtualization
   - Mặc định ẩn minor character
   - Group theo faction
   - Search là cách primary để find

6. **Nhân vật tử vong rồi sống lại / chuyển sinh**
   - Không xóa, dùng AttributeHistory để mark "alive=false từ event X" → "alive=true từ event Y"
   - Có thể có flag `is_alive` trong current state

## Metric đo lường (personal)

- **Character creation friction:** Tạo character mới ≤ 30 giây
- **Character-event linking:** Mọi event quan trọng có ≥ 1 character gắn
- **Filter usage:** Bản thân dùng filter character khi viết arc dài
- **Edit smoothness:** Detail panel load < 200ms với 200+ characters

## Open questions

1. Có cho phép custom field cho character không? (vd: "Cảnh giới tu luyện" cho kiếm hiệp)
2. Avatar: cho phép gắn nhiều avatar (theo phase trẻ/già) hay 1 chính?
3. Khi tạo event, có nên có quick-create character inline (không cần thoát ra tab Character)?
4. Color picker: bảng màu fixed hay free? Tránh writer chọn màu khó nhìn.
5. Voice/dialogue style: có cần track cách nói chuyện đặc trưng (phase 2)?

---

## AI assist (optional layer)

> Toggle ON/OFF toàn cục trong Settings. Khi OFF, mọi nút AI biến mất khỏi UI character.

**Khi AI ON, các tính năng thêm vào module Character:**

- **Auto-extract character từ bản thảo:** Scan chương → đề xuất character + alias + appearance (suggest, không tự ghi)
- **Co-reference resolution:** Resolve "hắn", "nàng", đại từ → đúng character
- **Inconsistency detection:** Mắt xanh chương 5, nâu chương 47 → cảnh báo trong sync diff
- **Soft conflict (evolution detection):** Phân biệt mâu thuẫn vs phát triển có chủ đích
- **Auto-suggest alias:** AI nhận diện cách gọi mới chưa có trong aliases
- **Importance score:** AI tính từ tần suất + role
- **Attribute version suggestion:** Khi nhân vật thay đổi trong bản thảo, AI gợi ý tạo version mới
- **Sync logic:** Conflict resolution UI khi user đã edit + AI muốn update

**Hard rules:**
- Mọi AI output đi qua sync diff modal — user accept / edit / reject từng item
- `user_edited=true` field được tôn trọng tuyệt đối
- AI không bao giờ tự ghi vào DB

Xem chi tiết AI behavior contract trong [spec.md mục 11](spec.md#11-ai-integration-spec-optional-layer).
