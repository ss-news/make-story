# Data Model — Canonical Schema

> **Đây là single source of truth cho data model.** Khi conflict với spec.md hoặc module docs (01-04), file này thắng. Spec.md/module docs nên link tới đây cho mọi field detail.
>
> Cập nhật: sau khi resolve các open question (xem section "Decisions đã chốt" cuối file).

---

## 1. Conventions

### 1.1 Naming
- **Entity tên gọi:** `Story` = `Project` = `Manuscript` (3 từ này là synonyms). Trong code/DB **dùng `Story`**, `story_id`. Trong UI hiển thị "Truyện" (vi) / "Story" (en).
- **Field naming:** `snake_case` cho DB, `camelCase` cho TypeScript layer (mapping qua ORM).
- **ID:** UUID v4 (text trong SQLite).
- **Timestamps:** `created_at`, `updated_at` (ISO 8601 string hoặc unix ms — chọn 1 và nhất quán).

### 1.2 Soft delete
- Mọi entity có `deleted_at: timestamp | null`.
- `deleted_at != null` → ẩn khỏi mọi query mặc định, chỉ hiện trong `/archive`.
- Hard delete sau 30 ngày (background job hoặc manual từ archive).
- Khi soft delete entity có reference (vd: xoá Character đang link Event) → giữ link, mark Event với cờ "có character đã xoá", warning UI.

### 1.3 Provenance / EditFlag
Thay vì per-field `user_edited` boolean rải khắp nơi, dùng `source` enum trên các unit có thể bị AI tác động:

```ts
type Source = 'user' | 'ai_suggested' | 'imported'
```

- Áp dụng cho: `AttributeHistory.versions[].source`, `Trait.versions[].source`, `Event.source`, `Character.source` (tạo ban đầu).
- Rule: AI không bao giờ override field/version có `source = 'user'` mà không hỏi.

### 1.4 Storage
- **SQLite (better-sqlite3) qua Tauri.** FTS5 cho search, transaction cho auto-save.
- 1 file `.sqlite` per project, lưu tại `~/Library/Application Support/WebStory/projects/{story_id}.sqlite`.
- Schema versioning: bảng `_meta` lưu `schema_version`. Migration scripts chạy on app start.

### 1.5 Locale & word count
- Default locale **vi**, đơn vị đếm **"chữ"** (token ngăn cách bởi space).
- Settings cho phép switch: word (en), char (cn/jp).
- `Chapter.word_count` cache theo locale hiện tại; recompute khi đổi locale.

---

## 2. Entity Diagram

```
Story (1)
├─ Storyline (1..5, ≥1 main)
│  └─ Arc (sequential trong Storyline)
│     └─ Event (thuộc đúng 1 Arc)
│        └─ CharacterEventLink ─→ Character
├─ Chapter (flat list, có order)
│  └─ linked_event_ids[] ─→ Event
├─ Character (entity độc lập)
│  ├─ AttributeHistory: appearance, personality, background, life_status
│  ├─ Trait[] (item/skill/ability/status/other)
│  └─ Relationship[]
└─ WorldBible
   ├─ sections[]
   └─ entries[]
```

Quan hệ:
- `Event.arc_id → Arc.id` (bắt buộc)
- `Arc.storyline_id → Storyline.id` (bắt buộc)
- `Character.home_storyline_id → Storyline.id` (default = Main)
- `Event.chapter_id → Chapter.id` (nullable, planned event chưa có chapter)
- `Chapter.implicit_arc_id → Arc.id` (nullable, manual override; null thì infer)
- `Trait.character_id → Character.id`
- `CharacterEventLink (character_id, event_id)` junction

---

## 3. Entities

### 3.1 Story

```ts
interface Story {
  id: uuid
  title: string                  // tên truyện
  premise: string                // 1-3 câu mô tả
  genre: string | null           // free-form
  tone: string | null
  target_length: number | null   // số chữ mục tiêu
  status: 'drafting' | 'paused' | 'completed' | 'abandoned'

  // Settings (per-story, override app setting nếu có)
  word_count_unit: 'word' | 'char' | null  // null = dùng app default
  default_storyline_id: uuid | null         // Main storyline, set khi tạo

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}
```

**Invariants:**
- Khi tạo Story, auto-tạo 1 Storyline `is_main=true` name="Main" và set `default_storyline_id`.
- Không cho phép xoá Storyline Main khi còn Arc thuộc nó.

---

### 3.2 Storyline

