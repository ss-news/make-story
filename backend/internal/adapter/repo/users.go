package repo

import (
	"context"
	"errors"

	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/samber/oops"
)

// Users provides persistence operations for user entities.
type Users struct {
	pool *pgxpool.Pool
}

// NewUsers constructs a Users repository backed by the given pool.
func NewUsers(pool *pgxpool.Pool) *Users {
	return &Users{pool: pool}
}

// Create inserts a new user. Returns domain.ErrEmailTaken if the email is already registered.
func (u *Users) Create(ctx context.Context, email, passwordHash, displayName string) (domain.User, error) {
	const q = `
		INSERT INTO users (email, password_hash, display_name)
		VALUES ($1, $2, $3)
		RETURNING id, email, password_hash, display_name, created_at, is_admin, ai_enabled
	`
	var out domain.User
	err := u.pool.QueryRow(ctx, q, email, passwordHash, displayName).Scan(
		&out.ID, &out.Email, &out.PasswordHash, &out.DisplayName,
		&out.CreatedAt, &out.IsAdmin, &out.AIEnabled,
	)
	if err != nil {
		var pgErr *pgconn.PgError
		if errors.As(err, &pgErr) && pgErr.Code == "23505" {
			return domain.User{}, oops.Wrapf(domain.ErrEmailTaken, "users.create email=%s", email)
		}
		return domain.User{}, oops.Wrapf(err, "users.create")
	}
	return out, nil
}

// FindByEmail returns the user with the given email (case-insensitive via citext).
// Returns domain.ErrNotFound if no row matches.
func (u *Users) FindByEmail(ctx context.Context, email string) (domain.User, error) {
	const q = `
		SELECT id, email, password_hash, display_name, created_at, is_admin, ai_enabled
		FROM users WHERE email = $1
	`
	var out domain.User
	err := u.pool.QueryRow(ctx, q, email).Scan(
		&out.ID, &out.Email, &out.PasswordHash, &out.DisplayName,
		&out.CreatedAt, &out.IsAdmin, &out.AIEnabled,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.User{}, oops.Wrapf(domain.ErrNotFound, "users.findByEmail")
		}
		return domain.User{}, oops.Wrapf(err, "users.findByEmail")
	}
	return out, nil
}

// FindByID returns the user with the given id. Returns domain.ErrNotFound if missing.
func (u *Users) FindByID(ctx context.Context, id uuid.UUID) (domain.User, error) {
	const q = `
		SELECT id, email, password_hash, display_name, created_at, is_admin, ai_enabled
		FROM users WHERE id = $1
	`
	var out domain.User
	err := u.pool.QueryRow(ctx, q, id).Scan(
		&out.ID, &out.Email, &out.PasswordHash, &out.DisplayName,
		&out.CreatedAt, &out.IsAdmin, &out.AIEnabled,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.User{}, oops.Wrapf(domain.ErrNotFound, "users.findByID")
		}
		return domain.User{}, oops.Wrapf(err, "users.findByID")
	}
	return out, nil
}
