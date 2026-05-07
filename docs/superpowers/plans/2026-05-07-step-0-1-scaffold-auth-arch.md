# Step 0 + Step 1 + Step 1.5 — Scaffold + Auth Shell + Architecture Review

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Spec:** `docs/superpowers/specs/2026-05-07-web-multi-user-design.md`

**Goal:** Đặt nền tảng cho web app: monorepo (`backend/`, `frontend/`, `deploy/`) build & run được; auth shell (register/login/logout/me) hoạt động end-to-end với session cookie; App shell (Topbar + Rail + Statusbar) pixel-perfect khớp design; Go architecture pattern doc chốt convention cho 14 step còn lại.

**Architecture:** Single Go binary `make-story` (chi router + pgx + embed FE static) trước Postgres; FE Vite SPA build vào `frontend/dist` rồi embed qua `embed.FS`. Session lưu Postgres, cookie `sid` HttpOnly+SameSite=Lax. Layered backend: `domain` → `service` → `adapter` (repo/llm) ← `api` handlers. DI bằng `samber/do` instantiate trong `cmd/server/main.go`. Migration auto-run khi boot qua `golang-migrate` + `embed.FS`. Frontend tokens.css = port nguyên CSS variables từ `docs/design/story-v2/project/styles.css`; Tailwind đọc lại qua `var(--token)` để pixel-perfect mà vẫn dùng utility class.

**Tech Stack:**
- Backend: Go 1.23+, `github.com/go-chi/chi/v5`, `github.com/jackc/pgx/v5`, `github.com/golang-migrate/migrate/v4`, `github.com/samber/do/v2`, `github.com/samber/oops`, `github.com/samber/lo`, `log/slog`, `golang.org/x/crypto/bcrypt`, `github.com/go-chi/httprate`, `github.com/go-playground/validator/v10`, testing: `github.com/stretchr/testify`, `github.com/testcontainers/testcontainers-go/modules/postgres`
- Frontend: Vite 5, React 18, TypeScript 5, Tailwind 3, shadcn/ui, `react-router-dom@6`, `zustand`, `@tanstack/react-query`, `react-hook-form` + `zod`, `@fontsource/lora`, `@fontsource/jetbrains-mono`, `@fontsource/inter`, `vitest`, `@testing-library/react`
- Tooling: Docker multi-stage, docker-compose, Caddy, `air` (Go hot reload), GitHub Actions CI

---

## File Structure

### Created in this plan

```
backend/
├── cmd/server/main.go                          # entrypoint
├── internal/
│   ├── app/
│   │   ├── app.go                              # DI wire-up + http.Handler builder
│   │   ├── config.go                           # env → Config struct
│   │   └── logger.go                           # slog factory (json/text by env)
│   ├── api/
│   │   ├── router.go                           # chi.Router builder
│   │   ├── health.go                           # GET /api/health
│   │   ├── auth.go                             # /api/auth/{register,login,logout,me}
│   │   ├── middleware.go                       # SessionLoader, AuthRequired, OriginCheck
│   │   ├── render.go                           # JSON success/error helpers
│   │   ├── static.go                           # embed FE dist + SPA fallback
│   │   └── static/.gitkeep                     # placeholder; CI copies dist here
│   ├── auth/
│   │   ├── password.go                         # bcrypt hash + verify
│   │   └── session.go                          # session id gen + cookie helpers
│   ├── domain/
│   │   ├── user.go                             # User entity
│   │   ├── session.go                          # Session entity
│   │   └── errors.go                           # sentinel errors (ErrNotFound, ErrInvalidCredentials, ...)
│   ├── service/
│   │   └── auth_service.go                     # Register, Login, Logout, ResolveSession
│   ├── adapter/repo/
│   │   ├── pool.go                             # pgxpool factory
│   │   ├── users.go                            # UsersRepo
│   │   └── sessions.go                         # SessionsRepo
│   └── migrations/
│       ├── embed.go                            # //go:embed *.sql
│       ├── runner.go                           # Up(), Down(), Version()
│       ├── 0001_init.up.sql
│       └── 0001_init.down.sql
├── go.mod
├── go.sum
├── .air.toml                                   # hot reload
└── .env.example

frontend/
├── src/
│   ├── api/
│   │   ├── client.ts                           # fetch wrapper (credentials: include)
│   │   └── auth.ts                             # TanStack Query hooks for auth
│   ├── components/
│   │   ├── ui/                                 # shadcn primitives (button, input, label, ...)
│   │   └── shell/
│   │       ├── AppShell.tsx                    # grid wrapper (rows: 40 1fr 22)
│   │       ├── Topbar.tsx                      # pixel-perfect topbar
│   │       ├── Rail.tsx                        # pixel-perfect 56px rail
│   │       └── Statusbar.tsx                   # statusbar (email user, no SQLite path)
│   ├── features/
│   │   └── auth/
│   │       ├── LoginPage.tsx
│   │       ├── RegisterPage.tsx
│   │       └── ProtectedRoute.tsx
│   ├── stores/
│   │   └── auth.ts                             # Zustand auth store
│   ├── styles/
│   │   ├── tokens.css                          # port từ design styles.css (CSS vars only)
│   │   └── globals.css                         # Tailwind base + tokens import
│   ├── lib/
│   │   └── utils.ts                            # cn() helper for shadcn
│   ├── App.tsx                                 # router
│   ├── main.tsx                                # bootstrap
│   └── vite-env.d.ts
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── components.json                             # shadcn config
└── .env.example

deploy/
├── Dockerfile                                  # multi-stage
├── docker-compose.yml
├── Caddyfile
└── .env.example

docs/architecture/
└── go-patterns.md                              # output Step 1.5

.github/workflows/
└── ci.yml

Makefile                                        # repo root
.gitignore                                      # repo root (covers .env, dist/, etc.)
README.md                                       # update existing if present
```

### Modified
- Repo root `README.md` — replace placeholder with quickstart pointing to spec + this plan

---

## Conventions

- **TDD:** test → fail → implement → pass → commit. One behavior per test.
- **Commits:** Conventional Commits (`feat:`, `chore:`, `test:`, `docs:`). Frequent (after every passing task).
- **Go style:** follow `golang-code-style`, `golang-naming`, `golang-error-handling` skills. Wrap errors with `oops.With("key", val).Wrapf(err, "...")`.
- **Pixel-perfect:** All shell components MUST visually match `docs/design/story-v2/project/Web Story.html` rendered against `styles.css`. Compare via inspection of HTML structure + class names; don't render in browser unless asked.
- **Lodash analog (FE):** use `lodash-es` when iterating/transforming collections; avoid manual for-loops.
- **No emoji** in code/docs unless a token (e.g., status icon) explicitly requires it per design.
- **Skill checks before each phase:**
  - Before Task 8 (backend Go work), invoke `golang-project-layout`, `golang-dependency-injection` (samber/do), `golang-error-handling`, `golang-database`, `golang-samber-oops`.
  - Before Task 18 (FE auth pages), invoke `shadcn`, `tailwind-css-patterns`, `vercel-react-best-practices`.
  - Before Task 30 (Step 1.5), invoke `golang-design-patterns`.

---

# Step 0 — Repo scaffold

Goal Step 0: `make dev-be` boots backend trên `:8080`, `GET /api/health` trả `{status:"ok",db:"up"}`. `make dev-fe` boots Vite dev server trên `:5173` proxying `/api` → `:8080`. `make build` produces single Docker image. CI green.

---

### Task 0.1: Repo root files (.gitignore, Makefile skeleton, README)

**Files:**
- Create: `.gitignore`
- Create: `Makefile`
- Modify: `README.md` (top of file)

- [ ] **Step 1: Write `.gitignore`**

```
# Go
backend/bin/
backend/tmp/
backend/coverage.out

# Node
frontend/node_modules/
frontend/dist/

# Embedded static (built artifact)
backend/internal/api/static/dist/

# Env
.env
deploy/.env

# IDE
.idea/
.vscode/
.DS_Store
```

- [ ] **Step 2: Write `Makefile`**

```make
.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "%-18s %s\n", $$1, $$2}'

dev-db: ## Start postgres in docker
	docker run --rm -d --name make-story-pg \
	  -e POSTGRES_USER=makestory -e POSTGRES_PASSWORD=devpass -e POSTGRES_DB=makestory \
	  -p 5432:5432 postgres:16-alpine

dev-db-stop: ## Stop dev postgres
	docker stop make-story-pg || true

dev-be: ## Run backend with hot reload
	cd backend && air

dev-fe: ## Run frontend dev server
	cd frontend && npm run dev

test-be: ## Run backend tests
	cd backend && go test ./...

test-fe: ## Run frontend tests
	cd frontend && npm test -- --run

lint-be: ## Lint backend
	cd backend && go vet ./... && gofmt -l . | (! grep .)

typecheck-fe: ## Frontend type-check
	cd frontend && npm run typecheck

build-fe: ## Build frontend bundle
	cd frontend && npm run build && rm -rf ../backend/internal/api/static/dist && cp -r dist ../backend/internal/api/static/dist

build: build-fe ## Build single docker image
	docker build -f deploy/Dockerfile -t make-story:dev .

up: ## docker-compose up
	cd deploy && docker compose up -d

down: ## docker-compose down
	cd deploy && docker compose down

.PHONY: help dev-db dev-db-stop dev-be dev-fe test-be test-fe lint-be typecheck-fe build-fe build up down
```

- [ ] **Step 3: Update `README.md` top section**

Replace any pre-existing scaffold/placeholder content with:
```markdown
# Make Story — Web (multi-user)

Web app port của Make Story (multi-user, self-hosted nhỏ).

- Spec: [`docs/superpowers/specs/2026-05-07-web-multi-user-design.md`](docs/superpowers/specs/2026-05-07-web-multi-user-design.md)
- Plans: [`docs/superpowers/plans/`](docs/superpowers/plans/)
- Design source of truth: [`docs/design/story-v2/`](docs/design/story-v2/)

## Quickstart (dev)

```bash
make dev-db        # start postgres in docker
make dev-be        # run backend with hot reload (:8080)
make dev-fe        # run frontend (:5173)
```

See `Makefile` for all targets.
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore Makefile README.md
git commit -m "chore: add repo root makefile, gitignore, readme skeleton"
```

---

### Task 0.2: Backend Go module + minimal `main.go` boots

**Files:**
- Create: `backend/go.mod`
- Create: `backend/cmd/server/main.go`
- Create: `backend/internal/app/config.go`
- Create: `backend/internal/app/logger.go`
- Create: `backend/.env.example`
- Create: `backend/.air.toml`
- Test: `backend/internal/app/config_test.go`

- [ ] **Step 1: Init module**