```ts
interface Storyline {
  id: uuid
  story_id: uuid

  name: string                   // "Main", "Triều đình", "Ma giáo"
  description: string

  display_order: number          // thứ tự hàng trên Storyline Grid
  color: string                  // hex, unique trong story
  icon: string | null            // emoji

  is_main: boolean               // đúng 1 main per story
  is_active: boolean             // false = đã kết thúc trong story-time

  starts_at_chapter_id: uuid | null
  ends_at_chapter_id: uuid | null
  pov_character_ids: uuid[]      // POV chính (hint, không enforce)

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}
```

**Invariants:**
- Max 5 Storyline per Story (warning ở 4, error ở 6).
- Đúng 1 Storyline có `is_main=true`.
- `color` unique trong cùng story (auto-suggest màu khác khi tạo).

---

### 3.3 Arc

```ts
interface Arc {
  id: uuid
  story_id: uuid
  storyline_id: uuid

  title: string                  // "Làng tân thủ", "Tông môn tu tiên"
  description: string
  goal: string | null            // mục tiêu Arc
  setting: string                // "Thanh Khê thôn"
  location_id: uuid | null       // phase 2 (chưa có Location entity)

  order: number                  // sequential trong storyline
  status: 'planned' | 'writing' | 'done'

  // Computed (cache, recompute khi events đổi):
  chapter_start: number | null   // min chapter.order của events trong arc
  chapter_end: number | null     // max
  closing_event_id: uuid | null  // turning event của arc (= Event.is_turning)

  // Outline fields (manual)
  opening_state: string | null   // bối cảnh đầu arc
  expected_outcome: string | null

  // Summary (manual hoặc AI)
  summary: string | null
  summary_source: Source         // user / ai_suggested / imported

  color: string | null           // override storyline color
  collapsed: boolean             // UI state
  is_flashback: boolean          // optional, có thể infer từ story_time

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}
```

**Invariants:**
- `order` unique trong cùng `storyline_id`.
- `chapter_start ≤ chapter_end`.
- Arc trong cùng Storyline KHÔNG được overlap chapter range (validation error). Flashback Arc dùng `is_flashback=true`, exclude khỏi check overlap.
- `status='planned'` ⟺ chưa có event nào có `chapter_id`.

---

### 3.4 Chapter

```ts
interface Chapter {
  id: uuid
  story_id: uuid

  title: string
  order: number                  // narrative order
  content: string                // rich text (TipTap JSON serialized hoặc markdown)
  content_hash: string           // dùng cho incremental AI extract

  word_count: number             // cache theo word_count_unit hiện tại
  pov_character_id: uuid | null

  // Link backwards (reverse index, cache)
  linked_event_ids: uuid[]
  implicit_arc_id: uuid | null   // manual override; null = infer từ events

  // Finalize flow
  status: 'draft' | 'final' | 'published'
  is_finalized: boolean
  manual_summary: string | null
  ai_summary: string | null
  ai_summary_source: Source | null
  last_extracted_at: timestamp | null  // lần cuối AI extract

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}
```

**Arc của Chapter — rule infer:**
1. Nếu `implicit_arc_id` set → dùng cái đó.
2. Else: lấy Arc của event đầu tiên trong `linked_event_ids` (theo `narrative_order`).
3. Else: Arc cuối (theo `order`) của Storyline Main mà có `chapter_start ≤ this.order ≤ chapter_end`.
4. Else: Arc cuối của Storyline Main (writer đang viết tiếp).
5. Else: null (chương đầu tiên, chưa có arc nào — UI nhắc tạo Arc).

**Invariants:**
- `order` unique trong story.
- Auto-save mỗi 5s; mỗi auto-save tạo 1 snapshot trong `chapter_snapshots` (xem 3.10).

---

### 3.5 Character

```ts
interface Character {
  id: uuid
  story_id: uuid
  home_storyline_id: uuid        // default = Storyline Main

  // Định danh
  primary_name: string
  aliases: string[]              // các cách gọi khác
  pronouns: string[]             // "hắn", "nàng", "y"

  // Phân loại
  role: string                   // free-form, autocomplete từ presets VN
  faction: string | null
  tags: string[]                 // cross-cut, free-form

  // Mô tả có history (xem AttributeHistory ở 3.11)
  appearance: AttributeHistory
  personality: AttributeHistory
  background: AttributeHistory
  life_status: AttributeHistory  // alive/deceased/missing/imprisoned/transformed/sealed

  // Visual
  avatar_url: string | null
  color: string                  // hex, unique trong story

  // Tracking (cache, auto-tính từ CharacterEventLink)
  first_appearance_event_id: uuid | null
  last_appearance_event_id: uuid | null
  appearance_count: number

  // Free-form
  notes: string                  // rich text
  source: Source                 // tạo ban đầu

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}
```

