# Web Story — Product Spec

**Loại:** Personal AI co-writing tool · single-user · local-first
**Mục tiêu:** Một người chưa nắm hệ thống viết tiểu thuyết vẫn viết được truyện dài (50k–200k chữ). Tool cung cấp khung sườn, quản lý nhân vật/sự kiện/tuyến truyện. AI là layer hỗ trợ optional — **mọi tác vụ đều có thể làm thủ công 100%**.

**Phasing:** Không chia phase. Một spec, build cho đến khi đạt "Done criteria" ở mục 12.

---

## 1. Triết lý cốt lõi

| Nguyên tắc | Implication |
|---|---|
| **Manual-first, AI-optional** | Mọi action có UI thủ công đầy đủ. AI luôn là nút phụ bên cạnh, có thể tắt toàn cục. |
| **User là tác giả, AI là trợ lý** | AI không bao giờ tự động ghi vào codex. Mọi output AI đều qua review/approve của user. |
| **Structure phục vụ context lẫn tư duy** | Storyline/Arc/Event vừa giúp user organize, vừa nén context cho AI khi cần. |
| **Source of truth là bản thảo + codex** | AI có thể fail, mất mạng, hết quota — tool vẫn dùng được như Plottr/Notion. |
| **Long-form first-class** | UX phải work ở 100k+ chữ, không chỉ demo 5 chương. |
| **Single source code** | Không chia phase. Mọi feature build trong cùng codebase, ưu tiên theo critical path. |

---

## 2. Đối tượng: Một writer cá nhân

- Có thể là người mới hoặc đã có thói quen viết
- Viết web novel dài, đa thể loại (kiếm hiệp / ngôn tình / sci-fi / đô thị / …)
- Comfortable với tool có nhiều knob/setting
- Có khả năng tự viết khung sườn truyện, dùng AI khi muốn brainstorm hoặc đỡ block

---

## 3. Module overview

| Module | Mục đích | Manual-only mode |
|---|---|---|
| **Story (Project)** | Container cho 1 truyện | Tạo/đặt tên/xóa thủ công |
| **Storyline** | Tuyến dài chạy xuyên truyện (max 5, default 1 "Main") | CRUD thủ công |
| **Arc** | Đoạn truyện có goal + cast, sequential trong Storyline | CRUD thủ công + drag-reorder |
| **Event** | Biến cố trong Arc | CRUD thủ công + link character |
| **Character** | Thực thể trong truyện + AttributeHistory | CRUD thủ công + đánh dấu lịch sử thay đổi |
| **World Bible** | Setting/magic/faction/glossary | Markdown editor tự do |
| **Chapter** | Bản thảo theo chương | Editor rich text + link Event |
| **Story Map** | View tổng quan Storyline → Arc → Event | View read-only sinh từ data |

→ **Mọi module có CRUD thủ công đầy đủ. AI hỗ trợ là tuỳ chọn ở mỗi action.**

---

## 4. Data model

> **Canonical schema = [06-data-model.md](06-data-model.md).** Mục này list entity high-level; field/invariant/index/conflict-rule đầy đủ ở 06. Khi conflict, 06 thắng.