```bash
cd backend && go mod init github.com/duyld/make-story/backend
go get github.com/go-chi/chi/v5@latest
go get github.com/samber/do/v2@latest
go get github.com/samber/oops@latest
go get github.com/samber/lo@latest
go get github.com/jackc/pgx/v5@latest
go get github.com/golang-migrate/migrate/v4@latest
go get github.com/golang-migrate/migrate/v4/database/pgx/v5@latest
go get github.com/golang-migrate/migrate/v4/source/iofs@latest
go get github.com/stretchr/testify@latest
```

- [ ] **Step 2: Write failing test for `Config.Load`**

`backend/internal/app/config_test.go`:
```go
package app_test

import (
	"testing"

	"github.com/duyld/make-story/backend/internal/app"
	"github.com/stretchr/testify/require"
)

func TestConfigLoad_AppliesDefaults(t *testing.T) {
	t.Setenv("DATABASE_URL", "postgres://u:p@localhost:5432/db")
	t.Setenv("SESSION_SECRET", "dev-secret-32-bytes-minimum-okay-now")
	cfg, err := app.LoadConfig()
	require.NoError(t, err)
	require.Equal(t, "8080", cfg.Port)
	require.Equal(t, "info", cfg.LogLevel)
	require.Equal(t, "json", cfg.LogFormat)
	require.Equal(t, 0, cfg.AIDailyLimit)
	require.False(t, cfg.DisableRegistration)
}

func TestConfigLoad_RequiresDatabaseURL(t *testing.T) {
	t.Setenv("DATABASE_URL", "")
	t.Setenv("SESSION_SECRET", "x")
	_, err := app.LoadConfig()
	require.Error(t, err)
}

func TestConfigLoad_RequiresSessionSecret(t *testing.T) {
	t.Setenv("DATABASE_URL", "postgres://u:p@h/d")
	t.Setenv("SESSION_SECRET", "")
	_, err := app.LoadConfig()
	require.Error(t, err)
}
```

Run: `cd backend && go test ./internal/app/...`
Expected: FAIL (package not found / undefined `app.LoadConfig`).

- [ ] **Step 3: Implement `config.go`**

```go
package app

import (
	"os"
	"strconv"

	"github.com/samber/oops"
)

type Config struct {
	Port                string
	DatabaseURL         string
	SessionSecret       string
	LogLevel            string // debug|info|warn|error
	LogFormat           string // json|text
	AllowedOrigins      []string
	DisableRegistration bool
	SeedDemo            bool

	LLMBaseURL      string
	LLMAPIKey       string
	LLMDefaultModel string
	LLMMaxTokens    int
	LLMTimeoutSec   int
	AIDailyLimit    int
}

func LoadConfig() (Config, error) {
	cfg := Config{
		Port:            envOr("PORT", "8080"),
		DatabaseURL:     os.Getenv("DATABASE_URL"),
		SessionSecret:   os.Getenv("SESSION_SECRET"),
		LogLevel:        envOr("LOG_LEVEL", "info"),
		LogFormat:       envOr("LOG_FORMAT", "json"),
		LLMBaseURL:      envOr("LLM_BASE_URL", "https://llm.musia.store/v1"),
		LLMAPIKey:       os.Getenv("LLM_API_KEY"),
		LLMDefaultModel: envOr("LLM_DEFAULT_MODEL", "claude-sonnet-4-5"),
		LLMMaxTokens:    envInt("LLM_MAX_TOKENS", 2048),
		LLMTimeoutSec:   envInt("LLM_TIMEOUT_SEC", 60),
		AIDailyLimit:    envInt("AI_DAILY_LIMIT", 0),
	}
	cfg.DisableRegistration = envBool("DISABLE_REGISTRATION", false)
	cfg.SeedDemo = envBool("SEED_DEMO", false)
	cfg.AllowedOrigins = splitCSV(os.Getenv("ALLOWED_ORIGINS"))

	if cfg.DatabaseURL == "" {
		return Config{}, oops.Errorf("DATABASE_URL is required")
	}
	if cfg.SessionSecret == "" {
		return Config{}, oops.Errorf("SESSION_SECRET is required")
	}
	return cfg, nil
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func envInt(k string, def int) int {
	if v := os.Getenv(k); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envBool(k string, def bool) bool {
	if v := os.Getenv(k); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return def
}

func splitCSV(s string) []string {
	if s == "" {
		return nil
	}
	var out []string
	cur := ""
	for _, r := range s {
		if r == ',' {
			if cur != "" {
				out = append(out, cur)
				cur = ""
			}
			continue
		}
		cur += string(r)
	}
	if cur != "" {
		out = append(out, cur)
	}
	return out
}
```

Run: `cd backend && go test ./internal/app/...`
Expected: PASS.

- [ ] **Step 4: Implement `logger.go`**

```go
package app

import (
	"log/slog"
	"os"
)

func NewLogger(cfg Config) *slog.Logger {
	level := slog.LevelInfo
	switch cfg.LogLevel {
	case "debug":
		level = slog.LevelDebug
	case "warn":
		level = slog.LevelWarn
	case "error":
		level = slog.LevelError
	}
	opts := &slog.HandlerOptions{Level: level}
	if cfg.LogFormat == "text" {
		return slog.New(slog.NewTextHandler(os.Stdout, opts))
	}
	return slog.New(slog.NewJSONHandler(os.Stdout, opts))
}
```

- [ ] **Step 5: Write minimal `cmd/server/main.go` (no router yet)**

```go
package main

import (
	"context"
	"errors"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/duyld/make-story/backend/internal/app"
)

func main() {
	cfg, err := app.LoadConfig()
	if err != nil {
		// Logger not available yet; use stderr.
		slog.New(slog.NewTextHandler(os.Stderr, nil)).Error("config", "err", err)
		os.Exit(1)
	}
	logger := app.NewLogger(cfg)
	slog.SetDefault(logger)

	mux := http.NewServeMux()
	mux.HandleFunc("/api/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"data":{"status":"ok","db":"unknown","llm":"unknown"}}`))
	})

	srv := &http.Server{
		Addr:              ":" + cfg.Port,
		Handler:           mux,
		ReadHeaderTimeout: 10 * time.Second,
	}

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		logger.Info("server starting", "port", cfg.Port)
		if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Error("server failed", "err", err)
			os.Exit(1)
		}
	}()

	<-ctx.Done()
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	_ = srv.Shutdown(shutdownCtx)
	logger.Info("server stopped")
}
```

- [ ] **Step 6: Write `backend/.env.example`**

```
PORT=8080
DATABASE_URL=postgres://makestory:devpass@localhost:5432/makestory?sslmode=disable
SESSION_SECRET=replace-me-with-32-byte-random-hex
LOG_LEVEL=info
LOG_FORMAT=text

LLM_BASE_URL=https://llm.musia.store/v1
LLM_API_KEY=
LLM_DEFAULT_MODEL=claude-sonnet-4-5
LLM_MAX_TOKENS=2048
LLM_TIMEOUT_SEC=60
AI_DAILY_LIMIT=0

DISABLE_REGISTRATION=false
SEED_DEMO=false
ALLOWED_ORIGINS=http://localhost:5173
```

- [ ] **Step 7: Write `backend/.air.toml`**

```toml
root = "."
tmp_dir = "tmp"
[build]
  cmd = "go build -o ./tmp/server ./cmd/server"
  bin = "tmp/server"
  include_ext = ["go", "tmpl", "sql"]
  exclude_dir = ["tmp", "internal/api/static"]
  delay = 500
[log]
  time = true
```

- [ ] **Step 8: Smoke run**

```bash
cd backend && \
  PORT=8080 DATABASE_URL='postgres://x:y@h/d' SESSION_SECRET='dev' \
  go run ./cmd/server &
sleep 1
curl -s http://localhost:8080/api/health
kill %1
```

Expected curl output: `{"data":{"status":"ok","db":"unknown","llm":"unknown"}}`

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold module with config, logger, and stub /api/health"
```

---

### Task 0.3: Replace `http.ServeMux` with chi router + middleware + render helpers

**Files:**
- Create: `backend/internal/api/render.go`
- Create: `backend/internal/api/router.go`
- Create: `backend/internal/api/health.go`
- Create: `backend/internal/api/middleware.go`
- Modify: `backend/cmd/server/main.go`
- Test: `backend/internal/api/health_test.go`
- Test: `backend/internal/api/render_test.go`

- [ ] **Step 1: Write failing test for `render.JSON` & `render.Error`**

`backend/internal/api/render_test.go`:
```go
package api_test

import (
	"net/http/httptest"
	"testing"

	"github.com/duyld/make-story/backend/internal/api"
	"github.com/stretchr/testify/require"
)

func TestJSON_WrapsInDataEnvelope(t *testing.T) {
	rec := httptest.NewRecorder()
	api.JSON(rec, 200, map[string]string{"hello": "world"})
	require.Equal(t, 200, rec.Code)
	require.Equal(t, "application/json; charset=utf-8", rec.Header().Get("Content-Type"))
	require.JSONEq(t, `{"data":{"hello":"world"}}`, rec.Body.String())
}

func TestError_WrapsCodeAndMessage(t *testing.T) {
	rec := httptest.NewRecorder()
	api.Error(rec, 400, "VALIDATION", "bad input", map[string]string{"email": "required"})
	require.Equal(t, 400, rec.Code)
	require.JSONEq(t,
		`{"error":{"code":"VALIDATION","message":"bad input","fields":{"email":"required"}}}`,
		rec.Body.String(),
	)
}
```

Run: `cd backend && go test ./internal/api/...`
Expected: FAIL (package not found).

- [ ] **Step 2: Implement `render.go`**

```go
package api

import (
	"encoding/json"
	"net/http"
)

func JSON(w http.ResponseWriter, status int, data any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{"data": data})
}

type errBody struct {
	Code    string `json:"code"`
	Message string `json:"message"`
	Fields  any    `json:"fields,omitempty"`
}

func Error(w http.ResponseWriter, status int, code, msg string, fields any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(map[string]any{
		"error": errBody{Code: code, Message: msg, Fields: fields},
	})
}
```

Run tests. Note: `json.Encoder.Encode` appends `\n`; use `JSONEq` (already in test). PASS.

- [ ] **Step 3: Write failing test for `/api/health`**

`backend/internal/api/health_test.go`:
```go
package api_test

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/duyld/make-story/backend/internal/api"
	"github.com/stretchr/testify/require"
)

func TestHealth_OK(t *testing.T) {
	r := api.NewRouter(api.RouterDeps{
		HealthDB:  func() bool { return true },
		HealthLLM: func() bool { return false },
	})
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	require.Equal(t, 200, rec.Code)
	require.Contains(t, rec.Body.String(), `"status":"ok"`)
	require.Contains(t, rec.Body.String(), `"db":"up"`)
	require.Contains(t, rec.Body.String(), `"llm":"down"`)
}
```

Run: FAIL.

- [ ] **Step 4: Implement `router.go` + `health.go`**

