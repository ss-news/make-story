package api

import (
	"context"
	"net/http"
	"slices"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/duyld/make-story/backend/internal/service"
)

type ctxKey int

const (
	ctxUser ctxKey = iota
	ctxSession
)

// SessionLoader resolves a session cookie (if any) and stuffs the User and Session
// into the request context. On success it also writes a fresh cookie reflecting
// any sliding renewal. Failures are silently ignored — the handler chain just
// runs anonymously.
func SessionLoader(svc *service.AuthService, secureCookies bool) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			c, err := r.Cookie(auth.SessionCookieName)
			if err != nil || c.Value == "" {
				next.ServeHTTP(w, r)
				return
			}
			u, sess, err := svc.ResolveSession(r.Context(), c.Value)
			if err != nil {
				auth.ClearSessionCookie(w, secureCookies)
				next.ServeHTTP(w, r)
				return
			}
			auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, secureCookies)
			ctx := context.WithValue(r.Context(), ctxUser, u)
			ctx = context.WithValue(ctx, ctxSession, sess)
			next.ServeHTTP(w, r.WithContext(ctx))
		})
	}
}

// AuthRequired short-circuits with 401 when no user is on the context.
func AuthRequired(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if _, ok := UserFrom(r.Context()); !ok {
			Error(w, http.StatusUnauthorized, "UNAUTHORIZED", "authentication required", nil)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// OriginCheck enforces an allowlist of Origin headers for unsafe HTTP methods.
// An empty allowed list disables the check (useful in tests / dev).
func OriginCheck(allowed []string) func(http.Handler) http.Handler {
	return func(next http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if len(allowed) == 0 {
				next.ServeHTTP(w, r)
				return
			}
			switch r.Method {
			case http.MethodGet, http.MethodHead, http.MethodOptions:
				next.ServeHTTP(w, r)
				return
			}
			origin := r.Header.Get("Origin")
			if origin == "" {
				next.ServeHTTP(w, r)
				return
			}
			if !slices.Contains(allowed, origin) {
				Error(w, http.StatusForbidden, "FORBIDDEN_ORIGIN", "origin not allowed", nil)
				return
			}
			next.ServeHTTP(w, r)
		})
	}
}

// UserFrom extracts a User stored in the context by SessionLoader.
func UserFrom(ctx context.Context) (domain.User, bool) {
	u, ok := ctx.Value(ctxUser).(domain.User)
	return u, ok
}

// SessionFrom extracts a Session stored in the context by SessionLoader.
func SessionFrom(ctx context.Context) (domain.Session, bool) {
	s, ok := ctx.Value(ctxSession).(domain.Session)
	return s, ok
}
