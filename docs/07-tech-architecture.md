# Tech Architecture — Go + React

> Tài liệu này thay thế phần **5. Tech stack** của [05-site-architecture.md](05-site-architecture.md) sau khi pivot từ Tauri/Rust sang Go.
> **Schema canonical:** [06-data-model.md](06-data-model.md). Khi conflict về data → 06 thắng.
> **Sản phẩm/flow:** [spec.md](spec.md). Khi conflict về flow → spec.md thắng.
> **Sitemap & UI nav:** [05-site-architecture.md mục 1–4](05-site-architecture.md). File này chỉ lo backend, frontend, packaging, build.

---

## 0. Quyết định stack (TL;DR)

| Layer | Chọn | Lý do |
|---|---|---|
| **Packaging** | **Wails v2** (Go + WebView2/WKWebView + React) | Tương đương Tauri nhưng cho Go. Single binary, không cần Node runtime production. Bindings tự sinh TS từ Go. |
| **Backend** | Go 1.23+ | User đã cài đủ skill Go. Pure Go, deploy gọn. |
| **Frontend** | Vite + React 18 + TypeScript | Đổi từ Next.js sang Vite-React vì tool chạy trong WebView, không cần SSR/routing server. |
| **UI** | Tailwind + shadcn/ui + Lucide | Skill đã cài. Bám aesthetic iA Writer / Bear (xem design `story-v2`). |
| **Editor** | TipTap (giữ nguyên) | Rich text, ProseMirror-based, link mention dễ tích hợp. |
| **State** | Zustand + TanStack Query | Zustand cho UI state; TanStack Query cho server state (Wails calls) + cache invalidation. |
| **Storage** | SQLite — `modernc.org/sqlite` (pure Go, có FTS5) | Pure Go, no CGO → cross-compile dễ, build sạch. Nếu cần benchmark hơn, fallback `mattn/go-sqlite3` (CGO). |
| **Migration** | Embedded `*.sql` files qua `embed.FS` + runner tự viết | Đơn giản hơn `golang-migrate` cho personal tool. |
| **DI** | `samber/do` | Lightweight, không reflect-heavy như `uber-fx`. Phù hợp scale nhỏ. |
| **Logging** | `log/slog` (stdlib) + handler text/json switch theo env | Stdlib, không cần extra dep. |
| **Error** | `samber/oops` | Chain error + context tags, log đẹp. |
| **Util** | `samber/lo`, `samber/mo` | Functional helpers, Option/Result types. |
| **Test** | `stretchr/testify` + table-driven + `goleak` | Theo skill đã cài. |
| **AI client** | Anthropic Go SDK + HTTP fallback cho OpenAI/Ollama | API key user-provided, never leave device. |
| **Config** | `flag` stdlib + JSON file ở `~/Library/Application Support/WebStory/config.json` | Personal tool, không cần Viper. |

---

## 1. High-level architecture

