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

// Sessions provides persistence operations for sessions.
type Sessions struct {
	pool *pgxpool.Pool
}

// NewSessions constructs a Sessions repository backed by the given pool.
func NewSessions(pool *pgxpool.Pool) *Sessions {
	return &Sessions{pool: pool}
}

// Create inserts a new session row.
func (s *Sessions) Create(ctx context.Context, sess domain.Session) error {
	const q = `
		INSERT INTO sessions (id, user_id, created_at, last_seen_at, expires_at, user_agent, ip)
		VALUES ($1, $2, $3, $4, $5, NULLIF($6, ''), NULLIF($7, '')::inet)
	`
	if _, err := s.pool.Exec(ctx, q,
		sess.ID, sess.UserID, sess.CreatedAt, sess.LastSeenAt, sess.ExpiresAt,
		sess.UserAgent, sess.IP,
	); err != nil {
		return oops.Wrapf(err, "sessions.create")
	}
	return nil
}

// Get returns the session with the given id. Returns domain.ErrNotFound if missing.
func (s *Sessions) Get(ctx context.Context, id string) (domain.Session, error) {
	const q = `
		SELECT id, user_id, created_at, last_seen_at, expires_at,
		       COALESCE(user_agent, ''), COALESCE(host(ip), '')
		FROM sessions WHERE id = $1
	`
	var out domain.Session
	err := s.pool.QueryRow(ctx, q, id).Scan(
		&out.ID, &out.UserID, &out.CreatedAt, &out.LastSeenAt, &out.ExpiresAt,
		&out.UserAgent, &out.IP,
	)
	if err != nil {
		if errors.Is(err, pgx.ErrNoRows) {
			return domain.Session{}, oops.Wrapf(domain.ErrNotFound, "sessions.get")
		}
		return domain.Session{}, oops.Wrapf(err, "sessions.get")
	}
	return out, nil
}

// Touch updates the session's last_seen_at and expires_at timestamps.
func (s *Sessions) Touch(ctx context.Context, id string, lastSeen, newExpires time.Time) error {
	const q = `UPDATE sessions SET last_seen_at = $2, expires_at = $3 WHERE id = $1`
	if _, err := s.pool.Exec(ctx, q, id, lastSeen, newExpires); err != nil {
		return oops.Wrapf(err, "sessions.touch")
	}
	return nil
}

// Delete removes the session with the given id (no error if absent).
func (s *Sessions) Delete(ctx context.Context, id string) error {
	const q = `DELETE FROM sessions WHERE id = $1`
	if _, err := s.pool.Exec(ctx, q, id); err != nil {
		return oops.Wrapf(err, "sessions.delete")
	}
	return nil
}
