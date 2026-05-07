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

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/api"
	"github.com/duyld/make-story/backend/internal/app"
	"github.com/duyld/make-story/backend/internal/migrations"
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

	srv := &http.Server{
		Addr:              ":" + cfg.Port,
		Handler:           handler,
		ReadHeaderTimeout: 10 * time.Second,
	}

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
