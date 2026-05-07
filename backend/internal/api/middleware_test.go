package api_test

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/api"
	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/service"
	"github.com/duyld/make-story/backend/internal/testutil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newTestAuthSvc(t *testing.T) *service.AuthService {
	t.Helper()
	pool := testutil.NewTestPool(t)
	return service.NewAuth(service.AuthDeps{
		Users:    repo.NewUsers(pool),
		Sessions: repo.NewSessions(pool),
	})
}

func TestSessionLoaderNoCookiePassesThrough(t *testing.T) {
	svc := newTestAuthSvc(t)

	called := false
	h := api.SessionLoader(svc, false)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
		_, ok := api.UserFrom(r.Context())
		assert.False(t, ok)
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	assert.True(t, called)
	assert.Equal(t, http.StatusOK, rr.Code)
}

func TestSessionLoaderValidCookieSetsUser(t *testing.T) {
	svc := newTestAuthSvc(t)
	ctx := context.Background()

	u, sess, err := svc.Register(ctx, "ml@example.com", "supersecret", "M", "", "")
	require.NoError(t, err)

	var seenUserEmail string
	h := api.SessionLoader(svc, false)(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		got, ok := api.UserFrom(r.Context())
		require.True(t, ok)
		seenUserEmail = got.Email
		w.WriteHeader(http.StatusOK)
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	req.AddCookie(&http.Cookie{Name: auth.SessionCookieName, Value: sess.ID})
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	assert.Equal(t, http.StatusOK, rr.Code)
	assert.Equal(t, u.Email, seenUserEmail)

	// Fresh cookie should be set on the response.
	cookies := rr.Result().Cookies()
	require.NotEmpty(t, cookies)
	var sidCookie *http.Cookie
	for _, c := range cookies {
		if c.Name == auth.SessionCookieName {
			sidCookie = c
		}
	}
	require.NotNil(t, sidCookie)
	assert.Equal(t, sess.ID, sidCookie.Value)
}

func TestAuthRequiredBlocksAnonymous(t *testing.T) {
	mw := api.AuthRequired
	called := false
	h := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		called = true
	}))

	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)

	assert.False(t, called)
	assert.Equal(t, http.StatusUnauthorized, rr.Code)
}

func TestOriginCheckBlocksDisallowed(t *testing.T) {
	mw := api.OriginCheck([]string{"https://allowed.example"})
	h := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))

	// Disallowed origin on POST → 403.
	req := httptest.NewRequest(http.MethodPost, "/", nil)
	req.Header.Set("Origin", "https://evil.example")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	assert.Equal(t, http.StatusForbidden, rr.Code)

	// Allowed origin on POST → 200.
	req2 := httptest.NewRequest(http.MethodPost, "/", nil)
	req2.Header.Set("Origin", "https://allowed.example")
	rr2 := httptest.NewRecorder()
	h.ServeHTTP(rr2, req2)
	assert.Equal(t, http.StatusOK, rr2.Code)

	// GET passes regardless.
	req3 := httptest.NewRequest(http.MethodGet, "/", nil)
	req3.Header.Set("Origin", "https://evil.example")
	rr3 := httptest.NewRecorder()
	h.ServeHTTP(rr3, req3)
	assert.Equal(t, http.StatusOK, rr3.Code)
}

func TestOriginCheckEmptyAllowedSkipsCheck(t *testing.T) {
	mw := api.OriginCheck(nil)
	h := mw(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	req := httptest.NewRequest(http.MethodPost, "/", nil)
	req.Header.Set("Origin", "https://anywhere.example")
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	assert.Equal(t, http.StatusOK, rr.Code)
}