`backend/internal/api/router.go`:
```go
package api

import (
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

type RouterDeps struct {
	HealthDB  func() bool
	HealthLLM func() bool
}

func NewRouter(deps RouterDeps) http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))

	r.Get("/api/health", healthHandler(deps))
	return r
}
```

`backend/internal/api/health.go`:
```go
package api

import "net/http"

type healthResponse struct {
	Status string `json:"status"`
	DB     string `json:"db"`
	LLM    string `json:"llm"`
}

func healthHandler(deps RouterDeps) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		boolToStr := func(ok bool) string {
			if ok {
				return "up"
			}
			return "down"
		}
		dbOk := deps.HealthDB != nil && deps.HealthDB()
		status := "ok"
		if !dbOk {
			status = "degraded"
		}
		JSON(w, http.StatusOK, healthResponse{
			Status: status,
			DB:     boolToStr(dbOk),
			LLM:    boolToStr(deps.HealthLLM != nil && deps.HealthLLM()),
		})
	}
}
```

Run tests. PASS.

- [ ] **Step 5: Update `main.go` to use router**

Replace `mux` block with:
```go
handler := api.NewRouter(api.RouterDeps{
    HealthDB:  func() bool { return false }, // wired in Step 0.4 + Step 1
    HealthLLM: func() bool { return false },
})
srv := &http.Server{
    Addr:              ":" + cfg.Port,
    Handler:           handler,
    ReadHeaderTimeout: 10 * time.Second,
}
```

Add import `"github.com/duyld/make-story/backend/internal/api"`.

- [ ] **Step 6: Run all tests + smoke**

```bash
cd backend && go test ./...
```
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(backend): add chi router with /api/health and JSON render helpers"
```

---

### Task 0.4: Postgres pool + migration runner stub + wire into health

**Files:**
- Create: `backend/internal/adapter/repo/pool.go`
- Create: `backend/internal/migrations/embed.go`
- Create: `backend/internal/migrations/runner.go`
- Create: `backend/internal/migrations/0001_init.up.sql` (empty placeholder; real content in Task 1.1)
- Create: `backend/internal/migrations/0001_init.down.sql`
- Modify: `backend/cmd/server/main.go`
- Test: `backend/internal/adapter/repo/pool_test.go` (skipped if no DB)

- [ ] **Step 1: Implement pool factory**

`backend/internal/adapter/repo/pool.go`:
```go
package repo

import (
	"context"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/samber/oops"
)

func NewPool(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	cfg, err := pgxpool.ParseConfig(dsn)
	if err != nil {
		return nil, oops.With("dsn_redacted", true).Wrapf(err, "parse pool config")
	}
	cfg.MaxConns = 10
	cfg.MinConns = 1
	cfg.MaxConnLifetime = 30 * time.Minute
	cfg.MaxConnIdleTime = 5 * time.Minute

	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, oops.Wrapf(err, "open pool")
	}
	pingCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()
	if err := pool.Ping(pingCtx); err != nil {
		pool.Close()
		return nil, oops.Wrapf(err, "ping postgres")
	}
	return pool, nil
}
```

- [ ] **Step 2: Stub migration runner**

`backend/internal/migrations/embed.go`:
```go
package migrations

import "embed"

//go:embed *.sql
var FS embed.FS
```

`backend/internal/migrations/runner.go`:
```go
package migrations

import (
	"strings"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/samber/oops"
)

func Up(databaseURL string) error {
	src, err := iofs.New(FS, ".")
	if err != nil {
		return oops.Wrapf(err, "iofs new")
	}
	// golang-migrate's pgx/v5 driver registers under the scheme "pgx5",
	// not "postgres". Rewrite the standard DSN scheme so callers can keep
	// using DATABASE_URL=postgres://...
	migrateURL := databaseURL
	if strings.HasPrefix(migrateURL, "postgres://") {
		migrateURL = "pgx5://" + strings.TrimPrefix(migrateURL, "postgres://")
	} else if strings.HasPrefix(migrateURL, "postgresql://") {
		migrateURL = "pgx5://" + strings.TrimPrefix(migrateURL, "postgresql://")
	}
	m, err := migrate.NewWithSourceInstance("iofs", src, migrateURL)
	if err != nil {
		return oops.Wrapf(err, "migrate new")
	}
	if err := m.Up(); err != nil && err != migrate.ErrNoChange {
		return oops.Wrapf(err, "migrate up")
	}
	return nil
}
```

- [ ] **Step 3: Create empty placeholder migration files**

`0001_init.up.sql`: `-- placeholder; real content in Task 1.1`
`0001_init.down.sql`: `-- placeholder`

- [ ] **Step 4: Wire pool + migrations into `main.go`**

Add after logger creation:
```go
ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
defer stop()

if err := migrations.Up(cfg.DatabaseURL); err != nil {
    logger.Error("migrations failed", "err", err)
    os.Exit(1)
}

pool, err := repo.NewPool(ctx, cfg.DatabaseURL)
if err != nil {
    logger.Error("postgres pool failed", "err", err)
    os.Exit(1)
}
defer pool.Close()

handler := api.NewRouter(api.RouterDeps{
    HealthDB:  func() bool { return pool.Ping(context.Background()) == nil },
    HealthLLM: func() bool { return false },
})
```

Add imports: `"github.com/duyld/make-story/backend/internal/migrations"`, `"github.com/duyld/make-story/backend/internal/adapter/repo"`.

- [ ] **Step 5: Smoke test against real Postgres**

```bash
make dev-db
sleep 2
cd backend && \
  DATABASE_URL='postgres://makestory:devpass@localhost:5432/makestory?sslmode=disable' \
  SESSION_SECRET='dev-secret-32-bytes-aaaaaaaaaaaaaaaaaa' \
  LOG_FORMAT=text \
  go run ./cmd/server &
sleep 2
curl -s http://localhost:8080/api/health | tee /tmp/health.json
kill %1
make dev-db-stop
```

Expected: `{"data":{"status":"ok","db":"up","llm":"down"}}`

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): add pgx pool, migration runner stub, wire DB ping into /api/health"
```

---

### Task 0.5: Frontend Vite + React + TS + Tailwind scaffold

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`, `frontend/tsconfig.node.json`
- Create: `frontend/tailwind.config.ts`, `frontend/postcss.config.js`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`
- Create: `frontend/src/styles/globals.css`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/.env.example`

- [ ] **Step 1: Init Vite project**

```bash
cd frontend && \
  npm create vite@latest . -- --template react-ts -y
```

(If interactive prompts appear, accept defaults.)

- [ ] **Step 2: Install deps**

```bash
npm install react-router-dom@6 zustand @tanstack/react-query \
  react-hook-form @hookform/resolvers zod \
  lodash-es \
  @fontsource/lora @fontsource/jetbrains-mono @fontsource/inter \
  clsx tailwind-merge

npm install -D tailwindcss postcss autoprefixer \
  @types/lodash-es \
  vitest @testing-library/react @testing-library/jest-dom jsdom

npx tailwindcss init -p
```

- [ ] **Step 3: Configure `tailwind.config.ts`**

```ts
import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        paper: 'var(--paper)',
        'paper-2': 'var(--paper-2)',
        'paper-3': 'var(--paper-3)',
        ink: 'var(--ink)',
        'ink-2': 'var(--ink-2)',
        muted: 'var(--muted)',
        'muted-2': 'var(--muted-2)',
        hairline: 'var(--hairline)',
        'hairline-strong': 'var(--hairline-strong)',
        accent: 'var(--accent)',
        'accent-soft': 'var(--accent-soft)',
        warn: 'var(--warn)',
        ok: 'var(--ok)',
        turning: 'var(--turning)',
      },
      fontFamily: {
        mono: 'var(--font-mono)',
        serif: 'var(--font-serif)',
        sans: 'var(--font-sans)',
      },
    },
  },
  plugins: [],
} satisfies Config
```

- [ ] **Step 4: Write `src/styles/globals.css`**

```css
@import './tokens.css';
@import '@fontsource/lora/400.css';
@import '@fontsource/lora/700.css';
@import '@fontsource/jetbrains-mono/400.css';
@import '@fontsource/inter/400.css';
@import '@fontsource/inter/600.css';

@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; margin: 0; }
body {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--ink);
  background: var(--paper);
  -webkit-font-smoothing: antialiased;
  letter-spacing: 0.01em;
}
```

- [ ] **Step 5: Write `src/lib/utils.ts`**

```ts
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```

- [ ] **Step 6: Write `vite.config.ts`**

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8080' },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
```

Create `frontend/src/test/setup.ts`:
```ts
import '@testing-library/jest-dom'
```

Add to `tsconfig.json` `compilerOptions`:
```json
"baseUrl": ".",
"paths": { "@/*": ["src/*"] }
```

- [ ] **Step 7: Write minimal `App.tsx` + `main.tsx`**

`src/App.tsx`:
```tsx
export default function App() {
  return (
    <div className="p-4">
      <h1 className="font-serif text-2xl text-ink">Make Story</h1>
      <p className="text-muted">scaffold ok</p>
    </div>
  )
}
```

`src/main.tsx`:
```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/globals.css'
import App from './App'

createRoot(document.getElementById('root')!).render(
  <StrictMode><App /></StrictMode>,
)
```

- [ ] **Step 8: Add `npm scripts`**

In `frontend/package.json` `scripts`:
```json
"scripts": {
  "dev": "vite",
  "build": "tsc -b && vite build",
  "preview": "vite preview",
  "typecheck": "tsc -b --noEmit",
  "test": "vitest"
}
```

- [ ] **Step 9: Smoke test**

```bash
cd frontend && \
  npm run typecheck && \
  npm run build
```
Expected: type-check passes, `dist/` contains `index.html` + bundled JS.

```bash
cd frontend && npm run dev &
sleep 3
curl -s http://localhost:5173 | grep -q 'Make Story'
kill %1
```

- [ ] **Step 10: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold vite+react+ts+tailwind with token-based theme"
```

---

### Task 0.6: Port `tokens.css` from design + verify visual fidelity primitives

**Files:**
- Create: `frontend/src/styles/tokens.css`

- [ ] **Step 1: Copy CSS variables only from design**

Open `docs/design/story-v2/project/styles.css`. Copy lines 1-46 (the `:root` and `[data-theme="dark"]` blocks) into `frontend/src/styles/tokens.css`. Add comment header:

```css
/* Tokens — ported from docs/design/story-v2/project/styles.css */
/* DO NOT add component styles here; use Tailwind utilities or component-scoped CSS. */

:root {
  /* light */
  --paper: #faf8f3;
  ... (paste exact content from design lines 4-27)
}

[data-theme="dark"] {
  ... (paste exact content from design lines 30-45)
}
```

- [ ] **Step 2: Verify build still succeeds**

```bash
cd frontend && npm run build
```
Expected: PASS.

- [ ] **Step 3: Visual sanity test (no browser, just unit)**

`frontend/src/styles/tokens.test.ts`:
```ts
import { describe, it, expect } from 'vitest'
import fs from 'node:fs'
import path from 'node:path'

