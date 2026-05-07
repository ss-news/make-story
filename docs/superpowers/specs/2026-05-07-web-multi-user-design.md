# Web Story — Multi-user Web App v1 Design

**Date:** 2026-05-07
**Status:** Draft (chờ user review)
**Replaces:** Top-level `README.md` plan + `docs/spec.md` mục 12–14 (multi-user web variant). Canonical `docs/06-data-model.md` được kế thừa với các adaptation cho Postgres + ownership ở Section 3.

---

## 0. Bối cảnh & quyết định cốt lõi

`docs/spec.md` viết cho **personal Wails desktop app** (single-user, local-first, SQLite). User pivot sang **multi-user web app** với các quyết định đã chốt qua brainstorming:

| Quyết định | Giá trị |
|---|---|
| Loại sản phẩm | Multi-user web app |
| Quy mô | Self-hosted nhỏ, 1-10 user |
| Scope v1 | Full pixel-perfect bao gồm AI layer |
| Approach | Vertical slice, build module theo thứ tự |
| AI provider | Backend proxy → `LLM_BASE_URL` (OpenAI-compatible). Shared key qua env. |
| Stack backend | Go 1.23+, chi router, pgx, golang-migrate, samber/{do,oops,lo,mo}, slog |
| Stack frontend | React 18 + TypeScript + Vite + Tailwind + shadcn/ui + TipTap + Zustand + TanStack Query |
| Database | PostgreSQL 16 |
| Auth | Open registration, email + password (bcrypt cost 12), session cookie 30 ngày sliding |
| Ownership | Hard silo — mỗi entity thuộc 1 user qua `stories.owner_user_id` |
| Design | `docs/design/story-v2/` là source of truth — pixel-perfect target. Spec.md có thể update để khớp design. |

**Định hướng:** Giữ tinh thần "manual-first, AI-optional" của spec gốc. AI default OFF per-user. Mọi feature work khi tắt AI.

---

## 1. Topology & repo layout

### 1.1 Topology (1 instance, single VPS)

```
┌─────────────────────────────────────────────────────────────────┐
│                       Single VPS / Docker host                   │
│                                                                 │
│   ┌──────────────┐    ┌────────────────────┐    ┌─────────────┐ │
│   │   Caddy /    │───▶│  make-story (Go)   │───▶│ Postgres 16 │ │
│   │   Nginx      │    │  HTTP API + static │    │             │ │
│   │  (TLS, gzip) │    │  fileserver        │    └─────────────┘ │
│   └──────────────┘    └─────────┬──────────┘                    │
│                                 │ HTTPS                          │
└─────────────────────────────────┼───────────────────────────────┘
                                  ▼
                      https://llm.musia.store/v1
                      (LLM_API_KEY from env)
```

- Frontend là static SPA (Vite build → `dist/`), backend serve static qua route `/` + API qua `/api/*`.
- Caddy/Nginx ở trước cho TLS + reverse proxy. Single binary `make-story` chạy port nội.
- Postgres riêng container/process. Backup snapshot qua `pg_dump` cron.
- Session lưu Postgres (table `sessions`), không cần Redis.

### 1.2 Repo layout

```
make-story/
├── backend/
│   ├── cmd/server/main.go           # entrypoint
│   ├── internal/
│   │   ├── app/                     # wire-up: chi, middleware, DI (samber/do)
│   │   ├── auth/                    # password, session, middleware
│   │   ├── domain/                  # entities + invariants (theo 06-data-model.md)
│   │   ├── service/                 # use cases
│   │   ├── adapter/
│   │   │   ├── repo/                # pgx implementations
│   │   │   ├── llm/                 # OpenAI-compatible client
│   │   │   └── search/              # FTS via Postgres tsvector
│   │   ├── api/                     # HTTP handlers, DTO, validation, embed FE static
│   │   └── migrations/*.sql         # golang-migrate, embed.FS
│   ├── go.mod
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── api/                     # TanStack Query hooks + fetch wrapper
│   │   ├── components/              # shadcn base + custom shared
│   │   ├── features/
│   │   │   ├── auth/                # login, register
│   │   │   ├── dashboard/           # ProjectList
│   │   │   ├── editor/              # 3-col Editor (TipTap)
│   │   │   ├── storymap/            # canvas + arc-detail
│   │   │   ├── characters/          # Grid + Detail
│   │   │   ├── relgraph/            # SVG graph
│   │   │   ├── events/              # List + Detail modal
│   │   │   ├── world/               # World Bible
│   │   │   ├── settings/            # Settings page
│   │   │   ├── create-modal/        # global Create modal
│   │   │   ├── cmdk/                # ⌘K palette
│   │   │   └── ai-diff/             # Diff modal
│   │   ├── stores/                  # Zustand
│   │   ├── lib/                     # utils
│   │   ├── styles/                  # tokens.css (port từ design styles.css)
│   │   ├── App.tsx                  # routing (react-router)
│   │   └── main.tsx
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── docs/                            # giữ nguyên
├── deploy/
│   ├── Caddyfile
│   ├── docker-compose.yml
│   └── Dockerfile                   # multi-stage
│
└── README.md
```

