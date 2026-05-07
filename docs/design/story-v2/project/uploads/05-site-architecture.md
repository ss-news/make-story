# Site Architecture — Personal Tool

> Tài liệu này mô tả app shell, navigation, settings, tech stack cho **personal local-first tool**. Không có auth, không có billing, không có landing page marketing.
> **Schema canonical:** [06-data-model.md](06-data-model.md). Khi conflict về data/storage → 06 thắng.
> Tham khảo [spec.md](spec.md) cho master spec, flow, build order.

## 1. Sitemap

```
Web Story (single-user, local-first)
│
├── / ............................. Project list (dashboard)
├── /new .......................... Tạo project mới (wizard, optional AI)
│
├── /p/:id ........................ Project workspace
│   ├── ?tab=editor ............... Editor 3-cột (default khi mở chapter)
│   ├── ?tab=story-map ............ Story Map (Storyline → Arc → Event)
│   ├── ?tab=characters ........... Character grid
│   ├── ?tab=relationships ........ Relationship Graph (center = main character)
│   ├── ?tab=events ............... Event list
│   ├── ?tab=world ................ World Bible
│   └── ?tab=settings ............. Project settings
│
├── /p/:id/character/:cid ......... Character detail (deep link)
├── /p/:id/relationships?center=:cid Relationship Graph (deep link, optional center)
├── /p/:id/event/:eid ............. Event detail (deep link)
├── /p/:id/storyline/:sid ......... Storyline detail
├── /p/:id/arc/:aid ............... Arc detail
├── /p/:id/chapter/:chid .......... Editor jump to chapter
│
├── /archive ...................... Archive (project / items đã xóa)
├── /settings ..................... App-level settings (AI toggle, API key, theme, …)
└── /help ......................... Shortcut cheatsheet
```

**Không có:** `/login`, `/signup`, `/forgot-password`, `/billing`, `/pricing`, `/about` — personal tool, không cần.

## 2. Navigation & layout chung

### 2.1 App shell

```
┌────────────────────────────────────────────────────────────────┐
│ [Logo]  [Project: Truyện X ▼]               [⚙️ App Settings] │ ← Top bar
├────┬───────────────────────────────────────────────────────────┤
│    │                                                            │
│ 📝 │                                                            │
│ 🌳 │                                                            │
│ 👤 │                  Main content area                         │
│ ⏱  │                  (route content)                           │
│ 🌍 │                                                            │
│    │                                                            │
│ ⚙️  │                                                            │
└────┴───────────────────────────────────────────────────────────┘
  ↑
  Module navigation (icon rail, 56px)
```

**Top bar (48px):**
- Logo (click → project list)
- Project switcher (dropdown, list project, "Tạo mới")
- App Settings button (AI toggle, theme, …)

**Left rail (icon-only, 56px):**
- 📝 Editor
- 🌳 Story Map
- 👤 Characters
- ⏱ Events
- 🌍 World Bible
- ─── divider
- ⚙️ Project settings

Hover → tooltip. Click → switch tab.

### 2.2 Routing & state
- URL phản ánh state (deep link được)
- Tab switching không reload (SPA)
- Filter/sort lưu trong URL query
- Local-first: routing chỉ là client-side, không có server-side rendering yêu cầu auth

### 2.3 Breadcrumb
- Tab name + sub-context (vd: "Story Map → Arc: Tông môn tu tiên → Event: Bái sư")
- Back button khi vào detail panel

## 3. Các trang ngoài modules

### 3.1 Project list (`/`)
- Grid card mỗi project: title, premise ngắn, word count, last edited
- "+ New project" → wizard (mục 3.2)
- Right-click card: rename / duplicate / archive / export

### 3.2 New project wizard (`/new`)
- **Manual path:** chỉ cần title → vào thẳng workspace với Storyline "Main" trống
- **AI-assisted path** (nếu AI ON): nhập premise + genre + tone + target_length → AI generate skeleton (world bible draft, 3-5 character, 5-10 Arc) → user review từng item → lưu

### 3.3 Project workspace (`/p/:id`)
- App shell + module tab content
- Editor mode = 3 cột (story map mini / editor / context panel)
- Các tab khác = single column với detail panel slide-in khi click item

### 3.4 Archive (`/archive`)
- List soft-deleted: project, chapter, character, event, …
- Restore / hard delete
- Auto hard-delete sau 30 ngày

### 3.5 App settings (`/settings`)

| Section | Settings |
|---|---|
| **General** | Theme (light/dark/system), language (vi/en), default word count mode (char/word) |
| **AI** | AI ON/OFF toggle, model select (Claude Sonnet/Opus/GPT-4o/local), API key input (lưu local), prompt cache enable, max token budget per request |
| **Editor** | Auto-save interval, font, font size, line height, distraction-free shortcut |
| **Backup** | Export all data (JSON/Markdown), import data, auto-backup folder path |
| **Shortcuts** | View/customize keyboard shortcuts |
| **Advanced** | Reset all, clear cache, debug log |

### 3.6 Help (`/help`)
- Keyboard shortcut cheatsheet
- Link tới spec.md / module docs (nếu host doc cùng app)

## 4. System features