describe('tokens.css', () => {
  const tokens = fs.readFileSync(path.resolve(__dirname, 'tokens.css'), 'utf-8')

  it('declares all required light-theme tokens', () => {
    const required = [
      '--paper', '--paper-2', '--paper-3',
      '--ink', '--ink-2', '--muted', '--muted-2',
      '--hairline', '--hairline-strong',
      '--accent', '--accent-soft',
      '--font-mono', '--font-serif', '--font-sans',
    ]
    for (const t of required) {
      expect(tokens).toContain(t)
    }
  })

  it('declares dark theme override', () => {
    expect(tokens).toMatch(/\[data-theme="dark"\]/)
  })
})
```

Run: `cd frontend && npm test -- --run`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/styles/tokens.css frontend/src/styles/tokens.test.ts
git commit -m "feat(frontend): port design tokens.css with verification test"
```

---

### Task 0.7: shadcn init + base primitives (button, input, label)

**Files:** generated by shadcn CLI under `frontend/src/components/ui/`
- Create: `frontend/components.json`

- [ ] **Step 1: Init shadcn**

```bash
cd frontend && npx shadcn@latest init
```
Pick: TypeScript yes, Tailwind config detected, base color `neutral`, CSS variables yes, src dir yes, RSC no.

- [ ] **Step 2: Add primitives needed for auth pages**

```bash
npx shadcn@latest add button input label card form
```

- [ ] **Step 3: Type-check + build**

```bash
npm run typecheck && npm run build
```
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): init shadcn with button/input/label/card/form primitives"
```

---

### Task 0.8: Dockerfile + docker-compose + Caddyfile

**Files:**
- Create: `deploy/Dockerfile`
- Create: `deploy/docker-compose.yml`
- Create: `deploy/Caddyfile`
- Create: `deploy/.env.example`

- [ ] **Step 1: Write `deploy/Dockerfile`** (multi-stage; matches spec §7.1)

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
RUN CGO_ENABLED=0 go build -ldflags='-s -w' -o /out/make-story ./cmd/server

# Stage 3: Runtime
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=be /out/make-story /make-story
EXPOSE 8080
USER nonroot
ENTRYPOINT ["/make-story"]
```

- [ ] **Step 2: Write `deploy/docker-compose.yml`** (matches spec §7.2)

Use exact content from spec §7.2 (already approved). Save as `deploy/docker-compose.yml`. Adjust `build:` path:
```yaml
  app:
    build:
      context: ..
      dockerfile: deploy/Dockerfile
```

- [ ] **Step 3: Write `deploy/Caddyfile`**

Use exact content from spec §7.3.

- [ ] **Step 4: Write `deploy/.env.example`**

```
POSTGRES_PASSWORD=changeme
SESSION_SECRET=replace-me-32-byte-random-hex
LLM_API_KEY=
```

- [ ] **Step 5: Smoke build**

```bash
make build
```
Expected: image `make-story:dev` built successfully.

```bash
docker run --rm make-story:dev --help 2>&1 | head -5
```
(Will likely fail because the binary requires DATABASE_URL; that's fine — image runs.)

- [ ] **Step 6: Commit**

```bash
git add deploy/
git commit -m "feat(deploy): add multi-stage dockerfile, docker-compose, caddyfile"
```

---

### Task 0.9: GitHub Actions CI

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write CI workflow**

```yaml
name: ci
on:
  push: { branches: [main] }
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with: { go-version: '1.23' }
      - name: vet
        run: cd backend && go vet ./...
      - name: gofmt
        run: cd backend && test -z "$(gofmt -l .)"
      - name: test
        run: cd backend && go test ./...

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '22' }
      - name: install
        run: cd frontend && npm ci
      - name: typecheck
        run: cd frontend && npm run typecheck
      - name: test
        run: cd frontend && npm test -- --run
      - name: build
        run: cd frontend && npm run build

  docker:
    runs-on: ubuntu-latest
    needs: [backend, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: build image
        run: docker build -f deploy/Dockerfile -t make-story:ci .
```

- [ ] **Step 2: Verify locally**

```bash
cd backend && go vet ./... && test -z "$(gofmt -l .)" && go test ./...
cd ../frontend && npm run typecheck && npm test -- --run && npm run build
```
Expected: all green.

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "ci: add backend, frontend, and docker build jobs"
```

**STEP 0 DONE.** Tag:
```bash
git tag step-0-scaffold
```

---

# Step 1 — Auth shell + base layout

Goal Step 1: User register/login/logout/me work end-to-end against real Postgres. Session cookie `sid` 30-day sliding. Frontend `/login` and `/register` pages pixel-perfect from design (apply auth-form layout from design system); 401 redirects to `/login`. App shell (Topbar + Rail + Statusbar) renders pixel-perfect on protected `/dashboard` placeholder route. Statusbar shows logged-in email instead of "SQLite local · ~/Library/web-story.db".

---

### Task 1.1: Migration `0001_init.sql` (extensions + users + sessions)

**Files:**
- Modify: `backend/internal/migrations/0001_init.up.sql`
- Modify: `backend/internal/migrations/0001_init.down.sql`

- [ ] **Step 1: Replace `0001_init.up.sql`**

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;

CREATE TABLE users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email         citext UNIQUE NOT NULL,
    password_hash text NOT NULL,
    display_name  text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    is_admin      bool NOT NULL DEFAULT false,
    ai_enabled    bool NOT NULL DEFAULT false
);

CREATE TABLE sessions (
    id           text PRIMARY KEY,
    user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at   timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    expires_at   timestamptz NOT NULL,
    user_agent   text,
    ip           inet
);
CREATE INDEX sessions_user_id_idx ON sessions(user_id);
CREATE INDEX sessions_expires_at_idx ON sessions(expires_at);
```

- [ ] **Step 2: Replace `0001_init.down.sql`**

```sql
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS users;
-- extensions intentionally not dropped (other DBs may share)
```

- [ ] **Step 3: Verify migration applies**

```bash
make dev-db
sleep 2
cd backend && \
  DATABASE_URL='postgres://makestory:devpass@localhost:5432/makestory?sslmode=disable' \
  SESSION_SECRET='dev-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaa' \
  go run ./cmd/server &
sleep 2
docker exec make-story-pg psql -U makestory -d makestory -c '\dt'
kill %1
```

Expected: `users`, `sessions`, `schema_migrations` listed.

- [ ] **Step 4: Commit**

```bash
git add backend/internal/migrations/
git commit -m "feat(db): add 0001_init with users + sessions tables"
```

---

### Task 1.2: Domain entities + sentinel errors

**Files:**
- Create: `backend/internal/domain/user.go`
- Create: `backend/internal/domain/session.go`
- Create: `backend/internal/domain/errors.go`

- [ ] **Step 1: Implement entities**

`domain/user.go`:
```go
package domain

import (
	"time"

	"github.com/google/uuid"
)

type User struct {
	ID           uuid.UUID
	Email        string // canonical lowercase
	PasswordHash string
	DisplayName  string
	CreatedAt    time.Time
	IsAdmin      bool
	AIEnabled    bool
}
```

`domain/session.go`:
```go
package domain

import (
	"time"

	"github.com/google/uuid"
)

type Session struct {
	ID         string // 64-char hex (32 bytes)
	UserID     uuid.UUID
	CreatedAt  time.Time
	LastSeenAt time.Time
	ExpiresAt  time.Time
	UserAgent  string
	IP         string
}

func (s Session) Active(now time.Time) bool {
	return now.Before(s.ExpiresAt)
}
```

`domain/errors.go`:
```go
package domain

import "errors"

var (
	ErrNotFound            = errors.New("not found")
	ErrEmailTaken          = errors.New("email already registered")
	ErrInvalidCredentials  = errors.New("invalid credentials")
	ErrSessionExpired      = errors.New("session expired")
	ErrRegistrationDisabled = errors.New("registration disabled")
	ErrUnauthorized        = errors.New("unauthorized")
)
```

- [ ] **Step 2: Add `google/uuid`**

```bash
cd backend && go get github.com/google/uuid@latest
```

- [ ] **Step 3: Type-check**

```bash
cd backend && go build ./...
```
PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "feat(domain): add User, Session entities and sentinel errors"
```

---

### Task 1.3: Password hashing (TDD)

**Files:**
- Create: `backend/internal/auth/password.go`
- Test: `backend/internal/auth/password_test.go`

- [ ] **Step 1: Failing test**

```go
package auth_test

import (
	"testing"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/stretchr/testify/require"
)

func TestPassword_HashAndVerify(t *testing.T) {
	hash, err := auth.HashPassword("correct horse battery staple")
	require.NoError(t, err)
	require.NotEmpty(t, hash)
	require.NoError(t, auth.VerifyPassword(hash, "correct horse battery staple"))
	require.Error(t, auth.VerifyPassword(hash, "wrong"))
}

func TestPassword_RejectsTooShort(t *testing.T) {
	_, err := auth.HashPassword("short")
	require.Error(t, err)
}
```

Run: FAIL.

- [ ] **Step 2: Implement**

```go
package auth

import (
	"github.com/samber/oops"
	"golang.org/x/crypto/bcrypt"
)

const MinPasswordLen = 8
const BcryptCost = 12

func HashPassword(plain string) (string, error) {
	if len(plain) < MinPasswordLen {
		return "", oops.With("min_len", MinPasswordLen).Errorf("password too short")
	}
	b, err := bcrypt.GenerateFromPassword([]byte(plain), BcryptCost)
	if err != nil {
		return "", oops.Wrapf(err, "bcrypt generate")
	}
	return string(b), nil
}

func VerifyPassword(hash, plain string) error {
	return bcrypt.CompareHashAndPassword([]byte(hash), []byte(plain))
}
```

Run: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/internal/auth/
git commit -m "feat(auth): add bcrypt password hash + verify with min length"
```

---

### Task 1.4: Session ID generation + cookie helpers (TDD)

**Files:**
- Create: `backend/internal/auth/session.go`
- Test: `backend/internal/auth/session_test.go`

- [ ] **Step 1: Failing test**

```go
package auth_test

import (
	"net/http/httptest"
	"testing"
	"time"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/stretchr/testify/require"
)

func TestNewSessionID_Hex64(t *testing.T) {
	id, err := auth.NewSessionID()
	require.NoError(t, err)
	require.Len(t, id, 64)
}

func TestSetSessionCookie_HasSecureFlags(t *testing.T) {
	rec := httptest.NewRecorder()
	exp := time.Now().Add(24 * time.Hour).UTC()
	auth.SetSessionCookie(rec, "abc123", exp, true /*secure*/)
	cookies := rec.Result().Cookies()
	require.Len(t, cookies, 1)
	c := cookies[0]
	require.Equal(t, "sid", c.Name)
	require.Equal(t, "abc123", c.Value)
	require.True(t, c.HttpOnly)
	require.True(t, c.Secure)
	require.Equal(t, "/", c.Path)
}

func TestClearSessionCookie_ExpiresInPast(t *testing.T) {
	rec := httptest.NewRecorder()
	auth.ClearSessionCookie(rec, true)
	c := rec.Result().Cookies()[0]
	require.True(t, c.MaxAge < 0)
}
```

Run: FAIL.

- [ ] **Step 2: Implement**

```go
package auth

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"time"

	"github.com/samber/oops"
)

const SessionCookieName = "sid"
const SessionDuration = 30 * 24 * time.Hour
const SessionRenewWhenLessThan = 7 * 24 * time.Hour

func NewSessionID() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", oops.Wrapf(err, "rand")
	}
	return hex.EncodeToString(b), nil
}

func SetSessionCookie(w http.ResponseWriter, sid string, expires time.Time, secure bool) {
	http.SetCookie(w, &http.Cookie{
		Name:     SessionCookieName,
		Value:    sid,
		Path:     "/",
		Expires:  expires,
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
}

func ClearSessionCookie(w http.ResponseWriter, secure bool) {
	http.SetCookie(w, &http.Cookie{
		Name:     SessionCookieName,
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
}
```

Run: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/internal/auth/
git commit -m "feat(auth): add session id generation and cookie helpers"
```

---

### Task 1.5: Users + Sessions repositories with testcontainers (TDD)

**Files:**
- Create: `backend/internal/adapter/repo/users.go`
- Create: `backend/internal/adapter/repo/sessions.go`
- Create: `backend/internal/adapter/repo/repo_test.go` (shared testcontainers harness)
- Test: `backend/internal/adapter/repo/users_test.go`
- Test: `backend/internal/adapter/repo/sessions_test.go`

- [ ] **Step 1: Add testcontainers**

```bash
cd backend && \
  go get github.com/testcontainers/testcontainers-go@latest && \
  go get github.com/testcontainers/testcontainers-go/modules/postgres@latest
```

- [ ] **Step 2: Shared harness**

`repo/repo_test.go`:
```go
package repo_test

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/migrations"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/testcontainers/testcontainers-go"
	tcpostgres "github.com/testcontainers/testcontainers-go/modules/postgres"
	"github.com/testcontainers/testcontainers-go/wait"
)

func newTestPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	ctx := context.Background()
	if os.Getenv("CI_SKIP_TESTCONTAINERS") == "1" {
		t.Skip("testcontainers disabled")
	}
	c, err := tcpostgres.Run(ctx,
		"postgres:16-alpine",
		tcpostgres.WithDatabase("test"),
		tcpostgres.WithUsername("test"),
		tcpostgres.WithPassword("test"),
		testcontainers.WithWaitStrategy(
			wait.ForLog("database system is ready to accept connections").WithOccurrence(2).
				WithStartupTimeout(60*time.Second)),
	)
	if err != nil {
		t.Fatalf("postgres: %v", err)
	}
	t.Cleanup(func() { _ = c.Terminate(ctx) })

	dsn, err := c.ConnectionString(ctx, "sslmode=disable")
	if err != nil {
		t.Fatal(err)
	}
	if err := migrations.Up(dsn); err != nil {
		t.Fatalf("migrations: %v", err)
	}
	pool, err := repo.NewPool(ctx, dsn)
	if err != nil {
		t.Fatalf("pool: %v", err)
	}
	t.Cleanup(pool.Close)
	_ = filepath.Join // silence unused
	return pool
}
```

- [ ] **Step 3: Failing tests for `UsersRepo`**

```go
package repo_test

import (
	"context"
	"testing"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/stretchr/testify/require"
)

func TestUsersRepo_CreateAndFindByEmail(t *testing.T) {
	pool := newTestPool(t)
	r := repo.NewUsers(pool)
	ctx := context.Background()

	u, err := r.Create(ctx, repo.CreateUserParams{
		Email: "alice@example.com", PasswordHash: "h", DisplayName: "Alice",
	})
	require.NoError(t, err)
	require.NotEmpty(t, u.ID)

	got, err := r.FindByEmail(ctx, "ALICE@example.com") // case-insensitive citext
	require.NoError(t, err)
	require.Equal(t, u.ID, got.ID)
}

func TestUsersRepo_DuplicateEmailReturnsTaken(t *testing.T) {
	pool := newTestPool(t)
	r := repo.NewUsers(pool)
	ctx := context.Background()
	_, err := r.Create(ctx, repo.CreateUserParams{Email: "a@b.com", PasswordHash: "h", DisplayName: "A"})
	require.NoError(t, err)
	_, err = r.Create(ctx, repo.CreateUserParams{Email: "a@b.com", PasswordHash: "h", DisplayName: "A"})
	require.ErrorIs(t, err, domain.ErrEmailTaken)
}

func TestUsersRepo_FindByEmail_NotFound(t *testing.T) {
	pool := newTestPool(t)
	r := repo.NewUsers(pool)
	_, err := r.FindByEmail(context.Background(), "nope@x.com")
	require.ErrorIs(t, err, domain.ErrNotFound)
}
```

Run: FAIL.

- [ ] **Step 4: Implement `UsersRepo`**

```go
package repo

import (
	"context"
	"errors"

	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/samber/oops"
)

type Users struct{ pool *pgxpool.Pool }

func NewUsers(pool *pgxpool.Pool) *Users { return &Users{pool: pool} }

type CreateUserParams struct {
	Email, PasswordHash, DisplayName string
}

func (r *Users) Create(ctx context.Context, p CreateUserParams) (domain.User, error) {
	const q = `INSERT INTO users(email, password_hash, display_name)
	           VALUES($1, $2, $3)
	           RETURNING id, email, password_hash, display_name, created_at, is_admin, ai_enabled`
	var u domain.User
	err := r.pool.QueryRow(ctx, q, p.Email, p.PasswordHash, p.DisplayName).
		Scan(&u.ID, &u.Email, &u.PasswordHash, &u.DisplayName, &u.CreatedAt, &u.IsAdmin, &u.AIEnabled)
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == "23505" {
			return domain.User{}, domain.ErrEmailTaken
		}
		return domain.User{}, oops.Wrapf(err, "insert user")
	}
	return u, nil
}

func (r *Users) FindByEmail(ctx context.Context, email string) (domain.User, error) {
	const q = `SELECT id, email, password_hash, display_name, created_at, is_admin, ai_enabled
	           FROM users WHERE email = $1`
	var u domain.User
	err := r.pool.QueryRow(ctx, q, email).
		Scan(&u.ID, &u.Email, &u.PasswordHash, &u.DisplayName, &u.CreatedAt, &u.IsAdmin, &u.AIEnabled)
	if errors.Is(err, pgx.ErrNoRows) {
		return domain.User{}, domain.ErrNotFound
	}
	if err != nil {
		return domain.User{}, oops.Wrapf(err, "find user by email")
	}
	return u, nil
}

func (r *Users) FindByID(ctx context.Context, id string) (domain.User, error) {
	const q = `SELECT id, email, password_hash, display_name, created_at, is_admin, ai_enabled
	           FROM users WHERE id = $1`
	var u domain.User
	err := r.pool.QueryRow(ctx, q, id).
		Scan(&u.ID, &u.Email, &u.PasswordHash, &u.DisplayName, &u.CreatedAt, &u.IsAdmin, &u.AIEnabled)
	if errors.Is(err, pgx.ErrNoRows) {
		return domain.User{}, domain.ErrNotFound
	}
	if err != nil {
		return domain.User{}, oops.Wrapf(err, "find user by id")
	}
	return u, nil
}
```

Run users tests: PASS.

- [ ] **Step 5: Failing tests + impl for `SessionsRepo`**

`sessions_test.go`:
```go
package repo_test

import (
	"context"
	"testing"
	"time"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/google/uuid"
	"github.com/stretchr/testify/require"
)

func TestSessionsRepo_CreateGetTouchDelete(t *testing.T) {
	pool := newTestPool(t)
	users := repo.NewUsers(pool)
	sess := repo.NewSessions(pool)
	ctx := context.Background()

	u, err := users.Create(ctx, repo.CreateUserParams{Email: "x@y.com", PasswordHash: "h", DisplayName: "X"})
	require.NoError(t, err)

	now := time.Now().UTC()
	created, err := sess.Create(ctx, domain.Session{
		ID: "abc123", UserID: u.ID,
		CreatedAt: now, LastSeenAt: now, ExpiresAt: now.Add(30 * 24 * time.Hour),
		UserAgent: "test", IP: "127.0.0.1",
	})
	require.NoError(t, err)
	require.Equal(t, "abc123", created.ID)

	got, err := sess.Get(ctx, "abc123")
	require.NoError(t, err)
	require.Equal(t, u.ID, got.UserID)

	require.NoError(t, sess.Touch(ctx, "abc123", now.Add(time.Hour), now.Add(31*24*time.Hour)))
	got2, _ := sess.Get(ctx, "abc123")
	require.True(t, got2.LastSeenAt.After(got.LastSeenAt))

	require.NoError(t, sess.Delete(ctx, "abc123"))
	_, err = sess.Get(ctx, "abc123")
	require.ErrorIs(t, err, domain.ErrNotFound)

	// uuid.Nil sentinel for type compile-time assert
	_ = uuid.Nil
}
```

`sessions.go`:
```go
package repo

import (
	"context"
	"errors"
	"time"

	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/samber/oops"
)

type Sessions struct{ pool *pgxpool.Pool }

func NewSessions(pool *pgxpool.Pool) *Sessions { return &Sessions{pool: pool} }

func (r *Sessions) Create(ctx context.Context, s domain.Session) (domain.Session, error) {
	const q = `INSERT INTO sessions(id, user_id, created_at, last_seen_at, expires_at, user_agent, ip)
	           VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING id`
	var id string
	err := r.pool.QueryRow(ctx, q, s.ID, s.UserID, s.CreatedAt, s.LastSeenAt, s.ExpiresAt, s.UserAgent, s.IP).Scan(&id)
	if err != nil {
		return domain.Session{}, oops.Wrapf(err, "insert session")
	}
	return s, nil
}

func (r *Sessions) Get(ctx context.Context, id string) (domain.Session, error) {
	const q = `SELECT id, user_id, created_at, last_seen_at, expires_at, COALESCE(user_agent,''), COALESCE(host(ip),'')
	           FROM sessions WHERE id = $1`
	var s domain.Session
	err := r.pool.QueryRow(ctx, q, id).
		Scan(&s.ID, &s.UserID, &s.CreatedAt, &s.LastSeenAt, &s.ExpiresAt, &s.UserAgent, &s.IP)
	if errors.Is(err, pgx.ErrNoRows) {
		return domain.Session{}, domain.ErrNotFound
	}
	if err != nil {
		return domain.Session{}, oops.Wrapf(err, "get session")
	}
	return s, nil
}