**Role presets VN (autocomplete):**
"Nam chính" | "Nữ chính" | "Nam phụ" | "Nữ phụ" | "Phản diện chính" | "Phản diện phụ" | "Hỗ trợ" | "Cameo" | "Quần chúng" | "NPC". Custom string cho phép, lưu lại làm preset cho lần sau trong cùng story.

**Invariants:**
- `color` unique trong story.
- `home_storyline_id` default = `Story.default_storyline_id` (Main).
- Mọi thay đổi appearance/personality/background/life_status → tạo version mới trong AttributeHistory, không overwrite.

---

### 3.6 Trait

```ts
interface Trait {
  id: uuid
  character_id: uuid

  kind: 'item' | 'skill' | 'ability' | 'status' | 'other'
  name: string
  description: string

  // Vòng đời
  acquired_at_event_id: uuid | null  // null = innate / từ đầu
  lost_at_event_id: uuid | null      // null = vẫn còn

  // Versions (level up / nâng cấp / diễn tiến)
  versions: TraitVersion[]

  // Ownership chain (chỉ cho kind='item')
  transferred_from_character_id: uuid | null
  transferred_at_event_id: uuid | null

  icon: string | null            // emoji
  color: string | null
  tags: string[]
  notes: string

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}

interface TraitVersion {
  id: uuid
  value: string                  // "Cấp 1", "Đại thành", "trúng độc cấp 2"
  effective_from_event_id: uuid | null  // null = từ acquired_at
  reason: string
  source: Source
  created_at: timestamp
}
```

**Computed:**
- `is_active(at_event_id)`: `acquired_at <= at_event_id` AND (`lost_at == null` OR `lost_at > at_event_id`).
- `version_at(at_event_id)`: version có `effective_from <= at_event_id` lớn nhất.

---

### 3.7 Event

```ts
interface Event {
  id: uuid
  story_id: uuid
  arc_id: uuid                   // bắt buộc, thuộc đúng 1 Arc

  // Nội dung
  title: string                  // 5-15 từ
  description: string            // 1-3 câu
  source_quote: string | null    // câu/đoạn gốc

  // Vị trí trong bản thảo
  chapter_id: uuid | null        // null = planned
  paragraph_range: { start: number, end: number } | null
  is_planned: boolean            // chưa viết trong bản thảo

  // Thời gian
  narrative_order: number        // auto-tính từ chapter.order + paragraph
  story_time: StoryTime

  // Flags
  is_turning: boolean            // đúng 1 turning per arc
  is_crossover: boolean          // auto-detect, có thể manual override
  crossover_storyline_ids: uuid[]  // auto-tính từ home_storyline_id của characters
  crossover_override: boolean    // user đã manual override is_crossover

  // Phân loại
  type: 'plot' | 'character' | 'world' | 'subplot' | 'flashback' | 'other'
  importance: 'major' | 'minor' | 'background'
  tone: 'tense' | 'romantic' | 'comedic' | 'tragic' | 'mysterious' | null

  // Causality
  caused_by_event_ids: uuid[]
  leads_to_event_ids: uuid[]
  foreshadows_event_ids: uuid[]  // optional

  // Location
  location_id: uuid | null
  location_text: string          // free-form khi chưa có entity

  // Visual
  color: string | null
  icon: string | null

  // Metadata
  user_notes: string
  tags: string[]
  source: Source                 // tạo ban đầu

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}

interface StoryTime {
  type: 'absolute' | 'relative' | 'unknown'
  absolute: string | null              // "Năm Càn Long thứ 3"
  relative_to_event_id: uuid | null
  relative_offset: string | null       // "3 ngày sau"
  duration: string | null              // "1 đêm"
  sortable_value: number               // dùng để sort tự động
}
```

**Crossover detection rule:**
```
event.is_crossover = (event không có crossover_override) ?
  (số distinct home_storyline_id của characters trong event ≥ 2) :
  event.is_crossover (giữ nguyên override)
```