---

## 2. Auth model

### 2.1 Schema mới

```sql
users (
  id              uuid PK DEFAULT gen_random_uuid(),
  email           citext UNIQUE NOT NULL,
  password_hash   text NOT NULL,             -- bcrypt cost 12
  display_name    text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  is_admin        bool NOT NULL DEFAULT false,
  ai_enabled      bool NOT NULL DEFAULT false
)

sessions (
  id              text PK,                   -- random 32-byte hex
  user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at      timestamptz NOT NULL DEFAULT now(),
  last_seen_at    timestamptz NOT NULL DEFAULT now(),
  expires_at      timestamptz NOT NULL,      -- created_at + 30 days
  user_agent      text,
  ip              inet
)
CREATE INDEX ON sessions(user_id);
CREATE INDEX ON sessions(expires_at);
```

### 2.2 Endpoints

| Endpoint | Hành vi |
|---|---|
| `POST /api/auth/register` | `{email, password, display_name}` → tạo user, tạo session, set cookie `sid` |
| `POST /api/auth/login` | `{email, password}` → bcrypt verify, tạo session, set cookie |
| `POST /api/auth/logout` | Xóa session + clear cookie |
| `GET  /api/auth/me` | Trả user hiện tại hoặc 401 |

### 2.3 Cookie & session

- Name `sid`, `HttpOnly`, `Secure` (prod), `SameSite=Lax`, `Path=/`
- Expiry 30 ngày, sliding renewal mỗi request (gia hạn nếu còn <7 ngày)

### 2.4 Middleware chain (chi)

```go
r.Use(middleware.RequestID, middleware.Logger, middleware.Recoverer)
r.Use(SessionLoader)              // load user vào ctx, không reject

r.Group(func(r chi.Router) {
    r.Post("/api/auth/register", ...)
    r.Post("/api/auth/login", ...)
    r.Get("/api/auth/me", ...)
})

r.Group(func(r chi.Router) {
    r.Use(AuthRequired)            // 401 nếu không auth
    r.Mount("/api", protectedRoutes)
})

r.Get("/*", staticHandler)         // serve frontend/dist
```

### 2.5 Rules

- Password tối thiểu 8 ký tự, không validate complexity khác
- Bcrypt cost 12
- Không có forgot-password v1 (admin reset DB nếu cần)
- Không 2FA, không OAuth
- Open registration; có thể disable bằng env `DISABLE_REGISTRATION=true`
- Admin promote qua CLI: `make-story user promote --email=...`
- Rate limit auth endpoints: 10 req/phút/IP qua `httprate`

---

## 3. Data model adaptations

Canonical schema = `docs/06-data-model.md`. Web/Postgres/multi-user áp các thay đổi sau:

### 3.1 Ownership (cột mới chỉ ở `stories`)

```sql
ALTER TABLE stories ADD COLUMN owner_user_id uuid NOT NULL
  REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX ON stories(owner_user_id);
```

Mọi entity con join qua `story_id` để lookup owner — schema sạch, integrity đảm bảo bởi FK chain. Mọi service method check ownership 1 lần đầu:
```go
if err := s.stories.EnsureOwner(ctx, storyID, userID); err != nil {
    return err  // → 404 NotFound (không leak existence)
}
```

### 3.2 SQLite → Postgres mapping

- `INTEGER PK AUTOINCREMENT` → `uuid PK DEFAULT gen_random_uuid()` (cần extension `pgcrypto`)
- `TEXT/INTEGER/REAL` → `text/int4|int8/numeric|double precision`
- `BLOB` → `bytea` hoặc giữ `text` (TipTap export JSON)
- `created_at INTEGER` (epoch) → `timestamptz NOT NULL DEFAULT now()`
- Boolean: `bool NOT NULL`

### 3.3 FTS5 → tsvector + pg_trgm

```sql
ALTER TABLE chapters ADD COLUMN search_tsv tsvector
  GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(title,'')), 'A') ||
    setweight(to_tsvector('simple', coalesce(content_text,'')), 'B')
  ) STORED;
CREATE INDEX ON chapters USING GIN(search_tsv);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX ON chapters USING GIN(title gin_trgm_ops);
CREATE INDEX ON characters USING GIN(name gin_trgm_ops);
```

Dùng `simple` dictionary (không có VN dict mạnh trong Postgres core); pg_trgm cover substring match cho VN có dấu.

### 3.4 Migrations

- `golang-migrate` + `embed.FS` từ `backend/internal/migrations/*.sql`
- `0001_init.sql` — extensions + users + sessions
- `0002_stories.sql` — stories + storylines + arcs + chapters
- `0003_codex.sql` — characters + events + character_event_links + relationships + world_bible
- `0004_attribute_history.sql` — attribute_history + traits
- `0005_search.sql` — tsvector cột + GIN indexes + pg_trgm
- `0006_seed_demo.sql` — seed `demo@example.com / demo1234` + Lý Thanh Vân story (port từ `data.js`); disable bằng env `SEED_DEMO=false`