func (r *Sessions) Touch(ctx context.Context, id string, lastSeen, newExpires time.Time) error {
	const q = `UPDATE sessions SET last_seen_at = $2, expires_at = $3 WHERE id = $1`
	_, err := r.pool.Exec(ctx, q, id, lastSeen, newExpires)
	if err != nil {
		return oops.Wrapf(err, "touch session")
	}
	return nil
}

func (r *Sessions) Delete(ctx context.Context, id string) error {
	_, err := r.pool.Exec(ctx, `DELETE FROM sessions WHERE id = $1`, id)
	return err
}
```

Run all repo tests: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(repo): add Users + Sessions repositories with testcontainers harness"
```

---

### Task 1.6: Auth service (TDD)

**Files:**
- Create: `backend/internal/service/auth_service.go`
- Test: `backend/internal/service/auth_service_test.go`

- [ ] **Step 1: Failing tests** (use real Postgres via testcontainers harness — promote `newTestPool` to a small helper package or duplicate the harness file under `service/` for now; cleanup in Task 1.10 if needed.)

Test cases:
- `Register` happy path → returns User + Session
- `Register` rejects duplicate email
- `Register` rejects weak password
- `Register` rejects when `cfg.DisableRegistration`
- `Login` happy path
- `Login` wrong password → `ErrInvalidCredentials`
- `Login` unknown email → `ErrInvalidCredentials` (don't leak existence)
- `ResolveSession` returns user + renews if <7d to expiry
- `ResolveSession` deletes & returns `ErrSessionExpired` if expired
- `Logout` deletes session

Use `require.ErrorIs(t, err, domain.X)`.

Run: FAIL.

- [ ] **Step 2: Implement service**

```go
package service

import (
	"context"
	"errors"
	"strings"
	"time"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/samber/oops"
)

type AuthDeps struct {
	Users               UsersRepo
	Sessions            SessionsRepo
	Now                 func() time.Time
	DisableRegistration bool
}

type UsersRepo interface {
	Create(ctx context.Context, p CreateUserParams) (domain.User, error)
	FindByEmail(ctx context.Context, email string) (domain.User, error)
	FindByID(ctx context.Context, id string) (domain.User, error)
}

type SessionsRepo interface {
	Create(ctx context.Context, s domain.Session) (domain.Session, error)
	Get(ctx context.Context, id string) (domain.Session, error)
	Touch(ctx context.Context, id string, lastSeen, newExpires time.Time) error
	Delete(ctx context.Context, id string) error
}

type CreateUserParams = struct {
	Email, PasswordHash, DisplayName string
}

type AuthService struct{ d AuthDeps }

func NewAuth(d AuthDeps) *AuthService {
	if d.Now == nil {
		d.Now = time.Now
	}
	return &AuthService{d: d}
}

type RegisterInput struct {
	Email, Password, DisplayName, UserAgent, IP string
}

func (s *AuthService) Register(ctx context.Context, in RegisterInput) (domain.User, domain.Session, error) {
	if s.d.DisableRegistration {
		return domain.User{}, domain.Session{}, domain.ErrRegistrationDisabled
	}
	in.Email = strings.ToLower(strings.TrimSpace(in.Email))
	if in.Email == "" || in.DisplayName == "" {
		return domain.User{}, domain.Session{}, oops.Errorf("email and display_name required")
	}
	hash, err := auth.HashPassword(in.Password)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	u, err := s.d.Users.Create(ctx, CreateUserParams{Email: in.Email, PasswordHash: hash, DisplayName: in.DisplayName})
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	sess, err := s.issueSession(ctx, u, in.UserAgent, in.IP)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	return u, sess, nil
}

type LoginInput struct {
	Email, Password, UserAgent, IP string
}

func (s *AuthService) Login(ctx context.Context, in LoginInput) (domain.User, domain.Session, error) {
	in.Email = strings.ToLower(strings.TrimSpace(in.Email))
	u, err := s.d.Users.FindByEmail(ctx, in.Email)
	if errors.Is(err, domain.ErrNotFound) {
		return domain.User{}, domain.Session{}, domain.ErrInvalidCredentials
	}
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	if err := auth.VerifyPassword(u.PasswordHash, in.Password); err != nil {
		return domain.User{}, domain.Session{}, domain.ErrInvalidCredentials
	}
	sess, err := s.issueSession(ctx, u, in.UserAgent, in.IP)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	return u, sess, nil
}

func (s *AuthService) Logout(ctx context.Context, sid string) error {
	return s.d.Sessions.Delete(ctx, sid)
}

func (s *AuthService) ResolveSession(ctx context.Context, sid string) (domain.User, domain.Session, error) {
	sess, err := s.d.Sessions.Get(ctx, sid)
	if errors.Is(err, domain.ErrNotFound) {
		return domain.User{}, domain.Session{}, domain.ErrUnauthorized
	}
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	now := s.d.Now()
	if !sess.Active(now) {
		_ = s.d.Sessions.Delete(ctx, sid)
		return domain.User{}, domain.Session{}, domain.ErrSessionExpired
	}
	// Sliding renewal: if remaining < 7d, extend by 30d.
	if sess.ExpiresAt.Sub(now) < auth.SessionRenewWhenLessThan {
		newExp := now.Add(auth.SessionDuration)
		if err := s.d.Sessions.Touch(ctx, sid, now, newExp); err != nil {
			return domain.User{}, domain.Session{}, err
		}
		sess.LastSeenAt = now
		sess.ExpiresAt = newExp
	} else {
		_ = s.d.Sessions.Touch(ctx, sid, now, sess.ExpiresAt)
		sess.LastSeenAt = now
	}
	u, err := s.d.Users.FindByID(ctx, sess.UserID.String())
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	return u, sess, nil
}

func (s *AuthService) issueSession(ctx context.Context, u domain.User, ua, ip string) (domain.Session, error) {
	id, err := auth.NewSessionID()
	if err != nil {
		return domain.Session{}, err
	}
	now := s.d.Now()
	return s.d.Sessions.Create(ctx, domain.Session{
		ID: id, UserID: u.ID,
		CreatedAt: now, LastSeenAt: now,
		ExpiresAt: now.Add(auth.SessionDuration),
		UserAgent: ua, IP: ip,
	})
}
```

Run service tests: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/internal/service/
git commit -m "feat(service): add AuthService with register/login/logout/resolve session"
```

---

### Task 1.7: Auth middleware (SessionLoader, AuthRequired, OriginCheck)

**Files:**
- Create: `backend/internal/api/middleware.go`
- Test: `backend/internal/api/middleware_test.go`

- [ ] **Step 1: Failing tests for `SessionLoader` + `AuthRequired`**

Cases:
- No `sid` cookie → handler sees `nil` user; `AuthRequired` returns 401
- Valid `sid` → handler sees user; cookie refreshed if renewed
- Expired `sid` → 401, cookie cleared
- `OriginCheck` for state-changing methods rejects mismatched Origin with 403; allows same-origin / no Origin (GET)

- [ ] **Step 2: Implement middleware**

```go
package api

import (
	"context"
	"net/http"
	"slices"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/duyld/make-story/backend/internal/service"
)

type ctxKey int

const (
	ctxUser ctxKey = iota
	ctxSession
)

func UserFrom(ctx context.Context) (domain.User, bool) {
	u, ok := ctx.Value(ctxUser).(domain.User)
	return u, ok
}

func SessionLoader(svc *service.AuthService, secureCookies bool) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c, err := r.Cookie(auth.SessionCookieName)
			if err != nil || c.Value == "" {
				next.ServeHTTP(w, r)
				return
			}
			u, sess, err := svc.ResolveSession(r.Context(), c.Value)
			if err != nil {
				auth.ClearSessionCookie(w, secureCookies)
				next.ServeHTTP(w, r)
				return
			}
			// Refresh cookie expiry on every authenticated request
			auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, secureCookies)
			ctx := context.WithValue(r.Context(), ctxUser, u)
			ctx = context.WithValue(ctx, ctxSession, sess)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

func AuthRequired(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if _, ok := UserFrom(r.Context()); !ok {
			Error(w, http.StatusUnauthorized, "UNAUTHORIZED", "auth required", nil)
			return
		}
		next.ServeHTTP(w, r)
	})
}

func OriginCheck(allowed []string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			switch r.Method {
			case http.MethodGet, http.MethodHead, http.MethodOptions:
				next.ServeHTTP(w, r)
				return
			}
			origin := r.Header.Get("Origin")
			if origin == "" {
				next.ServeHTTP(w, r)
				return
			}
			if len(allowed) == 0 || slices.Contains(allowed, origin) {
				next.ServeHTTP(w, r)
				return
			}
			Error(w, http.StatusForbidden, "ORIGIN", "origin not allowed", nil)
		})
	}
}
```

Run middleware tests: PASS.

- [ ] **Step 3: Commit**

```bash
git add backend/internal/api/
git commit -m "feat(api): add SessionLoader, AuthRequired, OriginCheck middleware"
```

---

### Task 1.8: Auth HTTP handlers + wire into router (TDD)

**Files:**
- Create: `backend/internal/api/auth.go`
- Modify: `backend/internal/api/router.go`
- Test: `backend/internal/api/auth_test.go`

- [ ] **Step 1: Failing tests** (full HTTP roundtrip; spin up router with real `AuthService` against testcontainers pool)

Test cases:
- `POST /api/auth/register` 201 + sets `sid` cookie + body has user
- `POST /api/auth/register` duplicate → 409 `EMAIL_TAKEN`
- `POST /api/auth/register` weak password → 400 `VALIDATION` field `password`
- `POST /api/auth/register` while `DISABLE_REGISTRATION=true` → 403
- `POST /api/auth/login` happy → 200 + cookie
- `POST /api/auth/login` wrong → 401 `INVALID_CREDENTIALS`
- `POST /api/auth/logout` clears cookie + deletes session
- `GET /api/auth/me` no cookie → 401
- `GET /api/auth/me` with cookie → 200 + user

- [ ] **Step 2: Implement handlers**

```go
package api

import (
	"encoding/json"
	"errors"
	"net/http"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/duyld/make-story/backend/internal/service"
)

type authHandlers struct {
	svc           *service.AuthService
	secureCookies bool
}

type registerReq struct {
	Email       string `json:"email"`
	Password    string `json:"password"`
	DisplayName string `json:"display_name"`
}

type userDTO struct {
	ID          string `json:"id"`
	Email       string `json:"email"`
	DisplayName string `json:"display_name"`
	IsAdmin     bool   `json:"is_admin"`
	AIEnabled   bool   `json:"ai_enabled"`
}

func toUserDTO(u domain.User) userDTO {
	return userDTO{ID: u.ID.String(), Email: u.Email, DisplayName: u.DisplayName, IsAdmin: u.IsAdmin, AIEnabled: u.AIEnabled}
}

