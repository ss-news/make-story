package api

import (
	"net/http"
	"time"

	"github.com/duyld/make-story/backend/internal/service"
	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/httprate"
)

// RouterDeps holds the dependencies needed to build the HTTP router.
type RouterDeps struct {
	HealthDB       func() bool
	HealthLLM      func() bool
	Auth           *service.AuthService
	SecureCookie   bool
	AllowedOrigins []string
}

// NewRouter wires middleware and routes for the public API.
func NewRouter(deps RouterDeps) http.Handler {
	r := chi.NewRouter()
	r.Use(middleware.RequestID)
	r.Use(middleware.RealIP)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))
	if deps.Auth != nil {
		r.Use(SessionLoader(deps.Auth, deps.SecureCookie))
	}
	r.Use(OriginCheck(deps.AllowedOrigins))

	r.Get("/api/health", healthHandler(deps))

	if deps.Auth != nil {
		r.Route("/api/auth", func(r chi.Router) {
			// Register and login: 10 req/min per client IP.
			r.Group(func(r chi.Router) {
				r.Use(httprate.LimitByIP(10, 1*time.Minute))
				r.Post("/register", handleRegister(deps.Auth, deps.SecureCookie))
				r.Post("/login", handleLogin(deps.Auth, deps.SecureCookie))
			})
			// Logout and me are not rate-limited.
			r.Post("/logout", handleLogout(deps.Auth, deps.SecureCookie))
			r.Get("/me", handleMe())
		})
	}

	// SPA fallback. Registered after all /api/* routes so chi matches API
	// handlers first; everything else (including 404s on non-API paths)
	// is served by the embedded frontend bundle.
	spa := SPAHandler()
	r.NotFound(spa.ServeHTTP)
	return r
}