### 3.5 Decisions cần update trong `docs/06`

- D4: "storage = SQLite + Tauri" → "Postgres 16 + chi/pgx HTTP server"
- D1, D5, D6: giữ nguyên

### 3.6 Conflict warning rules

Giữ nguyên rule trong `06 §7`. Implement ở `service/conflict_rules.go`. Response shape:
```json
{ "data": {...}, "warnings": [{"rule_id": "R-DEAD-APPEAR", "message": "...", "severity": "warn", "refs": [...]}] }
```

---

## 4. API surface

REST, JSON, prefix `/api`. Tất cả endpoint (trừ auth register/login) qua `AuthRequired` + ownership check.

### 4.1 Convention

- URL kebab-case (`/api/stories/{story_id}/story-map`)
- Method: GET/POST/PATCH/DELETE (không PUT)
- ID: UUID path param, không lặp trong body
- Response success:
  ```json
  { "data": {...}, "warnings": [...] }
  ```
- Response error:
  ```json
  { "error": { "code": "VALIDATION", "message": "...", "fields": {...} } }
  ```
- List: không paginate v1 (≤ vài chục stories, ≤ vài trăm entities); shape sẵn `{data, cursor: null}` để mở rộng
- Validation: `go-playground/validator`
- Optimistic concurrency: chỉ cho Chapter (gửi `updated_at` cũ; 409 nếu mismatch)

### 4.2 Endpoints (~70)

**Auth (4):** register, login, logout, me

**Stories (5):** list, create (auto Storyline "Main"), detail, patch, delete

**Storylines + Arcs + Events (16):** CRUD đầy đủ + reorder + move event giữa arc + Event detail full

**Chapters (8):** list, create, detail, patch (auto-save), delete, finalize (`{manual_summary}`), snapshot, list snapshots

**Characters + AttributeHistory + Traits + Relationships (15):**
- Character CRUD + detail (kèm attr history + traits)
- AttributeHistory CRUD per character
- Trait CRUD per character
- Relationship CRUD per story

**Character ↔ Event links (3):** create, patch role, delete

**World Bible (4):** get all, create section, patch section, delete section

**Story Map / aggregates (3):** story-map tree, timeline (sort theo `story_time` | `narrative_order`), character-snapshot at point T

**Search (1):** `/api/stories/{sid}/search?q=...` → `{chapters, characters, events, arcs}`

**AI (6):**
- `POST /api/ai/suggest-beat` (SSE optional)
- `POST /api/ai/continue` (SSE)
- `POST /api/ai/rewrite` (SSE optional)
- `POST /api/ai/ask` (SSE optional)
- `POST /api/ai/finalize-suggest` (JSON)
- `POST /api/ai/skeleton` (JSON)

**Export/Import (2):** export `?format=json|markdown`, import upload JSON

**Admin (2):** list users, promote

### 4.3 Ownership pattern

Mỗi service method nhận `userID` từ ctx. Ownership check first line, fail-fast 404. Cache trong request scope qua `samber/lo.Memoize` nếu request mutate nhiều entity.

### 4.4 AI streaming

`/api/ai/continue` và `/api/ai/suggest-beat` hỗ trợ SSE khi `Accept: text/event-stream`. Frontend dùng `fetch` + reader loop (cần POST body, không EventSource). Fallback JSON nếu Accept khác.

---

## 5. Frontend module breakdown

### 5.1 Routing (react-router v6)

```
/login                                # public
/register                             # public
/                                     # → /dashboard nếu auth, /login nếu không
/dashboard                            # ProjectList
/s/:storyId                           # → /s/:storyId/editor
/s/:storyId/editor                    # Editor 3-col
/s/:storyId/editor/:chapterId         # focus chapter
/s/:storyId/storymap                  # canvas
/s/:storyId/storymap/arc/:arcId       # arc-detail
/s/:storyId/characters
/s/:storyId/characters/:characterId
/s/:storyId/rels
/s/:storyId/events
/s/:storyId/world
/settings
```

Design dùng state local cho navigation; web phải có URL routing để bookmark/back-forward — adaptation cần thiết, không phá pixel-perfect (URL không hiện trong UI).

EventDetail giữ modal overlay nhưng add query string `?event=eid` cho share-able URL.

### 5.2 State strategy

| State type | Tool | Lý do |
|---|---|---|
| Server state | TanStack Query | Cache, invalidation, optimistic update |
| UI state (theme, AI on/off, sidebar) | Zustand | Persist subset trong localStorage |
| Form state | react-hook-form + zod | Validation đồng bộ với DTO backend |
| Modal/overlay | URL search params + Zustand | Share-able URL |