```
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         WAILS v2 DESKTOP APP (1 binary)                       ║
║                                                                               ║
║   ┌─────────────────────────────────────────────────────────────────────┐     ║
║   │                  FRONTEND (WebView, Vite + React)                   │     ║
║   │                                                                     │     ║
║   │   React 18 + TS  •  Tailwind + shadcn/ui  •  Lucide                 │     ║
║   │   TipTap (editor)  •  Zustand (UI)  •  TanStack Query (server)      │     ║
║   │                                                                     │     ║
║   │   Routes (react-router):                                            │     ║
║   │     /  /new  /p/:id?tab=…  /archive  /settings  /help               │     ║
║   │                                                                     │     ║
║   │   ┌─────────┬───────────┬───────────┬────────┬────────┬──────────┐  │     ║
║   │   │ Editor  │ Story Map │ Character │ Event  │ Rels   │ World    │  │     ║
║   │   └─────────┴───────────┴───────────┴────────┴────────┴──────────┘  │     ║
║   │                                                                     │     ║
║   │            ▲ TanStack Query cache  │ Wails-generated TS bindings    │     ║
║   └────────────┼──────────────────────┼──────────────────────────────────┘    ║
║                │                      ▼                                       ║
║   ┌─────────────────────────────────────────────────────────────────────┐     ║
║   │                  GO BACKEND (Wails app process)                     │     ║
║   │                                                                     │     ║
║   │   ┌──────── App layer (Wails bindings) ────────┐                    │     ║
║   │   │  StoryAPI  CharacterAPI  EventAPI          │  exposed → JS      │     ║
║   │   │  ChapterAPI  StorylineAPI  WorldAPI        │  via context-bound │     ║
║   │   │  AIAPI  SearchAPI  ImportExportAPI         │  struct methods    │     ║
║   │   └────────────────┬───────────────────────────┘                    │     ║
║   │                    ▼                                                │     ║
║   │   ┌──────── Service layer (use cases) ─────────┐                    │     ║
║   │   │  Story / Character / Event / Chapter / …   │                    │     ║
║   │   │  ConflictRules  ContextBuilder  Finalize   │                    │     ║
║   │   └────────────────┬───────────────────────────┘                    │     ║
║   │                    ▼                                                │     ║
║   │   ┌──────── Domain (entities + invariants) ────┐                    │     ║
║   │   │  Story Storyline Arc Event Chapter         │  schema = 06       │     ║
║   │   │  Character Trait Relationship WorldBible   │                    │     ║
║   │   │  AttributeHistory CharacterSnapshot        │                    │     ║
║   │   └────────────────┬───────────────────────────┘                    │     ║
║   │                    ▼                                                │     ║
║   │   ┌──────── Adapters (interfaces + impl) ──────┐                    │     ║
║   │   │  Repo (SQLite)  Search (FTS5)  Migrator    │                    │     ║
║   │   │  AIClient (Claude/OpenAI/Ollama)  FS       │                    │     ║
║   │   └────────────────┬───────────────────────────┘                    │     ║
║   └────────────────────┼────────────────────────────────────────────────┘     ║
╚════════════════════════╪══════════════════════════════════════════════════════╝
                         │
       ┌─────────────────┼──────────────────────┬──────────────────────┐
       ▼                 ▼                      ▼                      ▼
 ┌───────────┐    ┌──────────────┐      ┌─────────────────┐   ┌──────────────┐
 │  SQLite   │    │ User backup  │      │ AI provider     │   │ User home    │
 │  per      │    │ folder       │      │ (user API key)  │   │ FS — import  │
 │  project  │    │ JSON / MD    │      │ Claude / GPT /  │   │ DOCX/MD/TXT  │
 │  + FTS5   │    │ snapshots    │      │ Ollama (local)  │   │              │
 └───────────┘    └──────────────┘      └─────────────────┘   └──────────────┘

 macOS:   ~/Library/Application Support/WebStory/projects/{story_id}.sqlite
 Linux:   ~/.local/share/WebStory/projects/{story_id}.sqlite
 Windows: %APPDATA%\WebStory\projects\{story_id}.sqlite
```

---

## 2. Backend (Go) — project layout

Bám theo [`samber/cc-skills-golang@golang-project-layout`](../.agents/skills/golang-project-layout/SKILL.md). Internal-first, không export package mà chính app không dùng ngoài.