**Invariants:**
- `arc_id` bắt buộc, không null.
- Đúng 1 event per Arc có `is_turning=true` (set lại sẽ clear cái cũ); sync với `Arc.closing_event_id`.
- Causality không bidirectional auto: nếu A `leads_to` B, không tự thêm A vào `B.caused_by` (UI suggest reciprocal, user confirm).

---

### 3.8 CharacterEventLink

```ts
interface CharacterEventLink {
  // Composite PK: (character_id, event_id)
  character_id: uuid
  event_id: uuid

  role_in_event: 'main' | 'supporting' | 'witness' | 'mentioned' | 'affected'
  notes: string

  created_at: timestamp
}
```

**Trigger:**
- Khi insert/delete → recompute `Character.appearance_count`, `first/last_appearance_event_id`.
- Khi insert → recompute `Event.is_crossover` + `crossover_storyline_ids` (nếu không có override).

---

### 3.9 Relationship

```ts
interface Relationship {
  id: uuid
  character_id: uuid             // chủ thể
  related_character_id: uuid     // đối tượng

  type: string                   // "cha", "mẹ", "sư phụ", "bạn", "kẻ thù", "người yêu", custom
  description: string
  started_at_event_id: uuid | null  // event quan hệ bắt đầu

  // Tiến triển (optional)
  progressions: RelationshipProgression[]

  created_at: timestamp
  updated_at: timestamp
  deleted_at: timestamp | null
}

interface RelationshipProgression {
  id: uuid
  status: string                 // "bạn", "người yêu", "kẻ thù"
  changed_at_event_id: uuid
  reason: string
  created_at: timestamp
}
```

Quan hệ KHÔNG đối xứng tự động: A là "cha" của B không tự tạo B "con" của A. UI suggest reciprocal.

---

### 3.10 ChapterSnapshot (auto-save versioning)

```ts
interface ChapterSnapshot {
  id: uuid
  chapter_id: uuid
  content: string                // full snapshot của content tại thời điểm save
  word_count: number
  taken_at: timestamp
  is_manual_checkpoint: boolean  // true nếu user save tay
  checkpoint_label: string | null  // tên checkpoint nếu manual
}
```

**Rule:**
- Auto-save mỗi 5s khi user gõ.
- Giữ 50 snapshot gần nhất per chapter (rotation: xoá cái cũ nhất).
- Manual checkpoint không bị xoá bởi rotation.

---

### 3.11 AttributeHistory (universal)

```ts
interface AttributeHistory {
  current_value: string          // cache version mới nhất theo narrative_order
  versions: AttributeVersion[]
}

interface AttributeVersion {
  id: uuid
  value: string                  // mô tả tại thời điểm này
  effective_from_event_id: uuid | null  // null = từ đầu truyện
  reason: string                 // "bị thương ở event X"
  source: Source
  created_at: timestamp
}
```

**Computed:**
- `value_at(at_event_id, ordering: 'narrative'|'story')`: version có `effective_from` lớn nhất ≤ `at_event_id` theo ordering chọn. Nếu không có version nào với `effective_from <= at_event_id` → trả về version với `effective_from=null` (initial).

---

### 3.12 WorldBible

```ts
interface WorldBible {
  id: uuid                       // 1 per story
  story_id: uuid
  sections: WorldSection[]
  entries: WorldEntry[]
}

interface WorldSection {
  id: uuid
  title: string
  body_markdown: string
  order: number
}

interface WorldEntry {
  id: uuid
  section_id: uuid
  key: string                    // "Cửu Dương thần công"
  value: string
  tags: string[]
}
```

---

## 4. Computed Types (không lưu DB)

### 4.1 CharacterSnapshot — state at point T

```ts
interface CharacterSnapshot {
  character_id: uuid
  point: {
    type: 'event' | 'chapter'
    id: uuid
    ordering: 'narrative' | 'story'  // default 'story'
  }

  // Resolved values
  appearance: { value: string, version_id: uuid | null }
  personality: { value: string, version_id: uuid | null }
  background: { value: string, version_id: uuid | null }
  life_status: { value: string, version_id: uuid | null }

  // Active traits tại T
  active_traits: Array<{
    trait: Trait
    current_version: TraitVersion | null
  }>

  // Relationships active tại T
  active_relationships: Array<{
    relationship: Relationship
    current_status: string         // từ progressions hoặc relationship.type
  }>

  // Vị trí gần nhất
  last_known_location: {
    location_text: string | null
    from_event_id: uuid | null
  }
}
```

