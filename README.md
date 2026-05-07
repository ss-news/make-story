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

## Cấu trúc repo

```
web_story/
├── docs/
│   ├── design/                      # Bundle gốc từ Claude Design (claude.ai/design)
│   │   └── story-v2/
│   │       ├── README.md            # Hướng dẫn cho coding agent
│   │       ├── chats/               # Chat transcript design
│   │       └── project/             # HTML/JSX/CSS prototype + spec docs
│   │           ├── *.jsx            # 11 component file (~5,600 dòng)
│   │           ├── styles.css
│   │           ├── data.js          # sample data (Lý Thanh Vân)
│   │           └── uploads/         # spec markdown từ user
│   │
│   └── architecture/                # Tài liệu triển khai sang Go + React + Postgres
│       ├── README.md                # Index
│       ├── 01-architecture.md       # Stack, layout repo, deployment topology
│       ├── 02-database-schema.md    # Postgres DDL, indexes, invariants
│       ├── 03-api-spec.md           # REST endpoint spec (~80 endpoint)
│       ├── 04-frontend.md           # React module breakdown, routes, state
│       ├── 05-decisions.md          # ADR — vì sao chọn từng cái
│       └── 06-auth.md               # Auth basic — session cookie + bcrypt
│
└── README.md                        # File này
```

## Bắt đầu từ đâu

1. Đọc [`docs/design/story-v2/README.md`](docs/design/story-v2/README.md) — hướng dẫn từ Claude Design.
2. Đọc transcript thiết kế [`docs/design/story-v2/chats/chat1.md`](docs/design/story-v2/chats/chat1.md) — bối cảnh + ý đồ user.
3. Đọc spec sản phẩm [`docs/design/story-v2/project/uploads/`](docs/design/story-v2/project/uploads/) — đặc biệt [`spec.md`](docs/design/story-v2/project/uploads/spec.md) và [`06-data-model.md`](docs/design/story-v2/project/uploads/06-data-model.md).
4. Đọc kiến trúc triển khai [`docs/architecture/`](docs/architecture/) — bắt đầu từ [`01-architecture.md`](docs/architecture/01-architecture.md).

## Phạm vi v1

- Multi-user (≥2) với auth basic: session cookie + bcrypt. Mỗi story thuộc 1 owner.
- Nạp sẵn dữ liệu mẫu (Lý Thanh Vân — tiên hiệp), gắn user `demo`.
- 7 module chính: Dashboard · Editor · Story Map · Nhân vật · Quan hệ · Events · World Bible.
- AI proxy qua backend (Anthropic), browser không giữ key.

**Chưa làm v1:** OAuth, 2FA, forgot-password, role-based access, sharing/collaboration. Xem [`docs/architecture/06-auth.md §1`](docs/architecture/06-auth.md#1-yêu-cầu).

## Bước tiếp theo (chưa thực hiện)

1. Scaffold `backend/` (chi + pgx + migrate) và `frontend/` (Vite + React).
2. Viết migration `0001_init.sql` (entity tables) + `0002_auth.up.sql` (users/sessions/audit + cột `stories.owner_user_id`).
3. **M0 — Auth:** handlers `/api/auth/*`, middleware `Session` + `AuthRequired`, frontend `/login` + auth gate.
4. Viết seed SQL từ `docs/design/story-v2/project/data.js` (kèm seed user `demo`).
5. **M1 — Read-only endpoint** đủ để render UI từ DB thay vì `window.SEED`.
6. Port `*.jsx` từ prototype → ES modules dưới `frontend/src/`.

Khi user đồng ý chuyển sang implement, scaffold sẽ làm theo đúng layout trong [`01-architecture.md §3`](docs/architecture/01-architecture.md#3-repo-layout).
