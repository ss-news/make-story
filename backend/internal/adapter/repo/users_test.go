package repo_test

import (
	"context"
	"errors"
	"testing"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestUsersRepoCreateAndFind(t *testing.T) {
	pool := newTestPool(t)
	ctx := context.Background()
	users := repo.NewUsers(pool)

	u, err := users.Create(ctx, "Alice@Example.com", "hash1", "Alice")
	require.NoError(t, err)
	assert.NotEqual(t, "", u.ID.String())
	assert.Equal(t, "Alice@Example.com", u.Email)
	assert.Equal(t, "Alice", u.DisplayName)

	// citext: case-insensitive find by email.
	got, err := users.FindByEmail(ctx, "alice@example.com")
	require.NoError(t, err)
	assert.Equal(t, u.ID, got.ID)
	assert.Equal(t, "hash1", got.PasswordHash)

	got2, err := users.FindByID(ctx, u.ID)
	require.NoError(t, err)
	assert.Equal(t, u.Email, got2.Email)
}

func TestUsersRepoCreateDuplicateEmailReturnsErrEmailTaken(t *testing.T) {
	pool := newTestPool(t)
	ctx := context.Background()
	users := repo.NewUsers(pool)

	_, err := users.Create(ctx, "dup@example.com", "h", "D")
	require.NoError(t, err)

	_, err = users.Create(ctx, "DUP@example.com", "h2", "D2")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrEmailTaken))
}

func TestUsersRepoFindByEmailNotFound(t *testing.T) {
	pool := newTestPool(t)
	ctx := context.Background()
	users := repo.NewUsers(pool)

	_, err := users.FindByEmail(ctx, "nobody@example.com")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrNotFound))
}