```
web-story/
├── cmd/
│   └── web-story/
│       └── main.go                   Wails entry, container init, run app
│
├── internal/
│   ├── app/                          Wails binding adapters
│   │   ├── story_api.go              method nhận từ JS, gọi service
│   │   ├── character_api.go
│   │   ├── event_api.go
│   │   ├── chapter_api.go
│   │   ├── storyline_api.go
│   │   ├── world_api.go
│   │   ├── ai_api.go                 stream response qua Wails events
│   │   ├── search_api.go
│   │   ├── importexport_api.go
│   │   └── dto.go                    DTO ↔ domain mapping (snake/camel)
│   │
│   ├── domain/                       entity + value object + invariants
│   │   ├── story/
│   │   ├── storyline/
│   │   ├── arc/
│   │   ├── chapter/
│   │   ├── event/
│   │   ├── character/                gồm AttributeHistory, Trait
│   │   ├── relationship/
│   │   ├── world/
│   │   └── shared/                   Source enum, ID, StoryTime, errors
│   │
│   ├── service/                      use case (1 file = 1 service)
│   │   ├── story_service.go
│   │   ├── character_service.go
│   │   ├── event_service.go
│   │   ├── chapter_service.go
│   │   ├── storyline_service.go
│   │   ├── conflict_service.go       R-DEAD-APPEAR, R-ARC-OVERLAP… (06 §7)
│   │   ├── snapshot_service.go       CharacterSnapshot at point T (06 §4.1)
│   │   ├── finalize_service.go       Flow B.4 + AI delta merge
│   │   ├── context_builder.go        7 tier cho AI (spec 11.3)
│   │   └── import_export_service.go
│   │
│   ├── repository/                   interface ở domain, impl ở đây
│   │   ├── sqlite/
│   │   │   ├── story_repo.go
│   │   │   ├── character_repo.go
│   │   │   ├── event_repo.go
│   │   │   ├── …
│   │   │   ├── tx.go                 transaction helper
│   │   │   └── conn.go               *sql.DB pool, pragmas
│   │   └── search/
│   │       └── fts5_search.go        chapter_fts, character_fts, event_fts
│   │
│   ├── ai/
│   │   ├── client.go                 interface
│   │   ├── anthropic.go              Claude SDK client
│   │   ├── openai.go                 OpenAI HTTP
│   │   ├── ollama.go                 local model HTTP
│   │   └── cache.go                  prompt-cache hint builder
│   │
│   ├── migration/
│   │   ├── runner.go                 đọc embed.FS, apply theo schema_version
│   │   └── migrations/
│   │       ├── 001_init.sql
│   │       └── 002_xxx.sql
│   │
│   ├── config/
│   │   ├── config.go                 struct + load/save JSON
│   │   └── paths.go                  per-OS data dir
│   │
│   ├── logging/
│   │   └── logger.go                 slog setup, level, file rotation
│   │
│   └── di/
│       └── container.go              samber/do — provide tất cả service/repo
│
├── frontend/                         (xem mục 3)
│
├── build/                            Wails build assets (icon, info.plist)
├── wails.json                        Wails config
├── go.mod  go.sum
└── Makefile                          dev / build / test / lint
```

**Quy ước:**
- `internal/domain/*` không phụ thuộc `repository`, `service`, hay package ngoài chuẩn — chỉ chứa entity + invariant pure.
- Service phụ thuộc `repository` qua interface (định nghĩa cùng package domain hoặc service, impl ở `repository/sqlite`). Theo "accept interfaces, return structs".
- App layer (`internal/app`) là adapter mỏng: parse DTO → gọi service → trả DTO. Không có business logic.
- Errors dùng `samber/oops` để gắn context (`oops.With("story_id", id).Wrapf(err, "load story")`).

---

## 3. Frontend (React) — project layout

