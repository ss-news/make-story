# Go architecture patterns — make-story backend

**Status:** locked at end of Step 1.5. These conventions govern Steps 2–15.
**Reviewer:** standing in for the `golang-design-patterns` skill (skill not installed).
**Scope:** Go backend only (`backend/...`). Frontend has its own conventions.

This document is descriptive of the scaffold landed at the end of Step 1, then prescriptive for everything that follows. Where the scaffold already does the right thing, the rule cites the file as the canonical exemplar. Where the scaffold has a concrete, fixable violation it is listed at the bottom and the relevant rule says "see Concrete violations".

The reader is assumed to know Go. We are not re-explaining Effective Go or `errors.Is`. We are pinning down the *project-specific* shape of those patterns so the next 13 steps don't have to re-litigate them.

---

## 1. Layered architecture & boundaries

### 1.1 The layers

There are exactly six packages a request can pass through:

```
cmd/server          (composition root — main.go only)
   │
   ▼
internal/app        (Config, Logger — no domain logic)
   │
   ▼
internal/api        (chi router, HTTP handlers, middleware, DTOs, JSON envelope)
   │
   ▼
internal/service    (application services — orchestrate domain logic, define repo interfaces)
   │
   ▼
internal/adapter/repo (pgxpool implementations of service-defined interfaces)
   │
   ▼
internal/migrations (embed.FS + golang-migrate; SQL only, no business logic)
```

Three packages cut across all layers:

- `internal/domain` — entities (`User`, `Session`) and sentinel errors (`Err*`). Pure types; no I/O, no third-party deps.
- `internal/auth` — auth primitives (password hashing, session ID generation, cookie helpers). Used by both `service` and `api`. No DB, no chi.
- `internal/testutil` — test harness (`NewTestPool`). Imported only by `_test.go` files.

### 1.2 Allowed import direction

Strictly downward + cross-cutting:

- `cmd/server` may import any internal package (it wires them).
- `api` may import `service`, `auth`, `domain`. **Never `repo` directly.**
- `service` may import `auth`, `domain`. Defines its own repo interfaces; does not import `repo` package.
- `repo` may import `domain`. Implements interfaces defined in `service`.
- `domain` imports nothing from the project (only stdlib + `google/uuid`).
- `auth` may import `domain` (to wrap `domain.Err*`).
- `migrations` is a leaf — embed.FS + the migrate runner only.

Concretely: **a handler in `internal/api` MUST NOT import `internal/adapter/repo`**. If you find yourself reaching for `repo.NewUsers` inside a handler test, you've skipped the service layer — write a service method or a fake.

Exemplar of correct wiring: `cmd/server/main.go:38-61` — `repo` is constructed once, injected into `service.NewAuth`, which is injected into `api.NewRouter`. The router itself never knows `repo` exists.

### 1.3 What goes where — decision table

| Concern | Layer |
|---|---|
| Parse JSON request body | `api` (DTO struct) |
| Validate field shape (length, format) | `api` for shallow shape; `service` for business invariants (e.g. password length is in `auth.HashPassword`) |
| Authorization (ownership check) | `service` first line — see §8 Step 2 |
| SQL query | `repo` |
| Map `pgconn.PgError` codes to `domain.Err*` | `repo` (e.g. `users.go:38-41` maps `23505` to `ErrEmailTaken`) |
| Map `domain.Err*` to HTTP status | `api` (`auth.go:52-65` switch on `errors.Is`) |
| Wrap with `oops` for context | every layer that adds context; bottom layer wraps the raw lib error |
| Compose middleware | `api/router.go` |
| Read env vars | `app/config.go` only |
| Construct services | `cmd/server/main.go` only |

### 1.4 Anti-patterns

- **Handlers calling repos.** Adds an untested code path; `service` is bypassed and ownership checks get duplicated.
- **`service` returning `pgx.ErrNoRows` to `api`.** The handler now has to import `pgx` to switch on the error — a leak. Translate at the repo boundary (see §3, §4).
- **Business logic in `cmd/server`.** `main.go` should be a wiring file. If you find yourself writing `if user.IsAdmin { ... }` in `main.go`, it belongs in a service.
- **Cross-package globals.** No `var globalDB *pgxpool.Pool`. Pass via `Deps` structs.
- **`init()` doing real work.** `init()` is fine for `embed.FS` (`migrations/embed.go`) and constant tables. It is *not* fine for opening DB connections, reading env, or registering HTTP routes.

### 1.5 Verdict on current scaffold

§1 is observed correctly throughout. No violations.

---

## 2. DI with `samber/do` — when to register vs. instantiate

### 2.1 Current state

The plan mentioned `samber/do` as the DI container. **It is not currently a dependency** (`backend/go.mod` lists only `samber/oops` direct and `samber/lo` indirect). The scaffold uses plain constructor injection via `Deps` structs:

```go
authSvc := service.NewAuth(service.AuthDeps{
    Users:               usersRepo,
    Sessions:            sessionsRepo,
    DisableRegistration: cfg.DisableRegistration,
})
```

This is the right call for ~3 services. The cost-benefit of `samber/do` only flips around the time you have ≥ ~8 services, optional features that should be lazily constructed, or a clear test scenario where swapping a single dep out of a graph is painful.