**Build function (pseudo):**
```
function getCharacterStateAt(character_id, point):
  events_before = events with (
    ordering=narrative ? narrative_order : story_time.sortable_value
  ) <= point's ordering value
  
  return {
    appearance: character.appearance.value_at(point.id, point.ordering),
    personality: ...,
    life_status: ...,
    
    active_traits: traits.filter(t =>
      events_before contains t.acquired_at_event_id (or null=innate)
      AND (t.lost_at_event_id == null OR events_before NOT contains t.lost_at_event_id)
    ).map(t => ({ trait: t, current_version: t.version_at(point.id) })),
    
    active_relationships: relationships.filter(r =>
      r.started_at_event_id == null OR events_before contains r.started_at_event_id
    ).map(r => ({ relationship: r, current_status: latest_progression_before(r, point) })),
    
    last_known_location: latest_event_with_location_in(events_before, character_links).location
  }
```

**Default ordering:** `story` (về mặt thế giới truyện). Toggle sang `narrative` khi cần continuity check khi viết.

---

## 5. Indexes & Search

### 5.1 SQLite indexes
```sql
CREATE INDEX idx_arc_storyline_order ON Arc(storyline_id, order);
CREATE INDEX idx_event_arc ON Event(arc_id, narrative_order);
CREATE INDEX idx_event_chapter ON Event(chapter_id);
CREATE INDEX idx_chapter_story_order ON Chapter(story_id, order);
CREATE INDEX idx_character_story ON Character(story_id);
CREATE INDEX idx_link_event ON CharacterEventLink(event_id);
CREATE INDEX idx_link_character ON CharacterEventLink(character_id);
```

### 5.2 FTS5 virtual tables (cho Cmd+K search)
```sql
CREATE VIRTUAL TABLE chapter_fts USING fts5(
  chapter_id UNINDEXED, title, content, tokenize='unicode61'
);
CREATE VIRTUAL TABLE character_fts USING fts5(
  character_id UNINDEXED, primary_name, aliases, notes,
  appearance_value, personality_value, tokenize='unicode61'
);
CREATE VIRTUAL TABLE event_fts USING fts5(
  event_id UNINDEXED, title, description, source_quote, tokenize='unicode61'
);
```
Trigger để keep sync với entity tables.

---

## 6. Invariants — danh sách rule cứng

| ID | Rule | Enforce ở |
|---|---|---|
| I1 | Mỗi Story có ≥1 Storyline, đúng 1 `is_main=true` | Trigger insert/update |
| I2 | Max 5 Storyline / Story | Validation tạo mới |
| I3 | Color unique trong Story (Storyline + Character) | Validation + auto-suggest |
| I4 | Arc trong cùng Storyline không overlap chapter range (trừ flashback) | Validation update |
| I5 | Event.arc_id NOT NULL | Schema constraint |
| I6 | ≤1 turning event per Arc | Trigger update Event.is_turning |
| I7 | Event.is_crossover auto-recompute khi character link đổi (trừ khi có crossover_override) | Trigger |
| I8 | Trait time-correct: hover hoặc snapshot chỉ show traits với `acquired ≤ T < lost` | Computed function |
| I9 | AI không override field/version có `source='user'` mà không hỏi | Application layer |
| I10 | Soft delete only trong UI thường; hard delete chỉ qua /archive | Application layer |
| I11 | Causality không bidirectional auto | Application layer |
| I12 | Auto-save không mất quá 5s gõ phím | Application layer + transaction |

---

## 7. Conflict warning rules (cho [spec.md mục 9 build order step 9](spec.md))

Rule cụ thể chạy khi user save edit / mở chapter / open Arc:

| Rule | Trigger | Severity |
|---|---|---|
| **R-DEAD-APPEAR** | Character có version `life_status='deceased'` ở event X, lại link vào event sau X (ordering=story) mà không có version revert | Warning |
| **R-TRAIT-LOST-USED** | Description hoặc trait version reference trait đã `lost_at` trước event hiện tại | Warning |
| **R-ARC-OVERLAP** | Arc trong cùng Storyline có chapter range giao nhau (không phải flashback) | Error (block save) |
| **R-EVENT-NO-CHAR** | Event lưu mà không có character nào | Info ("có chắc không?") |
| **R-CHAPTER-NO-ARC** | Chapter có content nhưng infer-arc trả null | Info |
| **R-TURNING-LAST** | Turning event của Arc không phải event cuối (theo narrative_order) trong Arc | Warning |
| **R-CROSSOVER-LATE** | Event có character với `home_storyline_id` chưa start (Storyline.starts_at_chapter > current chapter) | Warning |
| **R-CONTRADICT-ATTR** | 2 versions appearance trong khoảng [event A, event B] không có `effective_from` ở giữa, mô tả mâu thuẫn (cần AI để detect — fallback rule cứng: 2 versions có overlap effective range) | Warning (AI khi ON) |
| **R-RELATIONSHIP-DEAD** | Relationship "started_at" event mà related_character đã deceased trước đó | Error |