### 4.1 Local data store
- **Storage:** SQLite (better-sqlite3) qua Tauri — đã chốt ([06 D4](06-data-model.md#8-decisions-đã-chốt))
- **FTS5** virtual tables cho full-text search (chapter content, character description, event title/description)
- **Location:** `~/Library/Application Support/WebStory/projects/{story_id}.sqlite` (macOS), tương đương trên Windows/Linux
- **Per project:** 1 file `.sqlite` riêng, portable, copy-paste được sang máy khác
- **Auto-backup:** ChapterSnapshot trong DB ([06 §3.10](06-data-model.md#310-chaptersnapshot--auto-save-versioning)) + export JSON định kỳ ra folder người dùng chọn

### 4.2 Search (toàn project)
- `Cmd+K` quick search: character, event, chapter, world entry
- Fuzzy matching trên primary_name + alias + tag
- Prefix filter: `c:` character, `e:` event, `ch:` chapter, `w:` world

### 4.3 Notifications & feedback
- Toast notification cho: save success, AI suggest sẵn sàng, conflict warning
- Status bar dưới cùng: word count tổng + chương hiện tại + AI status
- Không có notification center / inbox (personal tool, không cần)

### 4.4 Keyboard shortcuts (core)

| Shortcut | Action |
|---|---|
| `Cmd+S` | Manual save snapshot |
| `Cmd+K` | Quick search |
| `Cmd+\` | Toggle context panel |
| `Cmd+E` | Switch tab Event (in editor) |
| `Cmd+P` | Switch tab Character |
| `Cmd+Shift+E` | Tạo event từ selection |
| `Cmd+Shift+P` | Tạo character từ selection |
| `Cmd+Enter` | AI continue (nếu AI ON) |
| `Cmd+Shift+S` | AI suggest beat |
| `Cmd+/` | Ask about story (AI) |
| `Cmd+B/I` | Bold / Italic |
| `Cmd+Z` / `Cmd+Shift+Z` | Undo / Redo |

### 4.5 Distraction-free mode
- `Cmd+.` → ẩn 2 cột bên, full-screen editor
- Soft-fade UI elements khác

### 4.6 Auto-save & versioning
- Auto-save mỗi 5s khi gõ
- Snapshot 50 phiên bản gần nhất / chương
- Version history view: thời gian + diff view (optional)

### 4.7 Export & import
- **Export per project:**
  - JSON (toàn bộ data)
  - Markdown (chapter content + codex)
  - DOCX (chapter only)
- **Import:**
  - JSON (restore từ backup)
  - DOCX/TXT/MD (import chapter content, parse heading)

## 5. Tech stack

### 5.1 Frontend
- **Framework:** Next.js + TypeScript
- **Styling:** Tailwind + Shadcn (optional, có thể skip ở core)
- **Editor:** TipTap (rich text, extensible)
- **State:** Zustand hoặc React Query — dev tự chốt
- **Icon:** Lucide

### 5.2 Storage
- **Local-first:** SQLite (better-sqlite3) — đã chốt ([06 D4](06-data-model.md#8-decisions-đã-chốt))
- **FTS5** virtual tables cho search (chapters, characters, events) — index theo Vietnamese-aware tokenizer
- **Không có server DB** — tool chạy 100% client (Tauri đóng gói desktop app)
- **Migration:** schema version trong bảng `_meta`; mỗi version có up/down script
- **Backup:** ChapterSnapshot trong DB + export JSON định kỳ vào folder người dùng chọn

### 5.3 AI integration (optional)
- **Default model:** Claude Sonnet qua Anthropic SDK
- **Settings cho phép đổi:** Sonnet / Opus / GPT-4o / local model (Ollama)
- **API key:** lưu local trong settings, never leave device
- **Prompt caching:** enable mặc định (giảm 80% cost cho long-form context)

### 5.4 Build & deploy
- **Dev:** `next dev` (frontend) + Tauri dev shell — local
- **Production:** Tauri — đóng gói thành app desktop (đã chốt, [06 D4](06-data-model.md#8-decisions-đã-chốt))
- **Không deploy lên public web** — không có user khác, không cần

## 6. Performance & limits

| Metric | Target |
|---|---|
| Editor keystroke → render | < 50ms ngay cả với 20k chữ/chương |
| Story map render | < 200ms với 30 Arc, 100 Event |
| Character grid | < 200ms với 200 character |
| Quick search response | < 100ms |
| Auto-save | Non-blocking, không lag editor |
| Project size | Hỗ trợ 200k+ chữ, 100+ event, 50+ character |

## 7. Privacy & data ownership
- Toàn bộ data lưu **local trên máy user**
- Không có server, không có cloud sync (trừ khi user tự build sau)
- AI request: gửi qua API key của user, response không log
- Export full data bất cứ lúc nào (JSON/Markdown)
- Xóa project = xóa file local, không có "deleted from server" lo ngại

## 8. Risk & decision điểm chốt

### 8.1 Dev-trap warning
Personal tool dễ bị scope creep. Build theo critical path trong [spec.md mục 14](spec.md#14-build-order-gợi-ý-1-phase-ưu-tiên-critical-path), **dừng lại sau bước 4 để viết 5 chương thử trước khi build tiếp**.

### 8.2 Khi nào "Done"
Đạt [spec.md → Done criteria mục 12](spec.md#12-done-criteria-single-milestone). Sau đó **đóng băng feature**, dùng tool viết tới khi xong 1 truyện thật.

### 8.3 Cost AI
Personal use, ước tính:
- 100k chữ/tháng với prompt cache: $20-50/tháng (Claude Sonnet)
- Có thể giảm bằng local model (Qwen 2.5 / Llama) — chất lượng tiếng Việt yếu hơn
- API key của user, dev không phải lo billing infrastructure