### 2.2 Convention going forward

**Default: keep using `Deps` structs + constructor injection.** Each new service follows the `service.AuthDeps` pattern:

```go
type FooDeps struct {
    Stories StoriesRepo
    Now     func() time.Time   // optional clock injection
}

type FooService struct {
    stories StoriesRepo
    now     func() time.Time
}

func NewFoo(deps FooDeps) *FooService { ... }
```

Exemplar: `internal/service/auth_service.go:31-62`.

**Introduce `samber/do` only when ALL of these are true:**

1. We have ≥ 6 services in `internal/service`.
2. At least one service depends on ≥ 4 others (graph fan-out).
3. We've added optional features (e.g. AI proxy from §6 of the spec) that should be lazily constructed only when their feature flag is on.
4. The wiring section of `main.go` exceeds ~80 lines.

Before adopting it, raise an arch-review note. Don't sprinkle `do.Provide` calls across files speculatively.

### 2.3 If `samber/do` is adopted later

Rules to lock now (so the future migration is mechanical):

- Register everything in `cmd/server/main.go` (or a `cmd/server/wire.go`). No package-level `init()` registrations.
- One injector per process. Pass `*do.Injector` only into `cmd/server`; services receive their concrete deps via the same `FooDeps` structs.
- Services do NOT import `samber/do`. They keep accepting `FooDeps`. The container is a wiring detail, not a dependency of the business logic.
- Reason: this preserves testability — a unit test of `FooService` constructs `FooDeps{}` directly without booting a container.

### 2.4 Anti-patterns

- **Service-locator pattern.** `do.MustInvoke[*UserRepo](injector)` inside a handler. This couples handlers to the container and re-introduces a global.
- **`do.Provide` in `init()`.** Same problem as any other `init()` side effect: the order is opaque, tests can't isolate.
- **Passing the injector down through layers.** If any function below `main.go` takes `*do.Injector`, that's a smell.

### 2.5 Verdict