func (h *authHandlers) register(w http.ResponseWriter, r *http.Request) {
	var in registerReq
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		Error(w, 400, "VALIDATION", "invalid json", nil)
		return
	}
	u, sess, err := h.svc.Register(r.Context(), service.RegisterInput{
		Email: in.Email, Password: in.Password, DisplayName: in.DisplayName,
		UserAgent: r.UserAgent(), IP: r.RemoteAddr,
	})
	switch {
	case errors.Is(err, domain.ErrEmailTaken):
		Error(w, 409, "EMAIL_TAKEN", "email already registered", nil)
		return
	case errors.Is(err, domain.ErrRegistrationDisabled):
		Error(w, 403, "REGISTRATION_DISABLED", "registration disabled", nil)
		return
	case err != nil:
		// Password too short or other validation
		Error(w, 400, "VALIDATION", err.Error(), map[string]string{"password": "min 8 chars"})
		return
	}
	auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, h.secureCookies)
	JSON(w, 201, toUserDTO(u))
}

type loginReq struct {
	Email, Password string
}

func (h *authHandlers) login(w http.ResponseWriter, r *http.Request) {
	var in loginReq
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		Error(w, 400, "VALIDATION", "invalid json", nil)
		return
	}
	u, sess, err := h.svc.Login(r.Context(), service.LoginInput{
		Email: in.Email, Password: in.Password,
		UserAgent: r.UserAgent(), IP: r.RemoteAddr,
	})
	if errors.Is(err, domain.ErrInvalidCredentials) {
		Error(w, 401, "INVALID_CREDENTIALS", "invalid email or password", nil)
		return
	}
	if err != nil {
		Error(w, 500, "INTERNAL", "login failed", nil)
		return
	}
	auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, h.secureCookies)
	JSON(w, 200, toUserDTO(u))
}

func (h *authHandlers) logout(w http.ResponseWriter, r *http.Request) {
	if c, err := r.Cookie(auth.SessionCookieName); err == nil && c.Value != "" {
		_ = h.svc.Logout(r.Context(), c.Value)
	}
	auth.ClearSessionCookie(w, h.secureCookies)
	JSON(w, 200, map[string]string{"status": "ok"})
}

func (h *authHandlers) me(w http.ResponseWriter, r *http.Request) {
	u, ok := UserFrom(r.Context())
	if !ok {
		Error(w, 401, "UNAUTHORIZED", "auth required", nil)
		return
	}
	JSON(w, 200, toUserDTO(u))
}
```

- [ ] **Step 3: Update `router.go` to mount auth routes + middleware**

Extend `RouterDeps`:
```go
type RouterDeps struct {
	HealthDB     func() bool
	HealthLLM    func() bool
	Auth         *service.AuthService
	SecureCookie bool
	AllowedOrigins []string
}
```

In `NewRouter`:
```go
loader := SessionLoader(deps.Auth, deps.SecureCookie)
r.Use(loader)
r.Use(OriginCheck(deps.AllowedOrigins))

ah := &authHandlers{svc: deps.Auth, secureCookies: deps.SecureCookie}

r.Route("/api/auth", func(r chi.Router) {
    // TODO: add httprate.Limit for register/login in Task 1.9
    r.Post("/register", ah.register)
    r.Post("/login", ah.login)
    r.Post("/logout", ah.logout)
    r.Get("/me", ah.me)
})

r.Get("/api/health", healthHandler(deps))
```

- [ ] **Step 4: Wire `AuthService` in `cmd/server/main.go`**

```go
usersRepo := repo.NewUsers(pool)
sessionsRepo := repo.NewSessions(pool)
authSvc := service.NewAuth(service.AuthDeps{
    Users: usersRepo, Sessions: sessionsRepo,
    DisableRegistration: cfg.DisableRegistration,
})

handler := api.NewRouter(api.RouterDeps{
    HealthDB:       func() bool { return pool.Ping(context.Background()) == nil },
    HealthLLM:      func() bool { return false },
    Auth:           authSvc,
    SecureCookie:   os.Getenv("ENV") == "production",
    AllowedOrigins: cfg.AllowedOrigins,
})
```

- [ ] **Step 5: Run all tests**

```bash
cd backend && go test ./...
```
Expected: PASS.

- [ ] **Step 6: Smoke against real DB**

```bash
make dev-db && sleep 2
cd backend && \
  DATABASE_URL='postgres://makestory:devpass@localhost:5432/makestory?sslmode=disable' \
  SESSION_SECRET='dev-secret-aaaaaaaaaaaaaaaaaaaaaaaaaaa' LOG_FORMAT=text \
  go run ./cmd/server &
sleep 2
curl -i -c /tmp/c.txt -H 'Content-Type: application/json' \
  -d '{"email":"alice@example.com","password":"hunter22","display_name":"Alice"}' \
  http://localhost:8080/api/auth/register
curl -i -b /tmp/c.txt http://localhost:8080/api/auth/me
curl -i -b /tmp/c.txt -X POST http://localhost:8080/api/auth/logout
curl -i -b /tmp/c.txt http://localhost:8080/api/auth/me   # expect 401
kill %1 && make dev-db-stop
```

Expected: register 201 + Set-Cookie sid; me 200 with alice; logout 200 + Set-Cookie cleared; me 401.

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat(api): add auth endpoints register/login/logout/me with session cookie"
```

---

### Task 1.9: Rate limit auth endpoints (httprate)

**Files:**
- Modify: `backend/internal/api/router.go`
- Test: `backend/internal/api/auth_ratelimit_test.go`

- [ ] **Step 1: Add `httprate`**

```bash
cd backend && go get github.com/go-chi/httprate@latest
```

- [ ] **Step 2: Failing test** (10 reqs/min/IP on `/api/auth/login`; 11th returns 429)

- [ ] **Step 3: Wire `httprate.Limit`**

```go
import "github.com/go-chi/httprate"
...
r.Route("/api/auth", func(r chi.Router) {
    r.Group(func(r chi.Router) {
        r.Use(httprate.LimitByIP(10, 1*time.Minute))
        r.Post("/register", ah.register)
        r.Post("/login", ah.login)
    })
    r.Post("/logout", ah.logout)
    r.Get("/me", ah.me)
})
```

- [ ] **Step 4: Run tests**

PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/
git commit -m "feat(api): rate-limit auth register/login to 10 req/min/IP"
```

---

### Task 1.10: Frontend — fetch wrapper + auth API + Zustand store

**Files:**
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/stores/auth.ts`
- Test: `frontend/src/api/client.test.ts`

- [ ] **Step 1: Failing test for `apiFetch`**

Verify it includes credentials, throws typed `ApiError` for non-2xx with `error.code`, returns `data` on success.

- [ ] **Step 2: Implement `client.ts`**

```ts
export class ApiError extends Error {
  code: string
  status: number
  fields?: Record<string, string>
  constructor(status: number, code: string, message: string, fields?: Record<string, string>) {
    super(message)
    this.status = status
    this.code = code
    this.fields = fields
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
    ...init,
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const err = body?.error ?? { code: 'UNKNOWN', message: res.statusText }
    throw new ApiError(res.status, err.code, err.message, err.fields)
  }
  return body.data as T
}
```

- [ ] **Step 3: Implement `api/auth.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch, ApiError } from './client'

export type User = {
  id: string; email: string; display_name: string;
  is_admin: boolean; ai_enabled: boolean
}

export const meQueryKey = ['auth', 'me'] as const

export function useMe() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: () => apiFetch<User>('/api/auth/me'),
    retry: (count, err) => !(err instanceof ApiError && err.status === 401) && count < 1,
  })
}

export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { email: string; password: string; display_name: string }) =>
      apiFetch<User>('/api/auth/register', { method: 'POST', body: JSON.stringify(input) }),
    onSuccess: (user) => qc.setQueryData(meQueryKey, user),
  })
}

export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (input: { email: string; password: string }) =>
      apiFetch<User>('/api/auth/login', { method: 'POST', body: JSON.stringify(input) }),
    onSuccess: (user) => qc.setQueryData(meQueryKey, user),
  })
}

export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<{ status: string }>('/api/auth/logout', { method: 'POST' }),
    onSuccess: () => qc.setQueryData(meQueryKey, null),
  })
}
```

- [ ] **Step 4: Zustand auth store** (UI-only flag derived from query; minimal)

```ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

type Theme = 'light' | 'dark'

type AuthUI = {
  theme: Theme
  setTheme: (t: Theme) => void
}

export const useAuthUI = create<AuthUI>()(persist(
  (set) => ({
    theme: 'light',
    setTheme: (theme) => {
      document.body.dataset.theme = theme
      set({ theme })
    },
  }),
  { name: 'make-story-ui' }
))
```

(Auth status comes from TanStack Query, not Zustand. Zustand only for UI prefs.)

- [ ] **Step 5: Run tests + typecheck**

