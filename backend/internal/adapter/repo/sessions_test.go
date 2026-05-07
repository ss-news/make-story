package repo_test

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestSessionsRepoLifecycle(t *testing.T) {
	pool := newTestPool(t)
	ctx := context.Background()

	users := repo.NewUsers(pool)
	sessions := repo.NewSessions(pool)

	u, err := users.Create(ctx, "session@example.com", "hash", "Sessy")
	require.NoError(t, err)

	now := time.Now().UTC().Truncate(time.Second)
	expires := now.Add(30 * 24 * time.Hour)
	sess := domain.Session{
		ID:         "sid-abc",
		UserID:     u.ID,
		CreatedAt:  now,
		LastSeenAt: now,
		ExpiresAt:  expires,
		UserAgent:  "test-agent",
		IP:         "127.0.0.1",
	}
	require.NoError(t, sessions.Create(ctx, sess))

	got, err := sessions.Get(ctx, "sid-abc")
	require.NoError(t, err)
	assert.Equal(t, u.ID, got.UserID)
	assert.Equal(t, "test-agent", got.UserAgent)
	assert.Equal(t, "127.0.0.1", got.IP)

	// Touch updates last_seen_at and expires_at.
	newSeen := now.Add(time.Hour)
	newExp := now.Add(60 * 24 * time.Hour)
	require.NoError(t, sessions.Touch(ctx, "sid-abc", newSeen, newExp))

	got2, err := sessions.Get(ctx, "sid-abc")
	require.NoError(t, err)
	assert.WithinDuration(t, newSeen, got2.LastSeenAt, time.Second)
	assert.WithinDuration(t, newExp, got2.ExpiresAt, time.Second)

	// Delete removes it.
	require.NoError(t, sessions.Delete(ctx, "sid-abc"))
	_, err = sessions.Get(ctx, "sid-abc")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrNotFound))
}

func TestSessionsRepoGetUnknownReturnsErrNotFound(t *testing.T) {
	pool := newTestPool(t)
	ctx := context.Background()
	sessions := repo.NewSessions(pool)

	_, err := sessions.Get(ctx, "missing")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrNotFound))
}