```
frontend/
├── index.html
├── vite.config.ts
├── tailwind.config.ts
├── tsconfig.json
├── package.json
├── src/
│   ├── main.tsx                      bootstrap
│   ├── App.tsx                       router + theme + AI toggle providers
│   │
│   ├── api/
│   │   ├── bindings/                 ← Wails generates here (auto, gitignored)
│   │   ├── client.ts                 thin wrapper, error normalisation
│   │   └── queries/                  TanStack Query hooks per entity
│   │       ├── useCharacter.ts
│   │       ├── useEvents.ts
│   │       └── …
│   │
│   ├── routes/                       React Router routes = page components
│   │   ├── Dashboard.tsx              "/"
│   │   ├── NewProject.tsx             "/new"
│   │   ├── Workspace.tsx              "/p/:id" (shell + tabs)
│   │   ├── tabs/
│   │   │   ├── EditorTab.tsx
│   │   │   ├── StoryMapTab.tsx
│   │   │   ├── CharactersTab.tsx
│   │   │   ├── RelationshipsTab.tsx
│   │   │   ├── EventsTab.tsx
│   │   │   ├── WorldBibleTab.tsx
│   │   │   └── ProjectSettingsTab.tsx
│   │   ├── Archive.tsx
│   │   ├── AppSettings.tsx
│   │   └── Help.tsx
│   │
│   ├── modules/                      module-scoped components/logic
│   │   ├── editor/                   TipTap setup, mention, suggestions
│   │   ├── storymap/                 tree, arc-map, storyline-grid, dag
│   │   ├── character/                grid, detail, attribute-history form
│   │   ├── event/                    list, detail panel, causality picker
│   │   ├── relationship/             force-directed graph
│   │   ├── world/                    markdown sections + glossary
│   │   ├── ai/                       diff modal, suggest panel, context viewer
│   │   └── search/                   Cmd+K palette
│   │
│   ├── components/ui/                shadcn primitives (button, dialog, …)
│   ├── components/                   shared composite (StatusBar, TopBar, Rail…)
│   │
│   ├── state/                        Zustand stores
│   │   ├── useUIStore.ts             theme, ai toggle, current project, sel
│   │   ├── useEditorStore.ts         draft buffer, cursor, dirty flag
│   │   └── useStoryMapStore.ts       expand state, filters
│   │
│   ├── lib/
│   │   ├── classnames.ts
│   │   ├── word-count.ts             vi "chữ" + en word + cn char
│   │   ├── narrative-order.ts
│   │   └── kbd.ts                    keyboard shortcuts registry
│   │
│   ├── styles/
│   │   ├── globals.css               Tailwind directives + CSS vars (theme)
│   │   ├── tokens.css                paper/ink/muted/hairline/accent (xem design)
│   │   └── tiptap.css
│   │
│   └── i18n/
│       ├── vi.json
│       └── en.json
└── public/
    └── fonts/                        Lora, JetBrains Mono, Inter (self-host)
```

**Bám design `story-v2`:**
- Tokens (`paper`, `ink`, `muted`, `hairline`, `accent`) lấy từ design CSS gốc (`docs/design/story-v2/project/styles.css`).
- Màu Storyline: Main = terracotta `oklch(58% 0.12 30)`, Triều đình = ink-blue, Ma giáo = plum.
- Shell: top bar 48px + left rail 56px + status bar 24px (xem [design Web Story.html:166-233](design/story-v2/project/Web%20Story.html)).
- Component map từ design → React thực:
  - `canvas.jsx` → `modules/storymap/ArcMap.tsx`
  - `storymap.jsx` → `modules/storymap/Tree.tsx` + `Grid.tsx` + `ArcDetail.tsx`
  - `editor.jsx` → `modules/editor/Editor.tsx` + `routes/tabs/EditorTab.tsx`
  - `characters.jsx` → `modules/character/Grid.tsx` + `Detail.tsx`
  - `relgraph.jsx` → `modules/relationship/ForceGraph.tsx`
  - `events.jsx` → `modules/event/List.tsx` + `Detail.tsx`
  - `create-modal.jsx` → `components/CreateModal.tsx` (universal create với prefill)
  - `misc.jsx` → `routes/AppSettings.tsx` + `routes/tabs/WorldBibleTab.tsx`
  - `projects.jsx` → `routes/Dashboard.tsx`

---

## 4. IPC: cách Frontend gọi Backend

Wails sinh TS bindings từ struct method Go có signature `(ctx, args…) (result, error)`. Frontend gọi như async function.

```
   React component
        │
        │  const events = await api.event.list(storyId)
        ▼
   src/api/bindings/EventAPI.ts        ← Wails-generated, gitignored
        │
        │  window.runtime.Call('event_api.List', storyId)
        ▼
   Go: internal/app/event_api.go
        EventAPI.List(ctx, storyId) ([]EventDTO, error)
        │
        │  → service.EventService.List(ctx, storyId)
        ▼
   Go: internal/service/event_service.go
        │
        │  → repo.EventRepository.ListByStory(ctx, tx, storyId)
        ▼
   Go: internal/repository/sqlite/event_repo.go
        SELECT … FROM event WHERE story_id=? AND deleted_at IS NULL
```