```bash
cd frontend && npm test -- --run && npm run typecheck
```
PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat(frontend): add fetch wrapper, auth react-query hooks, ui store"
```

---

### Task 1.11: Frontend — Login + Register pages (pixel-perfect)

**Files:**
- Create: `frontend/src/features/auth/LoginPage.tsx`
- Create: `frontend/src/features/auth/RegisterPage.tsx`
- Create: `frontend/src/features/auth/ProtectedRoute.tsx`
- Modify: `frontend/src/App.tsx` (add router)
- Test: `frontend/src/features/auth/LoginPage.test.tsx`

**Pixel-perfect note:** Design bundle (`docs/design/story-v2/`) does not include explicit auth pages — they are gated upstream of the authed shell. Implement with minimalist design language matching tokens (paper bg, ink text, hairline border, Lora for headings, mono for inputs). Card centered, 380px wide. Use shadcn primitives.

- [ ] **Step 1: Failing test for LoginPage**

```tsx
import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from './LoginPage'

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LoginPage', () => {
  it('renders email + password fields', () => {
    renderWithProviders(<LoginPage />)
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/mật khẩu/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /đăng nhập/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Implement LoginPage**

```tsx
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLogin } from '@/api/auth'
import { ApiError } from '@/api/client'

const schema = z.object({
  email: z.string().email('Email không hợp lệ'),
  password: z.string().min(8, 'Tối thiểu 8 ký tự'),
})

export default function LoginPage() {
  const nav = useNavigate()
  const login = useLogin()
  const { register, handleSubmit, formState: { errors } } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
  })

  return (
    <div className="min-h-screen flex items-center justify-center bg-paper">
      <form
        onSubmit={handleSubmit(async (v) => {
          try {
            await login.mutateAsync(v)
            nav('/dashboard')
          } catch {/* error rendered below via login.error */}
        })}
        className="w-[380px] border border-hairline bg-paper-2 p-8 space-y-5"
      >
        <h1 className="font-serif text-xl text-ink">Đăng nhập</h1>
        <div className="space-y-1.5">
          <Label htmlFor="email" className="text-muted text-[11px] uppercase tracking-wide">Email</Label>
          <Input id="email" type="email" autoFocus {...register('email')} />
          {errors.email && <p className="text-warn text-xs">{errors.email.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password" className="text-muted text-[11px] uppercase tracking-wide">Mật khẩu</Label>
          <Input id="password" type="password" {...register('password')} />
          {errors.password && <p className="text-warn text-xs">{errors.password.message}</p>}
        </div>
        {login.error instanceof ApiError && (
          <p className="text-warn text-xs">
            {login.error.code === 'INVALID_CREDENTIALS' ? 'Email hoặc mật khẩu sai' : login.error.message}
          </p>
        )}
        <Button type="submit" disabled={login.isPending} className="w-full">
          {login.isPending ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </Button>
        <p className="text-muted text-xs text-center">
          Chưa có tài khoản? <Link to="/register" className="text-accent">Đăng ký</Link>
        </p>
      </form>
    </div>
  )
}
```

- [ ] **Step 3: Implement RegisterPage** (mirror with `display_name` field; `useRegister`; on success `nav('/dashboard')`).

- [ ] **Step 4: ProtectedRoute**

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { useMe } from '@/api/auth'

export default function ProtectedRoute() {
  const { data, isLoading, isError } = useMe()
  if (isLoading) return <div className="p-4 text-muted">…</div>
  if (isError || !data) return <Navigate to="/login" replace />
  return <Outlet />
}
```

- [ ] **Step 5: Wire router in App.tsx**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from './features/auth/LoginPage'
import RegisterPage from './features/auth/RegisterPage'
import ProtectedRoute from './features/auth/ProtectedRoute'
import AppShell from './components/shell/AppShell'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 30_000 } } })

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route path="/dashboard" element={<DashboardPlaceholder />} />
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

function DashboardPlaceholder() {
  return <div className="p-6 font-serif text-ink">Dashboard (Step 2)</div>
}
```

- [ ] **Step 6: Run tests + typecheck**

```bash
cd frontend && npm test -- --run && npm run typecheck && npm run build
```
PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): add login/register pages and protected route"
```

---

### Task 1.12: App shell — Topbar + Rail + Statusbar (pixel-perfect)

**Files:**
- Create: `frontend/src/components/shell/AppShell.tsx`
- Create: `frontend/src/components/shell/Topbar.tsx`
- Create: `frontend/src/components/shell/Rail.tsx`
- Create: `frontend/src/components/shell/Statusbar.tsx`
- Test: `frontend/src/components/shell/AppShell.test.tsx`

**Source of truth:** `docs/design/story-v2/project/Web Story.html` (App component) and the `.app`, `.topbar`, `.rail`, `.statusbar` CSS rules in `styles.css`. Use Tailwind utilities + raw CSS classes when shorter; copy exact dimensions (40px topbar, 56px rail, 22px statusbar).

- [ ] **Step 1: Read design source carefully**

Open `docs/design/story-v2/project/Web Story.html` and read App / Topbar / Rail / Statusbar JSX. Copy class names + structure verbatim. Add inline notes citing line numbers.

- [ ] **Step 2: Write failing test**

```tsx
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, it, expect } from 'vitest'
import AppShell from './AppShell'

// Mock useMe to return a user
vi.mock('@/api/auth', () => ({
  useMe: () => ({ data: { id: '1', email: 'alice@example.com', display_name: 'Alice', is_admin: false, ai_enabled: false } }),
  useLogout: () => ({ mutate: vi.fn() }),
}))

describe('AppShell', () => {
  it('renders topbar, rail, statusbar with email user', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter><AppShell /></MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByText(/alice@example.com/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 3: Implement `AppShell.tsx`**

```tsx
import { Outlet } from 'react-router-dom'
import Topbar from './Topbar'
import Rail from './Rail'
import Statusbar from './Statusbar'

export default function AppShell() {
  return (
    <div className="grid h-screen" style={{ gridTemplateRows: '40px 1fr 22px', gridTemplateColumns: '56px 1fr' }}>
      <div className="col-span-2"><Topbar /></div>
      <Rail />
      <main className="overflow-auto"><Outlet /></main>
      <div className="col-span-2"><Statusbar /></div>
    </div>
  )
}
```

- [ ] **Step 4: Implement `Topbar.tsx`**

Port markup from `Web Story.html` Topbar component verbatim. Bind:
- Brand: "Web Story" (mono, 13px)
- Switcher: shows current story title (placeholder "Lý Thanh Vân" until Step 2)
- Top action buttons: same icons / classes as design
- AI toggle: `.topbar .ai-toggle` with `.on/.off` + `.pulse`

- [ ] **Step 5: Implement `Rail.tsx`**

Port verbatim. 7 nav buttons + theme toggle at bottom. Hook `to` to react-router URLs:
- editor → `/s/:storyId/editor` (disabled until story selected; for Step 1 story is null, render disabled)
- storymap → `/s/:storyId/storymap`
- characters → `/s/:storyId/characters`
- rels → `/s/:storyId/rels`
- events → `/s/:storyId/events`
- world → `/s/:storyId/world`
- settings → `/settings`

For Step 1 (no story selected on `/dashboard`), all rail buttons except dashboard render in disabled visual state per design.

- [ ] **Step 6: Implement `Statusbar.tsx`** (key adaptation)

```tsx
import { useMe } from '@/api/auth'

export default function Statusbar() {
  const { data: user } = useMe()
  return (
    <div className="statusbar flex items-center justify-between px-3 text-[11px] text-muted border-t border-hairline">
      <div className="flex gap-4">
        <span>DỰ ÁN <span className="text-ink">—</span></span>
        <span>CH 0/0</span>
        <span>TỪ 0</span>
        <span>ARC —</span>
      </div>
      <div className="flex gap-4">
        {user && <span>Đăng nhập: <span className="text-ink">{truncate(user.email, 28)}</span></span>}
        <span className="text-ok">● Đã lưu</span>
        <span>v0.1</span>
      </div>
    </div>
  )
}

function truncate(s: string, n: number) {
  return s.length <= n ? s : s.slice(0, n - 1) + '…'
}
```

This implements spec §5.5 explicitly (replace `SQLite local · path` with `Đăng nhập: <email>`).

- [ ] **Step 7: Run tests + typecheck + build**

```bash
cd frontend && npm test -- --run && npm run typecheck && npm run build
```
PASS.

- [ ] **Step 8: Manual smoke (optional)**

```bash
make dev-db && make dev-be &
make dev-fe &
# Browse http://localhost:5173 → /login → register → see shell
```

- [ ] **Step 9: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): add pixel-perfect AppShell (topbar+rail+statusbar) with email statusbar adaptation"
```

**STEP 1 DONE.** Tag:
```bash
git tag step-1-auth-shell
```

---

# Step 1.5 — Architecture review with `golang-design-patterns`

Goal Step 1.5: Lock Go-side conventions for the remaining 13 steps via documented review. Output `docs/architecture/go-patterns.md`. Refactor only on **concrete violations** (not cosmetic).

---

### Task 1.5.1: Invoke `golang-design-patterns` skill on scaffolded code

**Files:**
- Create: `docs/architecture/go-patterns.md`

- [ ] **Step 1: Invoke skill**

Use the Skill tool: `golang-design-patterns`. Provide as input the current backend tree (paths + brief role of each package). Skill output = a structured review with: layer boundaries, DI usage, error chain, repository pattern, HTTP handler pattern, testing pattern, file size signals.

- [ ] **Step 2: Capture review output**

Save the skill's review verbatim into `docs/architecture/go-patterns.md` under headings:
1. Layered architecture & boundaries
2. DI with `samber/do` — when to register vs. instantiate
3. Error handling — `domain` sentinels + `oops` chain
4. Repository pattern — interface placement, transaction handling
5. HTTP handler pattern — DTO ↔ domain mapping, error→status mapping
6. Testing pattern — TDD layers, testcontainers reuse, table-driven
7. File-size signals — split when handler file > 300 lines, service > 400 lines
8. Conventions per upcoming step (Step 2-15)

- [ ] **Step 3: Cross-check with current code**

Walk through current backend code; for each section in the doc, note **concrete violations** found (file:line). Examples to look for:
- `init()` functions doing real work
- Global state (package-level mutable vars)
- Missing `context.Context` in goroutines
- Repository methods returning bare `error` without wrapping
- Handlers calling repos directly (skipping service)

If none found, write "No concrete violations found at this scaffold size; conventions documented for future steps."

- [ ] **Step 4: Commit doc**

```bash
git add docs/architecture/go-patterns.md
git commit -m "docs: lock Go architecture patterns from design-patterns skill review"
```

---

### Task 1.5.2: Apply concrete refactors (only if violations found)

**Files:** depends on findings.

- [ ] **Step 1: For each concrete violation, write a failing test that demonstrates the issue (e.g., race detector flag, missing context propagation)**

Skip this task entirely if Task 1.5.1 Step 3 found no violations.

- [ ] **Step 2: Refactor minimally to pass test**

- [ ] **Step 3: Re-run full test suite**

```bash
cd backend && go test -race ./...
cd ../frontend && npm test -- --run
```
PASS.

- [ ] **Step 4: Commit per violation**

```bash
git commit -m "refactor(<area>): <concrete fix per go-patterns.md §<n>>"
```

**Scope guard reminder:** No cosmetic refactors. No "cleaner if". If skill output is purely advisory with no concrete violations, this task is a no-op and the plan is done.

**STEP 1.5 DONE.** Tag:
```bash
git tag step-1.5-arch-review
```

---

## Done criteria

- [ ] `make build` produces `make-story:dev` Docker image
- [ ] `make dev-db && make dev-be && make dev-fe` brings up working dev stack
- [ ] `curl /api/health` returns `db:up`
- [ ] Register → me → logout flow works end-to-end via curl
- [ ] FE `/login` and `/register` pages render with form validation; submit creates session cookie
- [ ] FE `/dashboard` shows pixel-perfect Topbar + Rail + Statusbar (statusbar shows logged-in email)
- [ ] 401 from any API call redirects to `/login` (verified via direct nav to `/dashboard` without cookie)
- [ ] Auth endpoints rate-limited to 10 req/min/IP
- [ ] CI green on all jobs (backend, frontend, docker)
- [ ] `docs/architecture/go-patterns.md` exists, reviewed, committed
- [ ] All commits follow Conventional Commits; tags `step-0-scaffold`, `step-1-auth-shell`, `step-1.5-arch-review` exist

---

## Open follow-ups (NOT in this plan)

- **Step 2:** Stories CRUD + Dashboard (port `projects.jsx`)
- **Statusbar dynamic data:** chapter count, word count, save indicator (wired progressively in Step 3+)
- **CSRF beyond Origin check:** if needed, double-submit token; deferred until first state-changing endpoint outside `/api/auth/*`
- **i18n infrastructure:** all strings hardcoded vi for Step 1; `react-i18next` setup in Step 2 when first reusable strings appear
