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