Auth state: Zustand store `useAuth`, fetch `/api/auth/me` 1 lần khi load. 401 từ bất kỳ API → redirect `/login`.

### 5.3 Tokens & styling

- Extract toàn bộ CSS variables từ `docs/design/story-v2/project/styles.css` (82.5K) → `frontend/src/styles/tokens.css`. Giữ nguyên tên var.
- Tailwind config đọc CSS var qua `colors: { bg: 'var(--bg)', ... }`.
- Dark theme: `data-theme="dark"` trên `<body>` flip CSS var.
- Fonts: Lora + JetBrains Mono + Inter qua `@fontsource/*` (không CDN).

### 5.4 Component port plan (1-1 với design)

| Design file | → React/TS module |
|---|---|
| `common.jsx` | `components/{Icon, Tag, Kbd, ToolbarButton, ...}.tsx` |
| `projects.jsx` | `features/dashboard/ProjectList.tsx` |
| `editor.jsx` + `canvas.jsx` | `features/editor/{Editor, EditorCanvas, ContextPanel}.tsx` |
| `create-modal.jsx` (37.7K) | `features/create-modal/CreateModal.tsx` + sub-files split theo tab |
| `storymap.jsx` | `features/storymap/{StoryMapCanvas, ArcDetail}.tsx` |
| `characters.jsx` | `features/characters/{CharacterGrid, CharacterDetail}.tsx` |
| `relgraph.jsx` | `features/relgraph/RelGraph.tsx` |
| `events.jsx` | `features/events/{EventList, EventDetail}.tsx` |
| `misc.jsx` | `features/world/WorldBible.tsx` + `features/settings/Settings.tsx` |
| `Web Story.html` (App + CmdK + DiffModal) | `App.tsx` + `features/cmdk/CommandK.tsx` + `features/ai-diff/DiffModal.tsx` |

### 5.5 Status bar adaptation

Design hardcode "SQLite local · ~/Library/web-story.db". Web đổi thành:
```
DỰ ÁN <story>    CH <n>/<total>    TỪ <count>    ARC <i> — <name>
                                  Đăng nhập: <email>    ● Đã lưu    v0.1
```
Bỏ "SQLite local · path", thay bằng email user (truncate). UI khác giữ pixel-perfect.

### 5.6 i18n

- Default `vi`. Lib: `react-i18next` + `i18next-browser-languagedetector`
- v1 chỉ ship locale `vi`. Strings hardcode theo design (đã là vi). Đặt trong `vi.json` để sau add `en` dễ.
- Không build `en` v1 (YAGNI cho scope nhỏ); chỉ chuẩn bị infrastructure.

### 5.7 TipTap setup

- Extensions: StarterKit + Heading + BulletList + OrderedList + Blockquote + CodeBlock + Link
- Custom node `@character-mention` (popup chọn character từ codex story hiện tại). Lưu `<span data-character-id="...">@Tên</span>`.
- Lưu format: JSON (TipTap native) trong `chapters.content_json`. Plain text vào `chapters.content_text` (generated column hoặc trigger) cho FTS.
- Auto-save: debounce 800ms → PATCH `/api/chapters/{id}` với `updated_at` cũ.

### 5.8 Frontend serving

- Vite build → `frontend/dist/`
- Go backend embed `dist/` qua `embed.FS` (`internal/api/static.go`)
- Fallback `index.html` cho mọi route không match `/api/*` (SPA routing)

---

## 6. AI proxy layer

### 6.1 Wire diagram

```
Browser ────POST /api/ai/continue (SSE)──▶ Backend
                                              │
                                              │ ContextBuilder ─▶ Postgres
                                              │
                                              │ POST /v1/chat/completions
                                              ▼
                                  https://llm.musia.store/v1
                                              │
                                              │ stream chunks
                                              ▼
Browser ◀──text/event-stream chunks── Backend
```

### 6.2 LLM client (`internal/adapter/llm/`)

OpenAI-compatible HTTP client thuần (không SDK). Interface:

```go
type Client interface {
    Chat(ctx context.Context, req ChatRequest) (*ChatResponse, error)
    ChatStream(ctx context.Context, req ChatRequest, onChunk func(Delta) error) error
}

type ChatRequest struct {
    Model       string
    Messages    []Msg
    MaxTokens   int
    Temperature float32
    Stream      bool
}
```

Implement: `net/http` + `bufio.Scanner` đọc SSE (`data: {...}` lines). Timeout 60s tổng.

### 6.3 Config (env)

```
LLM_BASE_URL       = https://llm.musia.store/v1
LLM_API_KEY        = <secret>
LLM_DEFAULT_MODEL  = claude-sonnet-4-5
LLM_MAX_TOKENS     = 2048
LLM_TIMEOUT_SEC    = 60
AI_DAILY_LIMIT     = 0       # 0 = unlimited; >0 enforce per-user/ngày
```

Backend gọi `GET /v1/models` 1 lần startup, cache list, expose qua `GET /api/ai/models` cho FE dropdown trong Settings.