Scaffold is correct (no `samber/do` yet, doesn't need it).

---

## 3. Error handling — `domain` sentinels + `oops` chain

### 3.1 The pattern

There are two kinds of errors in this codebase:

1. **Sentinel errors** declared in `internal/domain/errors.go`. These are the *vocabulary* of the system — every cross-layer error condition is one of these.
2. **Wrapped library errors** via `samber/oops`. These carry the message chain and structured context but are checked with `errors.Is` against a sentinel for branching decisions.

Existing sentinels (canonical list — `internal/domain/errors.go:7-13`):

```go
ErrNotFound
ErrEmailTaken
ErrInvalidCredentials
ErrSessionExpired
ErrRegistrationDisabled
ErrPasswordTooShort
```

### 3.2 The convention

**Repos translate driver errors to sentinels.** Every `repo` method that returns "not found" returns `domain.ErrNotFound` wrapped with `oops`, never `pgx.ErrNoRows`. Exemplar:

```go
// repo/users.go:60-62
if errors.Is(err, pgx.ErrNoRows) {
    return domain.User{}, oops.Wrapf(domain.ErrNotFound, "users.findByEmail")
}
```

Postgres unique-violation (SQLSTATE `23505`) maps to a domain-specific sentinel:

```go
// repo/users.go:38-41
var pgErr *pgconn.PgError
if errors.As(err, &pgErr) && pgErr.Code == "23505" {
    return domain.User{}, oops.Wrapf(domain.ErrEmailTaken, "users.create email=%s", email)
}
```

**Services may translate sentinels to other sentinels.** When the meaning changes between layers, re-wrap. Exemplar:

```go
// service/auth_service.go:91-95
u, err := s.users.FindByEmail(ctx, email)
if err != nil {
    if errors.Is(err, domain.ErrNotFound) {
        return domain.User{}, domain.Session{}, oops.Wrapf(domain.ErrInvalidCredentials, "login")
    }
    return domain.User{}, domain.Session{}, err
}
```

(`ErrNotFound` becomes `ErrInvalidCredentials` so the handler doesn't leak account enumeration.)

**Handlers map sentinels to HTTP status codes via an `errors.Is` switch.** Exemplar:

```go
// api/auth.go:52-66
switch {
case err == nil:
    auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, secureCookie)
    JSON(w, http.StatusCreated, toUserDTO(u))
case errors.Is(err, domain.ErrEmailTaken):
    Error(w, http.StatusConflict, "EMAIL_TAKEN", "email already registered", nil)
case errors.Is(err, domain.ErrPasswordTooShort):
    Error(w, http.StatusBadRequest, "VALIDATION", "password too short",
        map[string]string{"password": "min 8 characters"})
case errors.Is(err, domain.ErrRegistrationDisabled):
    Error(w, http.StatusForbidden, "REGISTRATION_DISABLED", "registration is disabled", nil)
default:
    Error(w, http.StatusInternalServerError, "INTERNAL", "internal error", nil)
}
```

**The `default:` arm always emits `500 INTERNAL` with no detail.** Anything we want the client to learn must have a sentinel. This is an explicit safety net against leaking driver errors.

### 3.3 `oops` usage rules

- **Wrap once per layer that adds context.** `repo` wraps with the operation name; `service` wraps with the action name; do not double-wrap inside the same function.
- **Use `oops.Wrapf` (not `oops.Errorf`) when wrapping an existing error.** `oops.Errorf` is for new errors that aren't wrapping anything (e.g. `config.go:47` "DATABASE_URL is required").
- **Add structured context with `oops.With(...)` for sensitive values.** `repo/pool.go:14` uses `oops.With("dsn_redacted", true).Wrapf(err, "parse pool config")` — the connection string never appears in the error chain. Apply this anywhere we'd otherwise be tempted to embed PII (email is fine in dev, hash in prod logs is not).
- **`oops` does not change `errors.Is` semantics.** A wrapped `domain.ErrNotFound` still satisfies `errors.Is(err, domain.ErrNotFound)`. Never strip wrapping to "make the comparison work" — the comparison already works.

### 3.4 When to add a new sentinel

Add a sentinel when **at least one of these is true:**

1. The condition needs a non-500 HTTP status code.
2. The condition is referenced by ≥ 2 callers (avoid a sentinel that has exactly one user — just inline it).
3. The condition has a stable wire-format error code (e.g. `EMAIL_TAKEN`).

Add it to `internal/domain/errors.go` alphabetically grouped with related ones. Do not stash sentinels in service or repo packages — they cross layers by definition.

### 3.5 Anti-patterns

- **Bare `return err` from a repo when the cause is `pgx.ErrNoRows`.** Forces upper layers to know about pgx.
- **Comparing strings: `if err.Error() == "not found"`.** Banned. Use `errors.Is`.
- **Returning a generic `errors.New("something")` from service code.** Either use a sentinel or `oops.Errorf` with context — not raw `errors.New`.
- **Catching `error` and re-emitting `errors.New(err.Error())`.** Discards the chain. If you must convert, use `oops.Wrapf`.
- **Logging an error AND returning it.** Either log at the boundary (handler/main) or return; not both. The current scaffold logs only at `cmd/server/main.go` boundaries — keep it that way.

### 3.6 Verdict

Pattern is observed throughout. The one wart is `migrations/runner.go:29` which uses `err != migrate.ErrNoChange` instead of `errors.Is`. See Concrete violations below.

---

## 4. Repository pattern — interface placement, transaction handling

### 4.1 Interface placement (consumer side)

**Repository interfaces are defined in `internal/service`, not in `internal/adapter/repo`.** This is the consumer-side interface pattern: the service declares what it needs; the adapter provides it.

Exemplar:

```go
// service/auth_service.go:17-29
type UsersRepo interface {
    Create(ctx context.Context, email, passwordHash, displayName string) (domain.User, error)
    FindByEmail(ctx context.Context, email string) (domain.User, error)
    FindByID(ctx context.Context, id uuid.UUID) (domain.User, error)
}

type SessionsRepo interface {
    Create(ctx context.Context, sess domain.Session) error
    Get(ctx context.Context, id string) (domain.Session, error)
    Touch(ctx context.Context, id string, lastSeen, newExpires time.Time) error
    Delete(ctx context.Context, id string) error
}
```

The concrete `*repo.Users` (`adapter/repo/users.go:21-23`) implements `service.UsersRepo` structurally — Go's structural interface satisfaction means we don't need an explicit declaration.

**Why consumer-side?** The service knows precisely the methods it uses; the repo is free to expose more. If we ever swap pgx for sqlc-generated code, the test fakes don't change. Conversely, if `repo.Users` exposes a one-off method only used by an admin CLI, the service interface stays minimal.

### 4.2 Repository constructor signature

```go
type Users struct {
    pool *pgxpool.Pool
}

func NewUsers(pool *pgxpool.Pool) *Users {
    return &Users{pool: pool}
}
```

Exemplar: `repo/users.go:16-23`. Rules:

- Always take `*pgxpool.Pool` (not a single `*pgx.Conn`). The pool is per-process, shared across repos.
- Always return a pointer. Repositories carry no value semantics.
- Constructor name is `NewXxx`. No factory functions, no builders.

### 4.3 Method signatures

- **First param is always `context.Context`.** Non-negotiable. Even if the method body doesn't currently need it, future cancellation/tracing will. Exemplar: every method in `repo/users.go`, `repo/sessions.go`.
- **Return `(domain.T, error)` for read paths.** No DTOs at the repo boundary; map to `domain` and only `domain`.
- **Return `error` only for command paths** (`Create`, `Touch`, `Delete`). If the command also needs to surface the new entity (e.g. `INSERT ... RETURNING *`), return `(domain.T, error)`.
- **No transactions in this scaffold yet.** When introduced, see §4.5.

### 4.4 SQL handling

- **Parameterized queries only.** All scaffold queries use `$1, $2, …` placeholders. No string concatenation, no `fmt.Sprintf` of user input into SQL.
- **`const q = ` block at the top of the method.** Exemplar: `repo/users.go:27-31`. Multi-line backtick strings are fine; readable indentation matters more than minimal width.
- **`COALESCE` and `NULLIF` at the SQL boundary** to handle nullable columns without polluting the domain type. Exemplar: `repo/sessions.go:28` (`NULLIF($6, '')`) — empty string in the domain becomes SQL `NULL`, and `repo/sessions.go:43` (`COALESCE(user_agent, '')`) reverses it.
- **No ORM.** `pgx` is the only data-access library. Don't add `gorm`, `ent`, or `sqlx`.

### 4.5 Transactions — convention for upcoming steps

Step 4 (storyline + arc + event reorder) and Step 7 (event/character link) will need multi-row writes. The convention:

- **Add a `Tx` method to a repository when ≥ 2 repos must commit atomically:**
  ```go
  // service-side interface
  type StoriesRepo interface {
      WithTx(ctx context.Context, fn func(tx pgx.Tx) error) error
      // ... other methods
  }
  ```
- **The service orchestrates the transaction.** The service receives a `pgx.Tx` from `WithTx`, calls repo methods that accept the `pgx.Tx`, and the closure's return value drives commit/rollback.
- **Repository methods that need to participate in a transaction take a `pgx.Tx` parameter** (or an interface satisfied by both `*pgxpool.Pool` and `pgx.Tx` — pgx has `pgxtype.Querier` for this; we'll use it).
- **Don't expose `*pgxpool.Pool` outside `repo`.** The service sees only the `WithTx` callback.

This is *not* in the scaffold yet — pin this convention now so Step 4 doesn't reinvent it.

### 4.6 Anti-patterns

- **Returning `*pgx.Rows` from a repository.** That's leaking the iterator; if the caller forgets to close, the pool leaks. Repos should fully drain rows and return `[]domain.T`.
- **`select * from ...`.** Schema drift will silently break struct scanning. List columns explicitly (the scaffold does — see `users.go:30, 51, 71`).
- **Repos calling other repos.** Cross-entity operations belong in `service`. A `Stories` repo that calls `Users.FindByID` should instead let the service do the join or expose `EnsureOwner`.
- **`init()`-time pool creation.** Pool is constructed in `cmd/server/main.go` and threaded through.
- **Returning `nil, nil`.** A successful read either returns a value or `ErrNotFound` — never `nil, nil`.

### 4.7 Verdict

The pattern is implemented correctly. Adding the transaction rule (§4.5) is forward-looking and not yet exercised — first user will be Step 4.

---

## 5. HTTP handler pattern — DTO ↔ domain mapping, error→status mapping

### 5.1 Handler shape

```go
func handleRegister(svc *service.AuthService, secureCookie bool) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        var req registerReq
        if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
            Error(w, http.StatusBadRequest, "VALIDATION", "invalid JSON body", nil)
            return
        }
        u, sess, err := svc.Register(r.Context(), req.Email, req.Password, req.DisplayName, r.UserAgent(), clientIP(r))
        switch { /* errors.Is */ }
    }
}
```

Exemplar: `api/auth.go:44-67`. Conventions:

- **Closure factories**, not methods on a `Handlers` struct. The closure captures the dependencies; the returned `http.HandlerFunc` is the routable handler.
- **DTO struct in the same file as the handler.** `registerReq` lives in `auth.go:33-37`. No separate `dto/` package.
- **Always pass `r.Context()` to the service.** Never `context.Background()` from a handler. (Exception: `_ = svc.Logout(r.Context(), ...)` — but even then, prefer the request context.)
- **Decode then validate.** Decoding failures are 400 VALIDATION; service-layer validation failures are also 400 but with field hints when available.

### 5.2 DTO ↔ domain mapping

Two functions per entity:

```go
type userDTO struct {
    ID          string `json:"id"`
    Email       string `json:"email"`
    DisplayName string `json:"display_name"`
    IsAdmin     bool   `json:"is_admin"`
    AIEnabled   bool   `json:"ai_enabled"`
}

func toUserDTO(u domain.User) userDTO { /* ... */ }
```

Exemplar: `api/auth.go:14-31`.

Rules:

- **DTO struct names end in `DTO` and are unexported.** The HTTP boundary is the only place these exist.
- **Mapping functions are explicit and per-direction:** `toFooDTO(domain.Foo) fooDTO` and `(req fooDTO).toDomain() domain.Foo` (or a free function — pick one, but be consistent within a feature).
- **Never marshal a `domain` struct directly.** Reasons: passwords (`PasswordHash` would leak), zero-value timestamps, unexported uuids — DTO mapping is the firewall.
- **`json:"snake_case"` tags.** Match the spec's `display_name`, `is_admin`, etc. — the existing scaffold uses this.

### 5.3 JSON envelope

Two helpers in `api/render.go`:

```go
func JSON(w http.ResponseWriter, status int, data any)               // → {"data": ...}
func Error(w http.ResponseWriter, status int, code, msg string, fields any)  // → {"error": {...}}
```

**Every successful response is `{"data": ...}`. Every error is `{"error": {"code", "message", "fields?"}}`.** The frontend assumes this envelope; never break it.

`code` is a stable string constant (e.g. `EMAIL_TAKEN`, `VALIDATION`, `UNAUTHORIZED`). It is part of the API contract — changing it breaks clients. New codes need a corresponding sentinel in `domain.errors.go` plus a switch arm.

### 5.4 Middleware

Exemplar `api/middleware.go`:

- **`SessionLoader`** populates `ctxUser` and `ctxSession` (lines 24-44). Failure is silent — anonymous traffic still passes. Fresh cookie is set on every successful resolution to implement sliding renewal.
- **`AuthRequired`** short-circuits with 401 when the context has no user (lines 47-55). Apply per-route, not globally.
- **`OriginCheck`** enforces an allowlist for unsafe methods (lines 59-83). Empty allowlist disables it (useful in tests).
- Context keys are an unexported `ctxKey` type with `iota` values (lines 13-18). Never use a string key — collisions across packages.
- Accessors `UserFrom(ctx)` and `SessionFrom(ctx)` (lines 86-95) return `(T, bool)`. Always check the bool.

Middleware order in `router.go:25-32`:
```
RequestID → RealIP → Recoverer → Timeout → SessionLoader → OriginCheck
```
- `RealIP` must precede anything that reads `r.RemoteAddr` (notably `httprate`).
- `Recoverer` is early so panics in later middleware become 500s, not crashes.
- `Timeout` before `SessionLoader` so a hung DB doesn't lock requests indefinitely.
- `OriginCheck` after `SessionLoader` so we know who they are before deciding origin policy (we currently don't differentiate, but the order matters if we later allow admins to bypass).

### 5.5 Routing

Routes are declared in `api/router.go:NewRouter`. Group route declarations by feature using `r.Route("/api/foo", ...)`. The current example:

```go
r.Route("/api/auth", func(r chi.Router) {
    r.Group(func(r chi.Router) {
        r.Use(httprate.LimitByIP(10, 1*time.Minute))
        r.Post("/register", handleRegister(deps.Auth, deps.SecureCookie))
        r.Post("/login", handleLogin(deps.Auth, deps.SecureCookie))
    })
    r.Post("/logout", handleLogout(deps.Auth, deps.SecureCookie))
    r.Get("/me", handleMe())
})
```

(`api/router.go:37-48`). For Step 2's `/api/stories/*`, follow the same shape.

Per-route rate limits go inside an `r.Group` so the limiter only applies to the wrapped routes. Don't apply rate limits globally.

### 5.6 File size signals

**Split a handler file when it exceeds 300 lines** — one feature, one file:

- `api/auth.go` — auth handlers
- `api/health.go` — health
- `api/stories.go` — Step 2 stories handlers (new)
- `api/chapters.go` — Step 3 (new)
- `api/storymap.go` — Step 4 (new)
- etc.

DTOs live next to the handlers that use them. If a DTO is shared across 2+ handler files, move it to `api/dto.go` (no separate package).

### 5.7 Anti-patterns

- **Calling repos directly from handlers.** Skip the service layer → no ownership check, no business validation, no test isolation.
- **`http.Error(w, ...)`.** Bypasses the JSON envelope. Always use `api.Error`.
- **Reading env in a handler.** Capture the value in `RouterDeps` at boot.
- **Holding state on the router.** The `chi.Router` returned by `NewRouter` is wired once at boot. No `router.UpdateUser(...)` post-construction.
- **Returning `domain.User` directly via `JSON(w, ...)`.** Leaks `PasswordHash`. Use a DTO.
- **Catching panics manually.** `middleware.Recoverer` already does this.

### 5.8 Verdict

Patterns are clean. One concrete violation in `cmd/server/main.go:56` (health probe with no timeout) — see Concrete violations.

---

## 6. Testing pattern — TDD layers, testcontainers reuse, table-driven

### 6.1 Three test layers

| Layer | Lives in | Boots | Speed |
|---|---|---|---|
| Pure unit | `*_test.go` next to the unit | nothing | µs |
| Repo / service integration | same package, `_test.go` | postgres testcontainer | seconds |
| HTTP integration | `api_test` | postgres testcontainer + `httptest.NewRecorder` | seconds |

Examples:

- Pure unit: `auth/password_test.go`, `auth/session_test.go`, `app/config_test.go`, `api/render_test.go`.
- Repo: `repo/users_test.go`, `repo/sessions_test.go` — each calls `newTestPool(t)` (`repo/repo_test.go:11-14` thin wrapper around `testutil.NewTestPool`).
- Service: `service/auth_service_test.go` — uses real repos against a real container.
- HTTP: `api/auth_test.go`, `api/middleware_test.go`, `api/auth_ratelimit_test.go` — wire a real router with real services and real repos.

### 6.2 Test harness

**`testutil.NewTestPool(t)` is the only way to get a postgres pool in a test.** Exemplar: `internal/testutil/pgtest.go:19-49`. It:

1. Honors `CI_SKIP_TESTCONTAINERS=1` by calling `t.Skip` (CI without Docker, fast local feedback for non-DB tests).
2. Boots `postgres:16-alpine` via `tcpostgres.Run` with `BasicWaitStrategies`.
3. Runs `migrations.Up(dsn)` against the fresh container.
4. Returns a connected `*pgxpool.Pool`.
5. Registers `t.Cleanup` to terminate the container and close the pool.

**Each test gets its own container.** No shared state. The cost is ~1s per test for container boot + migration; we accept it. If/when test latency becomes painful (hundreds of integration tests), revisit with a per-package shared container guarded by `sync.Once` — but only when the pain is real.

### 6.3 Table-driven tests — when

**Use sub-tests (`t.Run`) for variants of the same scenario.** Use a table when:

- ≥ 3 cases share setup and structure.
- The cases differ only by inputs/expected outputs.
- A new failure mode would be added by appending a row, not editing logic.

Example pattern (not yet used in scaffold; lock for future):

```go
func TestFoo(t *testing.T) {
    cases := []struct {
        name    string
        input   string
        wantErr error
    }{
        {"happy", "valid", nil},
        {"empty", "", domain.ErrValidation},
    }
    for _, tc := range cases {
        t.Run(tc.name, func(t *testing.T) {
            // ...
        })
    }
}
```

The scaffold deliberately doesn't use tables for short, distinct scenarios (`auth_service_test.go`). That's correct — table-driven is a tool, not a default. Don't force it.

### 6.4 TDD discipline

Step 1 work was done under TDD per the plan. The convention forward:

1. **Red:** write the test that exercises the new behavior; run it and confirm it fails.
2. **Green:** write the minimum code to pass.
3. **Refactor:** clean up while green.

For repos and services, the test layer corresponds to the unit. Don't write a service test that exercises five repos — write a service-level test with fake repos when isolating logic, or accept the integration cost when the test is genuinely about integration (the scaffold takes the integration approach, which is acceptable for ~3 services and significantly increases confidence).

### 6.5 Assertions

`stretchr/testify` is the standard:

- `require` for failures that should stop the test (setup, decode).
- `assert` for failures that allow the test to continue (multiple checks per scenario).

Exemplar mixed usage: `service/auth_service_test.go:30-40`.

Don't import alternative assertion libraries.

### 6.6 Race detection

**All tests pass with `-race`.** The CI command for the test target is:

```bash
cd backend && go test -race ./...
```

If a new test fails under `-race` but passes without, that's a real bug — investigate, don't silence.

The scaffold passes `go test -race ./...` cleanly (verified in this review).

### 6.7 Anti-patterns

- **Sleeping in tests.** `time.Sleep` to wait for async work is a hint that the SUT needs a hook (a channel, an injected clock, a callback). Don't paper over.
- **Test depending on order.** Each test must be runnable in isolation. The current scaffold satisfies this — every test calls `NewTestPool` to get a fresh DB.
- **Asserting log output.** Logs are observability, not API. If you need to verify behavior, expose a metric or a returned value.
- **Hitting real network in unit tests.** Use `httptest.NewServer` for upstream simulation.
- **`init()` in `_test.go` files** that does setup. Use `TestMain` if you absolutely must, but prefer per-test setup.

### 6.8 Verdict

Pattern is clean. Race-free. Containerized-postgres approach is a solid foundation for Step 4+ (which will have larger transactional tests).

---

## 7. File-size signals — split when

These are **signals**, not hard rules. Hitting the threshold doesn't automatically mean split — it means *think about splitting*.

| File type | Soft cap | When to split |
|---|---|---|
| Handler file (`api/<feature>.go`) | 300 lines | When ≥ 5 unrelated endpoints; split by sub-resource |
| Service file (`service/<feature>_service.go`) | 400 lines | When ≥ 7 public methods or ≥ 3 distinct concerns |
| Repo file (`repo/<entity>.go`) | 250 lines | When the entity has ≥ 8 read methods (split into `<entity>_query.go` and `<entity>_command.go`) |
| Router file (`api/router.go`) | 150 lines | Extract per-feature route registration into `api/<feature>_routes.go` |
| Middleware file (`api/middleware.go`) | 200 lines | One middleware per file when files exceed |
| Migration file (`*.sql`) | 200 lines | Split into multiple numbered migrations; never edit a shipped migration |
| Test file | 600 lines | When the file mixes ≥ 3 distinct test subjects |

Current scaffold sizes (lines):
- `api/auth.go`: 121 — fine
- `api/middleware.go`: 95 — fine
- `service/auth_service.go`: 166 — fine
- `repo/users.go`: 86 — fine
- `repo/sessions.go`: 76 — fine
- `app/config.go`: 100 — fine
- `cmd/server/main.go`: 82 — fine; will grow with §8 features (LLM client, more services). Soft cap 200.

When you do split, **prefer same-package siblings over new packages.** Adding a new package adds an import edge; adding a file does not.

---

## 8. Conventions per upcoming step

These are forward-looking pins. They use the established patterns; this section says how to apply them to the specific entities each step introduces.

### 8.1 Step 2 — Stories CRUD + Dashboard

- Migration: `0002_stories.sql` adds `stories` with `owner_user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE` and index. (Plan §3.1.)
- Domain entity: `internal/domain/story.go` — `type Story struct { ID, OwnerUserID uuid.UUID; Title, Slug string; ... }`.
- New sentinels in `domain/errors.go`: `ErrStoryNotFound` (or just keep using `ErrNotFound`; pick one — the scaffold uses generic `ErrNotFound`, follow that).
- Repository: `internal/adapter/repo/stories.go` with `Create`, `List(ctx, ownerID)`, `FindByID`, `Update`, `Delete`. Plus the **first ownership-checking method**: `EnsureOwner(ctx, storyID, userID) error` returning `ErrNotFound` (not `ErrForbidden`) so we don't leak existence.
- Service: `internal/service/stories_service.go`. Every method first calls `s.stories.EnsureOwner(ctx, storyID, userID)` — fail-fast, return `ErrNotFound` to handler, handler emits 404.
- Service-side interface: `StoriesRepo interface { ... }` declared in `service/stories_service.go`, just like `UsersRepo`.
- Handlers: `api/stories.go`. DTOs `storyReq`, `storyDTO`. Routes under `r.Route("/api/stories", ...)`.
- Tests: repo tests + service tests + HTTP tests, mirroring the auth structure.

**Important:** do not add an `ErrForbidden` sentinel. Spec §3.1 explicitly mandates "fail-fast 404" for ownership mismatch — leaking "this exists but you can't see it" is the leak we're avoiding.

### 8.2 Step 3 — Editor M0 (chapters + snapshots)

- Migration: `0003_chapters.sql`. Two tables: `chapters` and `chapter_snapshots`.
- Auto-save with optimistic concurrency: chapter row carries a `version int` column, `PATCH` includes `If-Match: <version>` (or DTO field). Service compares; on mismatch return a new sentinel `ErrVersionMismatch` → handler emits 409.
- The version field is the **first transaction case** — `Patch` reads version + writes new content + bumps version atomically. Use `pgx.Tx` per §4.5. Add `WithTx` to `StoriesRepo` (yes, stories — chapters belong to stories, txs span both).
- TipTap content is stored as `text` (JSON string) per spec §3.2. Don't try to parse on the backend. Store-as-given, return-as-given.

### 8.3 Step 4 — Storyline + Arc + Event CRUD + Story Map

- Migration: `0004_storylines_arcs_events.sql`.
- Reorder endpoints (e.g. `POST /api/storylines/{id}/reorder`) take an array of IDs and update an `order_index` column for all affected rows in a single transaction. This is the canonical multi-row tx case — do it cleanly here, future reorder endpoints copy the pattern.
- Move-event-between-arcs: a single transaction that writes the new `arc_id` and updates `order_index` in both source and destination arcs.

### 8.4 Step 5 — Characters + AttributeHistory + Traits

- Migration: `0005_characters.sql` (4 tables).
- AttributeHistory rows are append-only; never `UPDATE`. The repo exposes `Append(ctx, charID, attr)` only. No `UpdateAttribute` method.
- Character event link table — Step 7 owns the link CRUD; Step 5 just creates the table.

### 8.5 Step 6 — Relationships + Rel Graph

- Migration: `0006_relationships.sql`.
- Relationships are story-scoped — `EnsureOwner(storyID)` first, then operate.

### 8.6 Step 7 — Events list + Detail + character ↔ event link

- Auto-flag crossover characters: a derived field returned by the read endpoint. Compute in the service using a join, not in a trigger.

### 8.7 Step 8 — World Bible

- Migration: `0007_world.sql` (`world_sections` + `world_entries`).
- Sections are story-scoped; entries are section-scoped. Two-level ownership chain — keep `EnsureOwner` at the story level only; entry/section ops join up to story_id and check there.

### 8.8 Step 9 — Cmd+K, search, conflict warnings

- Migration: `0008_search.sql` adds `search_tsv` generated column + GIN index + `pg_trgm`.
- Search service composes a single union-style query over chapters/characters/events/arcs. Single endpoint `GET /api/stories/{sid}/search?q=...`.
- ConflictRules service is pure logic — no DB writes. Inputs: a story aggregate; outputs: list of warnings. **Test it heavily with table-driven tests** — this is the first place tables really pay off.

### 8.9 Step 10 — Refactor ops + Export/Import + Settings

- Split chapter, merge chapters, kill character — multi-row, multi-table transactions. Reuse the §4.5 pattern.
- Export endpoint streams JSON or markdown. Use `io.Copy` from a `pgx.Rows`-driven encoder; do not buffer the whole story into memory.
- Import accepts a JSON upload, validates via DTO, runs in a single transaction. On any error: rollback, return validation details.

### 8.10 Step 11 — AI infrastructure

- Migration: `0009_ai.sql` (`ai_audit`, `ai_usage`, `users.ai_enabled`).
- New package: `internal/adapter/llm/`. The LLM client is an *adapter*, not a *service* — it speaks HTTP to upstream. Service layer wraps it with policy (rate limit, audit log, context building).
- Per spec §6: env vars `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_DEFAULT_MODEL`, etc. — already declared in `app/config.go:20-26`. No code reads them yet.
- This is **the right time to consider `samber/do`** if §2.2's conditions are met. Likely still no — single LLM service + 5 existing services is borderline.

### 8.11 Step 12 — AI 4 actions + SSE streaming

- SSE handlers: detect `Accept: text/event-stream`, switch to streaming mode. Use `http.Flusher`. Write `event: ` / `data: ` lines, flush after each.
- The streaming handler is still a closure factory; the difference is it doesn't return until the upstream is done or context is cancelled.
- Cancellation: `r.Context().Done()` short-circuits the stream. Make sure the upstream HTTP client respects context.

### 8.12 Step 13 — AI Diff Modal

- `user_edited` flag respect: stored on chapter row. AI-suggested changes that touch a `user_edited=true` chapter must include a confirmation roundtrip. Implement as a service-level invariant; surface as `ErrUserEditedConflict` sentinel → 409.

### 8.13 Step 14 — AI Skeleton generator

- Migration not strictly needed; reuses `ai_audit`. Endpoint accepts a project skeleton spec and returns a structured JSON the frontend renders into a wizard.

### 8.14 Step 15 — Polish & deploy

- Add `cmd/make-story/` for CLI subcommands (`user promote`, `db migrate`, etc.) per spec §7.8. CLI commands import `internal/service` directly — they are another composition root, not a duplicate service.
- Production observability: structured slog (already in place), request ID via `middleware.RequestID` (already in place). Add `oops.WithStackTrace` for ERROR level logs only (avoid noisy debug stacks).
- Backup script: nightly `pg_dump`. Out of scope for `internal/` Go code.

### 8.15 Universal step rules

For every step:

1. **Write a migration first**, run it, then write Go.
2. **Add domain entities & sentinels before writing the service.**
3. **Write the service interface inside the service package** — repo follows.
4. **TDD layer order:** repo test → repo impl → service test → service impl → handler test → handler impl.
5. **No new package without a written reason in the PR description.** New packages add import edges; default to a new file in an existing package.
6. **No new dependency without explicit discussion.** The current dep set (`chi`, `pgx`, `migrate`, `samber/oops`, `bcrypt`, `httprate`, `testify`, `testcontainers`) covers steps 2–10 entirely.

---

## 9. Concrete violations found

The scaffold is small (~1100 LoC excluding tests, ~2000 with). Two genuine, fixable violations were found. Two more issues are noted as "watch" but do not warrant a refactor under the plan's "no cosmetic refactors" scope guard.

### 9.1 `migrations/runner.go:29` — `err != migrate.ErrNoChange` should use `errors.Is`

**Severity:** Important.
**Why:** `golang-migrate` documents `ErrNoChange` as a sentinel and we use `errors.Is` everywhere else for sentinel comparison (§3.2). Using `==` is a violation of the project's own §3 rule and breaks if the lib ever wraps the error in a future minor version. Fixed in this review.

### 9.2 `cmd/server/main.go:56` — health probe `pool.Ping(context.Background())` has no timeout

**Severity:** Important.
**Why:** The health endpoint runs the DB ping per request with `context.Background()`. If the DB hangs (network partition, long-running migration on a peer), the ping waits forever. The chi `middleware.Timeout(60*time.Second)` upstream caps the request, but the goroutine running the ping leaks until pgx itself notices the connection is dead — which can be much longer than the request's HTTP deadline. The probe should bound itself to ~2s; if the ping doesn't return in 2s, the DB is effectively down for the purpose of health. Fixed in this review.

### 9.3 (Watch, not refactored) `service/auth_service.go:48` — `AuthService.Now` is exported & mutable

The clock is exported so tests can mutate it after construction (`svc.Now = func() time.Time { ... }` in `auth_service_test.go:129`, etc.). The pattern works under `go test -race` because no test mutates `Now` while concurrent traffic is hitting the same instance.

It's still a smell: a public mutable function field on a struct that lives behind concurrent HTTP handlers. The idiomatic fix is to make `Now` unexported, accept it only via `AuthDeps.Now`, and add a test-only `WithNow(func() time.Time)` setter or rebuild the service per test scenario.

**Why not refactored:** the plan's scope guard explicitly bans cosmetic refactors. This is closer to ergonomic-vs-disciplined than to a real bug. Documented here so future work prefers the unexported pattern (see §2.2 — new services should declare `now func() time.Time` unexported).

### 9.4 (Watch, not refactored) `service/auth_service.go:125` — best-effort cleanup uses request context

`ResolveSession` calls `s.sessions.Delete(ctx, sess.ID)` to clean up an expired session, with `_ =` discarding the error. If the request's context has been cancelled (client disconnected mid-resolve), the cleanup is silently dropped and the row remains expired-but-undeleted until the next resolve. A nightly cron / scheduled cleanup will sweep these eventually.

The idiomatic fix would be `cleanCtx, cancel := context.WithTimeout(context.WithoutCancel(ctx), 2*time.Second)` (Go 1.21+) for fire-and-forget cleanup. Trivial to apply.

**Why not refactored:** the practical impact is bounded (rare race, idempotent next pass, eventual cleanup acceptable). Documented; revisit if Step 11/12 audit logging shows expired-row buildup.

---

## 10. Summary

The scaffold is a clean, idiomatic Go service. Layer boundaries are respected. Errors flow through `domain` sentinels with `oops` context. Repos are correctly behind consumer-side interfaces. Handlers use closure factories with DTO mapping and a sentinel-driven error switch. Tests run on real Postgres via `testcontainers` with a `CI_SKIP_TESTCONTAINERS=1` escape hatch. `go test -race ./...` is green. `go vet` is clean. `gofmt` is clean.

Two concrete violations fixed (§9.1, §9.2). Two minor concerns documented (§9.3, §9.4) but not refactored per scope guard.

The conventions in this document are now load-bearing for Steps 2–15. Deviations should be discussed in PRs that propose them, not silently introduced.