| Entity | Mục đích | Schema canonical |
|---|---|---|
| **Story** | Container 1 truyện | [06 §3.1](06-data-model.md#31-story) |
| **Storyline** | Tuyến dài, max 5, ≥1 main | [06 §3.2](06-data-model.md#32-storyline) |
| **Arc** | Đoạn sequential trong Storyline | [06 §3.3](06-data-model.md#33-arc) |
| **Chapter** | Bản thảo theo chương | [06 §3.4](06-data-model.md#34-chapter) |
| **Character** | Nhân vật + AttributeHistory (appearance/personality/background/life_status) + Trait + home_storyline_id | [06 §3.5–3.6](06-data-model.md#35-character) |
| **Event** | Biến cố thuộc đúng 1 Arc; có `is_turning`, `is_crossover` (auto), causality | [06 §3.7](06-data-model.md#37-event) |
| **CharacterEventLink** | Junction Character ↔ Event với role | [06 §3.8](06-data-model.md#38-charactereventlink) |
| **Relationship** | Character ↔ Character với progression | [06 §3.9](06-data-model.md#39-relationship) |
| **WorldBible** | Setting/glossary với sections + entries | [06 §3.12](06-data-model.md#312-worldbible) |

**Universal types:** `AttributeHistory`, `Trait`, `ChapterSnapshot`, `Source` enum (`user`/`ai_suggested`/`imported`). Xem [06 §1.3, §3.6, §3.10, §3.11](06-data-model.md).

**Computed:** `CharacterSnapshot` — state của character at point T (event hoặc chapter); default ordering = `story_time`. Hỗ trợ flashback, AI context, continuity check. Xem [06 §4.1](06-data-model.md#41-charactersnapshot--state-at-point-t).

**Conflict warning rules** (cho build step 9): xem [06 §7](06-data-model.md#7-conflict-warning-rules-cho-specmd-mục-9-build-order-step-9) — R-DEAD-APPEAR, R-ARC-OVERLAP, R-TRAIT-LOST-USED, R-CROSSOVER-LATE, R-CONTRADICT-ATTR, ...

**Decisions đã chốt:** [06 §8](06-data-model.md#8-decisions-đã-chốt) — D1 word="chữ" cho VN, D4 storage=SQLite+Tauri, D5 home_storyline_id, D6 life_status history + snapshot, ...

---

## 5. Flow A — Khởi tạo dự án (manual hoặc AI)

### 5.1 Manual path (mặc định luôn dùng được)
1. New Project → nhập title + premise + genre (optional)
2. Vào thẳng Story Map trống
3. User tự tạo:
   - Storyline "Main" (auto-created khi khởi tạo)
   - Arc đầu tiên
   - Event đầu tiên
   - Character đầu tiên
   - World bible section đầu tiên (optional)

→ Sau 5 phút có khung trống đủ để bắt đầu.

### 5.2 AI-assisted path (optional)
- Sau khi New Project, user có nút **"Generate Skeleton with AI"**
- AI gen: world bible draft, 3-5 character chính, 5-10 Arc với event placeholder
- User review **toàn bộ** trong UI dạng review wizard, accept/edit/reject từng item
- Skip/cancel bất cứ lúc nào → fallback về manual path

→ AI path **không bắt buộc**. User tắt AI vẫn build skeleton thủ công được.

---

## 6. Flow B — Vòng lặp viết (manual hoặc AI)

### 6.1 Manual path

**B.1 Chọn vị trí viết**
- Từ Story Map → click Event placeholder → "Create Chapter for this Event"
- Hoặc từ Chapter list → "New Chapter" → link Event sau

**B.2 Editor 3 cột**
- **Trái:** Story Map mini (collapsible tree Storyline → Arc → Event, highlight current)
- **Giữa:** Editor rich text (TipTap)
- **Phải:** Context panel với 3 tab:
  - **Codex tab:** character + world relevant (filter manual hoặc auto theo Event link)
  - **AI tab** (nếu bật): 4 action AI (xem 6.2)
  - **Notes tab:** ghi chú tự do

**B.3 Manual workflow viết chương**
- User viết tự do trong editor
- Khi muốn ghi nhận thay đổi quan trọng: bấm **"Add Event"** (nếu phát sinh event mới), **"Update Character"** (mở character panel), **"Add World Fact"** — tất cả mở form thủ công
- Lúc nào cũng có thể edit Storyline/Arc/Event/Character từ context panel

**B.4 Finalize chapter (manual)**
- User bấm "Finalize"
- Modal yêu cầu review thủ công:
  - Liệt kê event đã link với chương — confirm
  - Hỏi: "Có character thay đổi attribute trong chương này không?" → user mở form AttributeHistory thủ công nếu có
  - Hỏi: "Tóm tắt chương này (1-3 câu)" → user gõ `manual_summary`
- Chapter mark `is_finalized=true`, `manual_summary` lưu lại
- Hết. Không cần AI.

### 6.2 AI-assisted path (overlay lên manual)

Trong editor, ngoài 4 action manual ở trên, user có 4 action AI:

| Action AI | Có thể thay bằng manual? | Cách manual |
|---|---|---|
| **Suggest next beat** | Có | User tự nghĩ và viết |
| **Continue writing** | Có | User tự gõ |
| **Rewrite selection** | Có | User tự sửa |
| **Ask about story** | Có | User tự đọc codex/chương cũ |

Khi finalize với AI bật:
- AI **đề xuất** delta (event mới, character change, world fact) dạng list
- User review từng item: accept / edit / reject
- AI có thể đề xuất `ai_summary` — user có thể giữ, sửa, hoặc thay bằng `manual_summary`

→ **Pure manual finalize vẫn hoạt động đầy đủ** kể cả khi AI off.

---

## 7. Flow C — Refactor cốt truyện (manual hoặc AI)

User có thể edit structure bất cứ lúc nào, không cần AI.

### 7.1 Manual operations
- **Reorder Arc/Event:** drag-drop trong Story Map
- **Insert Arc giữa chừng:** "+" giữa 2 Arc → form tạo Arc mới
- **Move Event sang Arc khác:** drag từ Arc này sang Arc khác
- **Split chapter:** chia 1 chương thành 2 ở vị trí cursor
- **Merge chapter:** gộp chương kế tiếp
- **Kill character:** mark `current_status="deceased"` + `last_appearance_event_id`
- **Bulk edit codex:** mở character/world detail, edit free-form
- **Conflict warning manual:** mỗi khi sửa entity, tool show "X chương đã reference entity này, review?"

### 7.2 AI assist (optional)
- AI có thể đề xuất event chuyển tiếp khi insert Arc
- AI có thể flag inconsistency (character X chết ở Arc 5 nhưng appear ở Arc 6)
- **Tất cả cảnh báo inconsistency cũng có rule-based check thủ công**, không phụ thuộc AI

---

## 8. Story Map view (core navigation)

### 8.1 Default tree view (manual-friendly)
```
Storyline: Main                                    [+ Storyline]
├─ Arc 1: Làng tân thủ          [done · 8 chap]   [+ Arc]
│   ├─ Event 1.1 ✓ (Ch.1)         [edit · move]
│   ├─ Event 1.2 ✓ (Ch.2-3)
│   └─ Event 1.3 ✓ turning (Ch.8)
├─ Arc 2: Vào tông môn          [writing · 3/6]
│   ├─ Event 2.1 ✓ (Ch.9)
│   ├─ Event 2.2 ✓ (Ch.10-11)
│   ├─ Event 2.3 (placeholder) ← current
│   └─ Event 2.4 (placeholder)
└─ Arc 3: Bí cảnh                [planned]
```

### 8.2 Filter (manual)
- Filter by character (xem journey)
- Filter by status
- Filter by storyline (khi có nhiều storyline)

### 8.3 Inline edit
- Mọi node click expand → edit form
- Right-click context menu: edit / duplicate / delete / move
- Keyboard: arrow nav, enter edit, del để xóa

---

## 9. Codex view (manual-first)

### 9.1 Character tab
- List character với search/filter
- Detail view: form edit đầy đủ mọi field
- AttributeHistory: bảng `event | attribute | old → new | source | note`
  - User có thể **tự thêm row** AttributeHistory thủ công bất cứ lúc nào
- Badge: `user-edited` / `ai-suggested` / `imported`

### 9.2 World Bible tab
- Markdown editor với section list
- Glossary entries dạng table key-value
- Tag system

### 9.3 Timeline tab
- List Event theo `narrative_order` hoặc `story_time`
- Toggle 2 trục
- Filter by character/arc

---

## 10. Editor capabilities

- **Rich text:** heading, bold, italic, blockquote, list, code (TipTap)
- **Inline reference:** `@character_name` để link character → tạo auto reference (manual paste cũng được)
- **Word count** real-time + target progress
- **Auto-save** local, manual save snapshot
- **Version history** từng chương (snapshot mỗi N phút hoặc on-demand manual)
- **Distraction-free mode** (ẩn 2 cột bên)
- **Find/replace** trong chương + toàn bộ truyện

---

## 11. AI integration spec (optional layer)

### 11.1 Toggle toàn cục
- Settings → AI: ON / OFF
- Khi OFF: mọi nút AI biến mất khỏi UI. Tool hoạt động như Plottr.
- Khi ON: nút AI xuất hiện bên cạnh action manual tương ứng

### 11.2 4 AI action (chỉ khi ON)
| Action | Hành vi | Manual fallback |
|---|---|---|
| Suggest next beat | 3 option đoạn tiếp | User tự viết |
| Continue writing | 200-500 chữ tiếp | User tự gõ |
| Rewrite selection | Phiên bản mới với prompt | User tự sửa |
| Ask about story | Q&A với context | User tự đọc codex |

### 11.3 Context tier (chỉ matter khi AI ON)
1. System prompt + style
2. World bible (relevant section)
3. Character codex (filter theo arc hiện tại)
4. Arc summary (current + previous)
5. Event list arc hiện tại
6. Last 2 chapter raw + summary các chapter trước
7. Current chapter draft + cursor

### 11.4 User-edited respect
- Field có `user_edited=true` → AI không suggest override mà không hỏi rõ
- Suggest output luôn vào diff modal để user duyệt

### 11.5 Model & cost
- Default: Claude Sonnet (qua API user-provided key)
- Settings cho phép đổi model (Sonnet/Opus/GPT-4o/local)
- API key lưu local, never leave device
- Prompt cache enable mặc định để giảm chi phí

### 11.6 Hard rule
- AI không bao giờ tự ghi vào DB. Mọi output AI đi qua user approval trước.
- AI không bao giờ tự xóa. Delete luôn là manual action.
- Mọi suggestion có thể discard. Nothing AI suggests is mandatory.

---

## 12. Done criteria (single milestone)

Tool được coi là "Done" khi tất cả check:

### 12.1 Manual completeness
- [ ] CRUD đầy đủ cho Storyline / Arc / Event / Character / World / Chapter — không cần AI
- [ ] Tạo 1 truyện từ trống → viết 10 chương (~30k chữ) **với AI tắt hoàn toàn**
- [ ] Story Map render đúng ở 5+ Arc, 30+ Event, 10+ Character
- [ ] AttributeHistory thêm/sửa/xóa thủ công work
- [ ] Drag-reorder Arc/Event không corrupt data
- [ ] Conflict warning manual rule (vd: character chết rồi appear) work

### 12.2 AI optional layer
- [ ] Toggle AI ON/OFF không phá data
- [ ] 4 AI action work với context tier hợp lệ
- [ ] Sync diff modal cho phép accept/edit/reject từng item
- [ ] AI off → tool dùng được như tool manual độc lập

### 12.3 Long-form
- [ ] Mở project có 50k+ chữ, 100+ event, 30+ character — UI vẫn responsive
- [ ] Context tier nén đúng, không vượt token budget khi AI ON
- [ ] Auto-save không lag editor

### 12.4 Reliability
- [ ] Mất mạng → tool vẫn edit được (local-first)
- [ ] Crash/reload không mất chương đang viết
- [ ] Export toàn bộ data dạng JSON/Markdown

### 12.5 Personal usability
- [ ] User (chính bạn) viết 1 truyện 50k+ chữ trong tool, không phải copy ra Word
- [ ] Mở lại sau 1 tuần vẫn dùng tiếp được, không lạc

---

## 13. Cắt scope (không build)

| Feature | Lý do |
|---|---|
| Multi-user / sharing / cloud sync | Personal tool |
| Auth / account | Single user local |
| Branch/alternative timeline | Phức tạp, không phải core |
| Plugin system | Dev-trap, hoãn |
| Marketplace template | Personal use |
| Mobile responsive | Dev trên desktop là đủ |
| Public landing page | Không bán |
| Analytics / usage tracking | Personal |
| Auto inconsistency detection ngoài rule cứng | AI optional, rule cứng đủ ở mức cơ bản |

---

## 14. Build order gợi ý (1 phase, ưu tiên critical path)

Build theo thứ tự để có thể "self-host viết truyện" sớm nhất, mỗi bước đều dùng được:

1. **Story + Chapter editor + manual save** — viết được chữ
2. **Character CRUD + Codex view** — quản lý nhân vật
3. **Storyline + Arc + Event CRUD + Story Map tree view** — có khung sườn
4. **Link Chapter ↔ Event, Event ↔ Character** — quan hệ
5. **AttributeHistory + filter timeline** — track journey
6. **World Bible markdown** — setting
7. **Refactor operations: drag-reorder, split/merge chapter, kill character** — sửa cấu trúc
8. **Manual finalize flow + manual summary** — close chương
9. **Manual conflict warning rule (chết-rồi-vẫn-xuất-hiện, attribute mâu thuẫn, ...)** — chất lượng
10. **Export JSON/Markdown** — backup
11. **Settings + AI toggle (default OFF)** — chuẩn bị AI
12. **AI: 4 action + context tier** — bật layer AI
13. **AI: sync diff modal khi finalize** — close loop
14. **AI: skeleton generator cho Phase A** — boost khởi tạo
15. **Polish: keyboard shortcut, distraction-free, version history**

→ Có thể stop bất kỳ bước nào. Sau bước 10 đã là tool dùng được hoàn chỉnh không AI. Bước 11-15 là layer AI optional.

---

## 15. Risk & decision points

### 15.1 Risk lớn nhất
**Bạn build tool 6 tháng thay vì viết truyện.** Mitigation: sau bước 4 (Story+Chapter+Character+Arc/Event link), **tự đặt mục tiêu viết 5 chương trong tool** trước khi build tiếp. Nếu không viết nổi 5 chương — vấn đề ở viết, không phải tool.

### 15.2 Decision khi gặp xung đột
- Manual path đụng AI path → ưu tiên manual
- Đẹp đụng nhanh → ưu tiên nhanh
- Generic đụng cá nhân hóa cho thể loại bạn viết → ưu tiên cá nhân hóa
- Feature mới đụng "viết tiếp truyện hiện tại" → viết tiếp truyện trước

### 15.3 Khi nào kết thúc
Khi đạt section 12 Done criteria, **đóng băng feature**, dùng tool viết truyện cho tới khi xong 1 truyện hoàn chỉnh. Mọi feature mới tính sau truyện đầu.