UI hiển thị: badge số warning trên Story Map / Character / Event. Click → modal list issues, mỗi cái có "Đến" (jump tới entity), "Bỏ qua rule này", "Đánh dấu intentional".

---

## 8. Decisions đã chốt

| # | Quyết định | Câu hỏi cũ |
|---|---|---|
| D1 | Word count default = "chữ" (token tách bởi space) cho VN; settings cho phép đổi sang word/char | Open Q editor 1.2 |
| D2 | 1 manuscript tại 1 thời điểm; switch project qua dropdown; multi-window Tauri-level nếu cần | Open Q editor 1.1 |
| D3 | Bỏ `attributes` key-value của spec.md; dùng AttributeHistory + Trait + tags[] làm flexibility | Conflict spec vs 02-char |
| D4 | Storage = SQLite + Tauri (FTS5, transaction); export JSON cho portability | Site-arch 5.2 |
| D5 | Crossover: thêm `Character.home_storyline_id` (default = Main); rule auto-detect dựa vào field này | Open Q timeline crossover |
| D6 | Character state at point T = first-class operation; thêm `life_status: AttributeHistory` (thay `current_status` string đơn); UI Snapshot panel; default ordering = story_time | Gap user nêu |
| D7 | Arc dùng `title` (không phải `name`); Storyline dùng `name` | Conflict spec vs 04-timeline |
| D8 | Event dùng `is_turning` (không phải `is_turning_event`); pair với `is_crossover` | Conflict spec vs 03-event |
| D9 | EditFlag dùng `source: 'user'\|'ai_suggested'\|'imported'` per-version, không per-field boolean | Spec 4.8 |
| D10 | Chapter↔Arc: thêm `Chapter.implicit_arc_id` (manual override); fallback infer rule 5 bước | Gap không có chapter→arc trực tiếp |

---

## 9. Còn treo (decide khi build tới)

- **Sub-arc / nested Arc** — hiện tại refuse, hướng user tách Arc anh em (timeline R7). Confirm khi build mục Story Map.
- **Storyline merge / split** — hiện tại không support; "Storyline cũ kết, Storyline mới bắt đầu" là workaround. Re-evaluate sau khi viết 5 chương test.
- **Crossover cấp Arc** (1 Arc thuộc nhiều Storyline) — hiện tại NO, chỉ event level. Re-evaluate khi gặp use case "Đại chiến" có cả 3 phe.
- **Multi-chapter event** — hiện tại 1 event có `chapter_id` đơn + `paragraph_range`. Mở rộng sang `chapter_range: [start_chapter_id, end_chapter_id]` khi cần.
- **Event template** (Hero's Journey, Save the Cat) — hoãn, không essential.
- **Custom field cho character genre-specific** (vd: "Cảnh giới tu luyện") — dùng `Trait kind=status` (level via versions). Nếu bất tiện sẽ revisit.
- **Avatar variations theo phase** (trẻ/già/biến thân) — hiện tại 1 avatar per character. Phase 2.

---

## 10. Migration / schema versioning

```ts
// _meta table
{ key: 'schema_version', value: '1' }
```

- Mỗi lần đổi schema → bump version, viết migration script `migrations/v1_to_v2.sql`.
- Migration runner chạy on app start, idempotent.
- Backup file `.sqlite` trước khi migrate.
- Export JSON cũng có `schema_version` để import phát hiện cần migrate.

---

## 11. Quan hệ với các doc khác

- **spec.md** — phần "4. Data model" trong spec.md sẽ rút gọn còn high-level entity list + link tới file này cho field detail.
- **02-character.md / 03-event.md / 04-timeline.md** — mọi field definition trong các file này phải khớp file này. Khi conflict, update các file đó.
- **01-editor.md** — Chapter shape ở mục 1.2 phải khớp 3.4 trong file này.
- **05-site-architecture.md** — section 4.1 Local data store update path: SQLite + Tauri (đã chốt D4).
