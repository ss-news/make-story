package repo_test

import (
	"testing"

	"github.com/duyld/make-story/backend/internal/testutil"
	"github.com/jackc/pgx/v5/pgxpool"
)

// newTestPool boots a fresh postgres container with migrations applied.
func newTestPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	return testutil.NewTestPool(t)
}