### 6.4 Context Builder (theo spec.md mục 11.3)

7 tier:
1. System prompt + style guide (per action template)
2. World bible — chỉ sections referenced bởi current arc/chapter
3. Character codex — chỉ characters trong current arc + tagged trong chapter draft
4. Arc summary — current + previous arc cùng storyline
5. Event list — events trong current arc
6. Last 2 chapters raw + manual_summary các chapter trước
7. Current chapter draft + cursor marker

Token budget mặc định 32k. Tier 6 cap 8k, tier 7 fill phần còn lại. Estimate `len(text)/3`; thêm `tiktoken-go` nếu cần chính xác.

### 6.5 Per-user rate limit

```sql
ai_usage (
  user_id        uuid,
  day            date,
  request_count  int,
  PRIMARY KEY (user_id, day)
)
```

- Nếu `cfg.AIDailyLimit == 0` → skip check hoàn toàn (không hit DB)
- `> 0` → enforce; vượt → 429
- Admin bypass independently

### 6.6 Action endpoints

| Endpoint | Hành vi | Stream? |
|---|---|---|
| `/api/ai/suggest-beat` | Context → 3 beat options | Có thể |
| `/api/ai/continue` | Context + draft → 200-500 chữ | **SSE** |
| `/api/ai/rewrite` | Context + selection + prompt → version mới | Có thể |
| `/api/ai/ask` | Context (filtered scope) + question → Q&A | Có thể |
| `/api/ai/finalize-suggest` | Chapter content + diff codex → JSON delta | Không |
| `/api/ai/skeleton` | Premise/genre → world + characters + arcs/events | Không |

Prompt template ở `internal/service/prompts/*.tmpl` (Go `text/template`), versioned với git.

### 6.7 user_edited flag respect

- Field user-editable trong character/world có cột `user_edited bool` + `last_edited_source enum('user','ai_imported')`
- Prompt finalize-suggest include warning "field này user đã sửa, KHÔNG suggest override trừ khi clearly contradicted bởi chapter content"
- Diff modal hiện badge `user-edited` cho item rủi ro override

### 6.8 AI toggle (per-user)

- `users.ai_enabled bool DEFAULT false` (match spec "AI optional, default OFF")
- `false` → FE ẩn nút AI; backend reject `/api/ai/*` 403 (defense in depth)
- ON yêu cầu user xác nhận: thông báo prompt sẽ gửi tới `LLM_BASE_URL`, backend giữ key, audit log không lưu nội dung

### 6.9 Audit log

```sql
ai_audit (
  id, user_id, action, model,
  prompt_token, completion_token,
  status, latency_ms, created_at
)
```

Không lưu prompt/completion text (privacy). Admin query để phát hiện abuse / debug cost.

---

## 7. Deployment, observability, secrets

### 7.1 Dockerfile (multi-stage)

```dockerfile
# Stage 1: Frontend
FROM node:22-alpine AS fe
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Backend
FROM golang:1.23-alpine AS be
WORKDIR /src
COPY backend/go.mod backend/go.sum ./
RUN go mod download
COPY backend/ ./
COPY --from=fe /app/dist ./internal/api/static/dist
RUN go build -ldflags='-s -w' -o /out/make-story ./cmd/server

# Stage 3: Runtime
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=be /out/make-story /make-story
EXPOSE 8080
ENTRYPOINT ["/make-story"]
```

FE embed vào binary qua `embed.FS` — single self-contained binary.

### 7.2 docker-compose.yml

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: makestory
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: makestory
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "makestory"]
      interval: 5s

  app:
    build: .
    environment:
      DATABASE_URL: postgres://makestory:${POSTGRES_PASSWORD}@postgres:5432/makestory?sslmode=disable
      SESSION_SECRET: ${SESSION_SECRET}
      LLM_BASE_URL: https://llm.musia.store/v1
      LLM_API_KEY: ${LLM_API_KEY}
      LLM_DEFAULT_MODEL: claude-sonnet-4-5
      AI_DAILY_LIMIT: "0"
      DISABLE_REGISTRATION: "false"
      SEED_DEMO: "false"
      LOG_LEVEL: info
      LOG_FORMAT: json
      PORT: "8080"
    depends_on:
      postgres: { condition: service_healthy }
    restart: unless-stopped
    ports:
      - "127.0.0.1:8080:8080"

volumes:
  pgdata:
```

### 7.3 Caddyfile

```
makestory.example.com {
    encode gzip zstd
    reverse_proxy 127.0.0.1:8080
    header {
        Strict-Transport-Security "max-age=31536000"
        X-Content-Type-Options nosniff
        Referrer-Policy strict-origin-when-cross-origin
    }
}
```

Caddy auto Let's Encrypt cert.

### 7.4 Secrets

- `.env` ở host (không commit). `.gitignore` block `.env`.
- Repo có `.env.example` với placeholder.
- Variables:
  ```
  POSTGRES_PASSWORD, SESSION_SECRET, LLM_API_KEY
  ```

### 7.5 Observability

**Logging:**
- `slog` JSON production, text dev
- Mỗi request: `request_id, method, path, status, latency_ms, user_id, user_agent`
- AI calls log riêng qua `ai_audit`
- `samber/oops` chain error với context tags

**Metrics:** v1 không tích Prometheus (over-kill). Health-check:
```
GET /api/health → 200 {status:ok, db:up, llm:up}
```

**Error tracking:** v1 đọc log file. Thêm Sentry/Honeybadger sau nếu cần.

### 7.6 Backups

```
0 3 * * *  docker exec postgres pg_dump -U makestory -Fc makestory > /backups/makestory-$(date +%F).dump
```

Retention 30 ngày. Restore script `deploy/restore.sh`.

### 7.7 Database migrations

- Chạy tự động khi backend boot: `migrator.Up(ctx)` trong `cmd/server/main.go`. Idempotent.
- Embed `*.sql` qua `embed.FS`.
- Rollback: `make-story migrate down` CLI (cẩn thận; production nên restore pg_dump).

### 7.8 CLI subcommands

```
make-story serve                              # default
make-story migrate up|down|version
make-story user create --email=... --display-name=... [--admin]
make-story user list
make-story user promote --email=...
make-story export-story --id=... --format=json
```

### 7.9 Local dev

`Makefile`:
```
make dev-db      # postgres container
make dev-be      # backend với hot reload (air)
make dev-fe      # frontend Vite (proxy /api → :8080)
make build       # full docker build
make seed        # run 0006_seed_demo.sql
```

Vite proxy:
```ts
server: { proxy: { '/api': 'http://localhost:8080' } }
```

### 7.10 CSRF + rate limit

- Cookie `SameSite=Lax` + state-changing endpoints check `Origin` header. Reject nếu Origin không match `cfg.AllowedOrigins`.
- `httprate` middleware: 60 req/phút/IP non-auth; 10 req/phút/IP auth endpoints.

---

## 8. Build order (replaces spec.md mục 14)

Vertical slice. Mỗi step deploy được, dogfood sớm. ✅ = pixel-perfect khớp design.

### Step 0 — Repo scaffold
- `backend/` + `frontend/` + `deploy/` theo Section 1
- Makefile, .env.example, Dockerfile, docker-compose, Caddyfile
- Backend: chi router + `GET /api/health` + slog + DI skeleton (samber/do)
- Frontend: Vite + React + TS + Tailwind + shadcn init + port `tokens.css`
- Migration runner stub
- CI: build + lint Go + frontend type-check

### Step 1 — Auth shell + base layout
- Migration `0001_init.sql`
- Backend: `/api/auth/{register,login,logout,me}` + middleware
- Frontend: `/login`, `/register` pages + auth store + 401 redirect
- ✅ Topbar + Rail + Statusbar (App shell từ `Web Story.html`)
- Statusbar text điều chỉnh: thay "SQLite local" bằng email user

### Step 1.5 — Architecture review với `golang-design-patterns` skill
- Invoke skill `golang-design-patterns` để review project structure đã scaffold
- Review: layer boundaries, DI usage (samber/do), error chain (samber/oops), repository pattern, HTTP handler pattern, testing pattern, file size signals
- Output: `docs/architecture/go-patterns.md` chốt convention
- Refactor Step 0/1 code nếu skill chỉ ra pattern lệch
- Step 2-15 sau follow document đã chốt
- Note: nếu skill chưa cài, copy từ `.agents/skills/golang-design-patterns` vào `~/.claude/skills/`

### Step 2 — Stories CRUD + Dashboard ✅
- Migration `0002_stories.sql` (stories với `owner_user_id`)
- Backend: `/api/stories/*` (5 endpoints) + ownership check
- Frontend: `features/dashboard/ProjectList` port `projects.jsx` pixel-perfect
- CreateModal tab `project`
- Routing `/dashboard`, `/s/:storyId` redirect editor (placeholder)

### Step 3 — Editor M0 ✅
- Migration `0002` thêm chapters
- Backend: `/api/stories/{sid}/chapters` + `/api/chapters/{id}` + auto-save
- Frontend: `features/editor/Editor` port `editor.jsx` + `canvas.jsx` pixel-perfect
- TipTap setup
- Auto-save debounce 800ms với optimistic concurrency
- Word count "chữ"
- ✅ Distraction-free + theme + Lora editor font
- Context panel right: Codex tab + Notes tab

**Ship:** Vào story → tạo chapter → viết → auto-save. Dogfood viết được 1 chương thật.

### Step 4 — Storyline + Arc + Event CRUD + Story Map ✅
- Migration `0003` storylines + arcs + events
- Backend: 16 endpoints + reorder/move
- Frontend: `features/storymap/StoryMapCanvas` + `ArcDetail`
- CreateModal mở rộng tabs `storyline/arc/event`
- Drag-drop qua `dnd-kit`
- Story Map mini trong Editor context panel

### Step 5 — Characters + AttributeHistory + Traits ✅
- Migration `0004` characters + attribute_history + traits + character_event_links
- Backend: 15 endpoints
- Frontend: `features/characters/{CharacterGrid, CharacterDetail}`
- CreateModal tab `character`
- Editor codex tab fill characters relevant
- TipTap `@character-mention` extension
- Filter timeline view trong character detail

**🚧 Risk gate:** ép viết 5 chương thật trong web app. Không viết được → fix viết, không build Step 6+.

### Step 6 — Relationships + Rel Graph ✅
- Migration `0004` thêm relationships
- Backend: 4 endpoints
- Frontend: `features/relgraph/RelGraph` pixel-perfect SVG
- CreateModal tab `relationship`

### Step 7 — Events list + Detail modal + character ↔ event link ✅
- Backend: 3 link endpoints + Event detail
- Frontend: `features/events/{EventList, EventDetail}`
- Crossover detect (auto-flag character từ storyline khác)

### Step 8 — World Bible ✅
- Migration `0005` world_sections + world_entries
- Backend: 4 endpoints
- Frontend: `features/world/WorldBible` markdown + glossary

### Step 9 — Cmd+K, search, conflict warnings ✅
- Migration `0005` search tsvector + pg_trgm
- Backend: `/api/stories/{sid}/search` + ConflictRules service
- Frontend: `features/cmdk/CommandK` ⌘K modal
- Conflict warnings banner trong context panel

### Step 10 — Refactor ops + Export/Import + Settings ✅
- Backend: split/merge chapter, kill character, export JSON/Markdown, import JSON
- Frontend: `features/settings/Settings`
- Refactor menu trong context panel

**Ship:** Tool **manual** complete (như Plottr/Notion).

### Step 11 — AI infrastructure ✅
- Migration `0006` ai_audit + ai_usage + `users.ai_enabled`
- Backend: LLM client adapter, ContextBuilder, rate limit env-based, `/api/ai/models`
- Frontend: AI toggle với confirm dialog
- Settings model picker từ `/api/ai/models`

### Step 12 — AI 4 actions + SSE streaming ✅
- Backend: `/api/ai/{suggest-beat,continue,rewrite,ask}` + SSE
- Frontend: AI tab + 4 nút action
- Streaming UI cho Continue

### Step 13 — AI Diff Modal ✅
- Backend: `/api/ai/finalize-suggest` + `user_edited` respect
- Frontend: `features/ai-diff/DiffModal`
- Apply accepted items qua endpoint

### Step 14 — AI Skeleton generator ✅
- Backend: `/api/ai/skeleton`
- Frontend: "Generate Skeleton with AI" trong CreateModal tab `project` → review wizard

### Step 15 — Polish & deploy
- Keyboard shortcuts đủ (⌘N, ⌘K, ⌘S, navigation, ESC)
- Version history per chapter UI
- Find/replace toàn truyện
- Admin page: list users, promote, view audit logs
- Production deploy: Caddyfile, docker-compose lên VPS, backup cron
- Smoke test full flow

**Ship: v1 production live.**

### Effort estimate (1 dev part-time)

| Steps | Effort | Cumulative |
|---|---|---|
| 0–1.5 (scaffold + auth + arch review) | ~1.5 tuần | Week 1.5 |
| 2 (Stories + Dashboard) | ~3 ngày | Week 2 |
| 3 (Editor M0) | ~1 tuần | Week 3 |
| 4 (Story Map) | ~2 tuần | Week 5 |
| 5 (Characters) | ~1.5 tuần | Week 6.5 |
| 6–8 (Rels, Events, World) | ~2 tuần | Week 8.5 |
| 9–10 (Cmd+K, refactor, export) | ~1 tuần | Week 9.5 |
| 11–14 (AI layer) | ~2 tuần | Week 11.5 |
| 15 (Polish + deploy) | ~1 tuần | Week 12.5 |

→ ~12-13 tuần part-time. Stop bất kỳ step nào sau Step 3 đã có tool dùng được.

---

## 9. Done criteria for v1 web

### 9.1 Auth & multi-tenancy
- [ ] User register/login/logout work; session 30 ngày sliding renewal
- [ ] User A không thể đọc/sửa/xóa data của user B qua bất kỳ endpoint nào
- [ ] Admin promote CLI work; admin endpoints reject non-admin
- [ ] Rate limit auth endpoints (10/phút/IP) work

### 9.2 Manual completeness
- [ ] CRUD đầy đủ Storyline / Arc / Event / Character / World / Chapter — không cần AI
- [ ] Tạo 1 truyện trống → viết 10 chương (~30k chữ) **với AI tắt hoàn toàn**
- [ ] Story Map render đúng ở 5+ Arc, 30+ Event, 10+ Character
- [ ] AttributeHistory thêm/sửa/xóa thủ công work
- [ ] Drag-reorder Arc/Event không corrupt data
- [ ] Conflict warning rule hiện banner đúng
- [ ] Export JSON/Markdown 1 story đầy đủ; import JSON tạo story mới đúng

### 9.3 AI optional layer
- [ ] AI toggle ON/OFF per-user, default OFF
- [ ] 4 AI action work với context tier
- [ ] SSE streaming `/api/ai/continue` không buffer-block
- [ ] `/api/ai/finalize-suggest` Diff modal cho phép accept/edit/reject từng item
- [ ] `user_edited` flag được tôn trọng
- [ ] AI key chỉ ở backend (frontend bundle không chứa `LLM_API_KEY`)
- [ ] Audit log không có nội dung prompt/completion
- [ ] Rate limit env-based: `AI_DAILY_LIMIT=0` skip; `>0` enforce 429

### 9.4 Pixel-perfect design fidelity
- [ ] 7 view (Dashboard, Editor, Story Map, Characters, Rel Graph, Events, World Bible) khớp design
- [ ] Topbar + Rail + Statusbar khớp design (trừ statusbar text "SQLite local" → email user)
- [ ] CmdK ⌘K modal khớp design
- [ ] DiffModal khớp design
- [ ] CreateModal đầy đủ tabs (project/storyline/arc/event/character/relationship)
- [ ] Light + dark theme work, toggle giữ state
- [ ] Fonts Lora + JetBrains Mono + Inter load đúng (qua @fontsource)
- [ ] CSS tokens từ `styles.css` được giữ nguyên

### 9.5 Long-form
- [ ] Mở project có 50k+ chữ, 100+ event, 30+ character — UI vẫn responsive (TTI < 2s)
- [ ] Context tier nén đúng, không vượt token budget khi AI ON
- [ ] Auto-save không lag editor (debounce 800ms, không UI freeze)
- [ ] Cmd+K search trên 50k+ chữ trả kết quả < 300ms

### 9.6 Reliability
- [ ] Crash/reload không mất chương đang viết
- [ ] Postgres restart → app reconnect tự động
- [ ] LLM upstream down → AI 503 với message rõ; manual flow vẫn work
- [ ] Migration auto-run khi boot, idempotent
- [ ] pg_dump cron daily, restore script verified

### 9.7 Deployment
- [ ] Single binary `make-story` chứa frontend embed + migrations
- [ ] `docker-compose up` từ clean → app accessible qua Caddy với TLS
- [ ] Health check `/api/health` 200 với db + llm status
- [ ] `.env.example` có đủ variable, không leak secret

### 9.8 Personal usability
- [ ] **User chính (chính bạn) đăng ký account, viết 1 truyện 50k+ chữ trong tool, không phải copy ra Word**
- [ ] Mở lại sau 1 tuần vẫn dùng tiếp được, không lạc

### 9.9 Cắt scope (KHÔNG build v1)

| Feature | Lý do |
|---|---|
| Sharing/collab giữa user | Hard silo — phase sau nếu cần |
| Forgot password | Admin reset DB |
| 2FA / OAuth / SSO | YAGNI cho 1-10 user |
| Mobile responsive | Dev trên desktop |
| Public landing page | Không bán |
| Multi-tenant scale (>100 user) | Self-hosted nhỏ |
| Branch/alternative timeline | Phức tạp, không core |
| Auto inconsistency ngoài rule cứng | Rule cứng đủ |
| Billing | Self-host |

---

## 10. Open questions

Có thể chốt khi viết implementation plan, không block design:

1. CSV/Excel export? — v1 chỉ JSON/Markdown
2. Localized FTS với Vietnamese stemming? — v1 dùng `simple` + pg_trgm; review nếu search precision thấp
3. Rich `@event-mention` ngoài `@character-mention`? — v1 chỉ character; mở rộng sau nếu cần
4. Chapter version history UI rộng tới đâu? — v1 list snapshot + restore-to; diff view sau
5. Admin dashboard chi tiết tới đâu? — v1 list users + promote + view audit; không cần edit user

---

## 11. References

- `docs/spec.md` — product spec gốc (sẽ update mục 12, 13, 14 theo doc này sau khi approve)
- `docs/06-data-model.md` — canonical schema (kế thừa với adaptations Section 3)
- `docs/00-overview.md` — triết lý sản phẩm
- `docs/01-editor.md`, `02-character.md`, `03-event.md`, `04-timeline.md` — module docs
- `docs/05-site-architecture.md` — sitemap (cập nhật routing theo Section 5.1)
- `docs/07-tech-architecture.md` — Wails tech stack (KHÔNG còn áp dụng cho web variant; FE stack giữ lại)
- `docs/design/story-v2/` — design bundle (source of truth pixel-perfect)
- `docs/design/story-v2/project/styles.css` — CSS tokens nguồn
- `docs/design/story-v2/project/data.js` — sample data Lý Thanh Vân (seed v1)
- Top-level `README.md` — sẽ update sau approve để chỉ tới design doc này