**Streaming (AI):**
```
React → api.ai.continueWriting(prompt, ctx)
   ↓
Go AIAPI streams chunks via wails runtime.EventsEmit("ai:chunk:<reqId>", chunk)
   ↓
React subscribes once: runtime.EventsOn("ai:chunk:<reqId>", onChunk)
```

**Cache invalidation:**
- TanStack Query keys khớp với entity: `['event', storyId]`, `['character', storyId, charId]`.
- Sau mutation thành công, service emit Wails event `repo:invalidate` với pattern → React refresh tương ứng.

---

## 5. Storage layer

### 5.1 Driver
`modernc.org/sqlite` — pure Go, đã hỗ trợ FTS5. Không CGO → cross-compile thuận lợi (macOS arm64/x64, Linux, Windows từ 1 máy).

```go
db, err := sql.Open("sqlite", dsn)
// PRAGMA mặc định bật khi mở:
//   journal_mode=WAL
//   synchronous=NORMAL
//   foreign_keys=ON
//   busy_timeout=5000
//   temp_store=MEMORY
```

### 5.2 1 file SQLite per project
Theo [06 §1.4](06-data-model.md#14-storage). Mỗi project là `{story_id}.sqlite` riêng — copy-paste portable.

### 5.3 Schema migration
- Migrations dạng `001_init.sql`, `002_*.sql` nhúng qua `embed.FS`.
- Bảng `_meta(key TEXT PRIMARY KEY, value TEXT)` lưu `schema_version`.
- Runner: lock file → BEGIN → apply tuần tự bằng order số → bump version → COMMIT. Backup `.sqlite` trước khi migrate.
- Không có down migration runtime — restore từ backup nếu fail.

### 5.4 FTS5 (search)
3 virtual table như [06 §5.2](06-data-model.md#52-fts5-virtual-tables-cho-cmdk-search):
- `chapter_fts(title, content)`
- `character_fts(primary_name, aliases, notes, appearance_value, personality_value)`
- `event_fts(title, description, source_quote)`

Trigger `AFTER INSERT/UPDATE/DELETE` đồng bộ. Tokenizer: `unicode61` (đủ tốt cho VN; nếu cần tách Hán-Nôm chính xác hơn, để sau).

### 5.5 Transaction & auto-save
- `Service` mở transaction, pass `tx` xuống repo.
- Auto-save chapter: debounce 5s ở frontend → 1 Wails call → 1 transaction (`UPDATE chapter` + `INSERT chapter_snapshot`). Snapshot rotation chạy cùng tx.
- Mục tiêu: keystroke → render < 50ms ([05 §6](05-site-architecture.md#6-performance--limits)) — auto-save không block UI vì đã async.

---

## 6. AI integration (Go side)

```
   Frontend (AI tab / inline action)
        │  payload: { storyId, action, selection, options }
        ▼
   AIAPI (app layer)
        │
        ▼
   AIService
     1. ContextBuilder.Build(storyId, currentChapterId)         ← spec 11.3
        - 7 tier: system + style → world section (relevant)
                  → character codex (filter arc) → arc summary
                  → event list arc → last 2 chapter raw + prior summaries
                  → current draft + cursor
        - Token budget enforcement (config.MaxTokens)
        - Cache hints: world + character được mark `cache_control: ephemeral`
     2. AIClient.Stream(ctx, prompt, modelOpts)                  ← chọn provider
        - anthropic / openai / ollama qua interface chung
     3. emit Wails event "ai:chunk:<reqId>"
     4. Khi finalize → trả delta proposal (event mới, attribute change…)
        - Không tự ghi DB. Frontend hiện diff modal → user accept/reject từng item.
```

**Hard rule (spec 11.6):**
- AI service không gọi `repo.Write*` trực tiếp. Mọi delta đi qua `FinalizeService.ApplyDelta(ctx, delta, userApproval)` sau khi user duyệt.
- Field `source='user'` không bị override mà không hỏi → check ở `FinalizeService` trước khi apply.

---

## 7. Conflict warning rules

[06 §7](06-data-model.md#7-conflict-warning-rules-cho-specmd-mục-9-build-order-step-9) liệt kê 9 rule. Implement ở `internal/service/conflict_service.go`:

```go
type Rule interface {
    ID() string                                    // "R-DEAD-APPEAR"
    Severity() Severity                            // info / warning / error
    Check(ctx, snap *StoryFullSnapshot) []Issue    // run trên data đã load
}

type ConflictService struct {
    rules []Rule
}

func (s *ConflictService) Run(ctx, storyID) ([]Issue, error) { … }
```

- Run mỗi khi: open chapter, save edit Arc/Event/Character, mở Story Map.
- Issue cache 60s ở service layer; invalidate khi entity liên quan thay đổi.
- UI: badge số issue trên rail + Story Map node có warning dot. Click → modal list, mỗi cái có "Đến", "Bỏ qua rule này", "Đánh dấu intentional" (lưu `Issue.suppressed_at`).

---

## 8. Dependency injection (samber/do)

```go
// internal/di/container.go
func Build(cfg *config.Config) *do.Injector {
    inj := do.New()

    do.Provide(inj, func(i *do.Injector) (*sql.DB, error) {
        return sqlite.Open(cfg.DataDir)
    })
    do.Provide(inj, NewMigrator)
    do.Provide(inj, NewStoryRepo)         // depends *sql.DB
    do.Provide(inj, NewCharacterRepo)
    do.Provide(inj, NewEventRepo)
    // …
    do.Provide(inj, NewConflictService)   // depends repos
    do.Provide(inj, NewAIClient)          // anthropic / openai / ollama factory
    do.Provide(inj, NewContextBuilder)
    do.Provide(inj, NewFinalizeService)

    do.Provide(inj, NewStoryAPI)          // app layer
    do.Provide(inj, NewCharacterAPI)
    // …
    return inj
}
```

`main.go`:

```go
func main() {
    cfg := config.MustLoad()
    log := logging.New(cfg)
    inj := di.Build(cfg)
    defer inj.Shutdown()

    do.MustInvoke[*migration.Migrator](inj).Run()  // chạy migration trước

    err := wails.Run(&options.App{
        Title:  "Web Story",
        Width:  1440, Height: 900,
        Bind: []interface{}{
            do.MustInvoke[*app.StoryAPI](inj),
            do.MustInvoke[*app.CharacterAPI](inj),
            do.MustInvoke[*app.EventAPI](inj),
            do.MustInvoke[*app.ChapterAPI](inj),
            do.MustInvoke[*app.StorylineAPI](inj),
            do.MustInvoke[*app.WorldAPI](inj),
            do.MustInvoke[*app.AIAPI](inj),
            do.MustInvoke[*app.SearchAPI](inj),
            do.MustInvoke[*app.ImportExportAPI](inj),
        },
        // …
    })
    if err != nil { log.Error("wails run", "err", err); os.Exit(1) }
}
```

---

## 9. Testing strategy

| Layer | Cách test | Tooling |
|---|---|---|
| **Domain** | Pure unit (invariant, computed values) | `testing` + `testify/assert` |
| **Service** | Table-driven, repo qua interface mock | `testify/mock` hoặc fake in-mem repo |
| **Repository** | Integration test với SQLite tạm in `t.TempDir()` | `modernc.org/sqlite` + migrations |
| **App layer** | Smoke: gọi method → check DTO mapping | testify + container thật |
| **AI** | Stub `AIClient` interface (record prompt, replay response) | golden file |
| **Frontend** | Vitest + React Testing Library cho component; Playwright cho E2E core flow (`viết 5 chương AI off`) | |
| **Goroutine leak** | `goleak.VerifyNone(t)` ở repo + service test | uber-go/goleak |

CI: GitHub Actions matrix `{macos-latest, ubuntu-latest, windows-latest}` × `go 1.23`.

---

## 10. Build & deploy

```
make dev                # wails dev — hot reload front + Go restart
make build              # wails build → dist/web-story (per OS)
make build-all          # cross-compile arm64/x64 macOS + win + linux
make test               # go test ./… && cd frontend && npm test
make lint               # golangci-lint + eslint
make migrate-new NAME=… # tạo file migration mới
```

Output: 1 binary `web-story` (~25-40 MB) — không cần Node ở máy user.

**Không deploy lên public web.** Personal tool, chạy local. Phân phối qua DMG/ZIP/MSI tự build, không qua App Store.

---

## 11. Performance targets

Giữ nguyên [05 §6](05-site-architecture.md#6-performance--limits):

| Metric | Target | Cách đảm bảo |
|---|---|---|
| Editor keystroke → render | < 50ms tại 20k chữ/chương | TipTap + chunked render; auto-save async |
| Story map render | < 200ms với 30 Arc, 100 Event | Single SQL query với JOIN, index `idx_event_arc` |
| Character grid | < 200ms với 200 character | `LIMIT/OFFSET` + virtualised list |
| Quick search | < 100ms | FTS5 query + LIMIT 12 |
| Auto-save | Non-blocking, không lag editor | Debounce 5s + transaction + WAL |
| Project size | 200k+ chữ, 100+ event, 50+ char | Đo bằng `BenchmarkLargeProject` |

---

## 12. Privacy & data ownership

Giữ nguyên [05 §7](05-site-architecture.md#7-privacy--data-ownership):
- 100% local. Không server, không cloud sync.
- AI request: Go gọi thẳng provider với key của user. Không log prompt/response.
- Export full data bất cứ lúc nào (JSON/Markdown).
- Xóa project = xóa file `.sqlite` trong data dir.

---

## 13. Module → code mapping (build order)

Bám [spec.md §14 build order](spec.md#14-build-order-gợi-ý-1-phase-ưu-tiên-critical-path), mỗi bước = stack vertical (DB → repo → service → API → UI):

| # | Bước | Backend file mới | Frontend file mới |
|---|---|---|---|
| 1 | Story + Chapter editor + manual save | `domain/story`, `domain/chapter`, `repository/sqlite/story_repo.go`, `chapter_repo.go`, `service/chapter_service.go`, `app/story_api.go`, `chapter_api.go`, `migrations/001_init.sql` | `routes/Workspace.tsx`, `modules/editor/Editor.tsx`, `state/useEditorStore.ts` |
| 2 | Character CRUD + Codex | `domain/character`, repo, service, api | `modules/character/{Grid,Detail}.tsx`, `routes/tabs/CharactersTab.tsx` |
| 3 | Storyline + Arc + Event + Story Map tree | `domain/{storyline,arc,event}`, repos, services | `modules/storymap/Tree.tsx`, `routes/tabs/StoryMapTab.tsx` |
| 4 | Link Chapter↔Event, Event↔Character | `repository/sqlite/character_event_link_repo.go`, infer-arc rule trong `chapter_service.go` | inline mention TipTap extension |
| 5 | AttributeHistory + Trait + filter timeline | `domain/character/attribute_history.go`, `trait.go`, `service/snapshot_service.go` | `modules/character/AttributeHistoryForm.tsx`, filter UI trong StoryMap |
| 6 | World Bible markdown | `domain/world`, repo, api | `routes/tabs/WorldBibleTab.tsx` |
| 7 | Refactor ops (drag-reorder, split/merge, kill char) | `service/refactor_service.go` | drag-drop trong Tree.tsx |
| 8 | Manual finalize + summary | `service/finalize_service.go` (manual branch) | `modules/editor/FinalizeModal.tsx` |
| 9 | Conflict warning rules | `service/conflict_service.go` + 9 rule files | issue badge UI |
| 10 | Export JSON/Markdown | `service/import_export_service.go` | `routes/AppSettings.tsx` Backup section |
| 11 | Settings + AI toggle | `config` extend | AI toggle ở topbar |
| 12 | AI 4 action + context tier | `ai/`, `service/context_builder.go` | `modules/ai/SuggestPanel.tsx` |
| 13 | AI sync diff modal | `service/finalize_service.go` (AI branch) | `modules/ai/DiffModal.tsx` |
| 14 | AI skeleton generator | `service/skeleton_service.go` | `routes/NewProject.tsx` AI path |
| 15 | Polish | shortcut registry, distraction-free CSS, version history view | |

---

## 14. So sánh với phương án cũ (Tauri/Rust)

| Khía cạnh | Tauri + Rust + Next.js | **Wails + Go + Vite-React** |
|---|---|---|
| Binary size | ~10-15 MB | ~25-40 MB |
| Cross-compile | Khó (cần Rust + native libs per OS) | Dễ (pure Go + modernc/sqlite) |
| Dev iteration | Cargo rebuild chậm | Go build < 2s |
| SQLite FTS5 | rusqlite + bundled | modernc/sqlite (pure Go) |
| Frontend | Next.js (SSR thừa cho desktop) | Vite (đúng nhu cầu SPA) |
| Skill ecosystem | — | Đã cài 42 Go skill (samber/do, oops, lo, slog…) |
| Learning curve | Rust ownership | Go straight-forward |
| AI SDK | `anthropic-rs` (community) | `anthropic-sdk-go` (official) |

Trade-off: Wails ít trưởng thành hơn Tauri một chút, ecosystem nhỏ hơn. Bù lại: tốc độ build, đơn giản, cross-compile, và phù hợp với skill stack đã chọn.

---

## 15. Risks & mitigation

| Risk | Mitigation |
|---|---|
| Wails v2 còn breaking change giữa minor | Pin version chính xác trong `go.mod` + `wails.json`; lock CI matrix. |
| `modernc.org/sqlite` chậm hơn CGO ~2-3× ở write nặng | Acceptable cho personal tool. Nếu fail benchmark §11 → swap sang `mattn/go-sqlite3` (CGO) qua build tag. |
| FTS5 tokenizer `unicode61` không tách Hán-Nôm tốt | Fallback rule: query LIKE `%term%` cho `aliases`. Custom ICU tokenizer là phase 2. |
| AI streaming qua Wails events có thể đổi API | Gói qua interface `AIStream`; nếu Wails đổi thì chỉ sửa adapter. |
| Frontend bundle phình to (TipTap + shadcn) | Vite code-split per route; preload editor chunk khi mở project. |

---

## 16. Open questions cho lần build

- [ ] Embed Lora / JetBrains Mono / Inter trong binary hay tải runtime? (kích thước vs offline-first) — nghiêng embed, +~2 MB.
- [ ] Có cần `swaggo/swag` không? — Tool chỉ có Wails IPC, không có HTTP API public → **không cần**, bỏ skill `golang-swagger` khỏi critical path.
- [ ] DI dùng `samber/do` hay tự inject thủ công? — Personal tool có ~15 service. `samber/do` đáng dùng cho lifecycle Shutdown, nhưng cũng có thể manual init nếu muốn zero-dep.
- [ ] Test E2E qua Playwright (drive WebView của Wails) hay chỉ unit + integration? — Chốt sau bước 4 build order.

---

## 17. Tham chiếu chéo

- Schema chi tiết: [06-data-model.md](06-data-model.md)
- Flow & Done criteria: [spec.md](spec.md)
- Sitemap & UI nav: [05-site-architecture.md mục 1–4](05-site-architecture.md)
- Module logic: [01-editor.md](01-editor.md), [02-character.md](02-character.md), [03-event.md](03-event.md), [04-timeline.md](04-timeline.md)
- Design HTML/CSS gốc: [docs/design/story-v2/project/](design/story-v2/project/)
- Skill ecosystem (Go): `.agents/skills/golang-*` (42 skill, samber/cc-skills-golang)
- Skill ecosystem (FE): `.agents/skills/{shadcn, tailwind-css-patterns, vercel-react-best-practices, vercel-composition-patterns, typescript-advanced-types}`
