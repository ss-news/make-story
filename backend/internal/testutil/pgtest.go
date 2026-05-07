// Package testutil provides shared helpers for backend tests.
package testutil

import (
	"context"
	"os"
	"testing"

	"github.com/duyld/make-story/backend/internal/migrations"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/stretchr/testify/require"
	tcpostgres "github.com/testcontainers/testcontainers-go/modules/postgres"
)

// NewTestPool boots a postgres container, runs migrations, and returns a connected
// pool. Honors CI_SKIP_TESTCONTAINERS=1 by calling t.Skip.
//
// The container is automatically terminated and the pool closed via t.Cleanup.
func NewTestPool(t *testing.T) *pgxpool.Pool {
	t.Helper()
	if os.Getenv("CI_SKIP_TESTCONTAINERS") == "1" {
		t.Skip("CI_SKIP_TESTCONTAINERS=1 set; skipping postgres testcontainer")
	}

	ctx := context.Background()
	pgC, err := tcpostgres.Run(ctx,
		"postgres:16-alpine",
		tcpostgres.WithDatabase("make_story_test"),
		tcpostgres.WithUsername("test"),
		tcpostgres.WithPassword("test"),
		tcpostgres.BasicWaitStrategies(),
	)
	require.NoError(t, err, "start postgres container")

	t.Cleanup(func() {
		_ = pgC.Terminate(context.Background())
	})

	dsn, err := pgC.ConnectionString(ctx, "sslmode=disable")
	require.NoError(t, err, "connection string")

	require.NoError(t, migrations.Up(dsn), "run migrations")

	pool, err := pgxpool.New(ctx, dsn)
	require.NoError(t, err, "open pool")
	t.Cleanup(pool.Close)

	return pool
}
