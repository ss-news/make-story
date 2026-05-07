package api_test

import (
	"bytes"
	"context"
	"encoding/json"
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

type authTestEnv struct {
	router http.Handler
	svc    *service.AuthService
}

func newAuthEnv(t *testing.T, disableReg bool) authTestEnv {
	t.Helper()
	pool := testutil.NewTestPool(t)
	svc := service.NewAuth(service.AuthDeps{
		Users:               repo.NewUsers(pool),
		Sessions:            repo.NewSessions(pool),
		DisableRegistration: disableReg,
	})
	r := api.NewRouter(api.RouterDeps{
		HealthDB:  func() bool { return true },
		HealthLLM: func() bool { return false },
		Auth:      svc,
	})
	return authTestEnv{router: r, svc: svc}
}

func doJSON(t *testing.T, h http.Handler, method, path string, body any, cookies ...*http.Cookie) *http.Response {
	t.Helper()
	var rdr *bytes.Reader
	if body != nil {
		raw, err := json.Marshal(body)
		require.NoError(t, err)
		rdr = bytes.NewReader(raw)
	} else {
		rdr = bytes.NewReader(nil)
	}
	req := httptest.NewRequest(method, path, rdr)
	req.Header.Set("Content-Type", "application/json")
	for _, c := range cookies {
		req.AddCookie(c)
	}
	rr := httptest.NewRecorder()
	h.ServeHTTP(rr, req)
	return rr.Result()
}

func sidCookie(resp *http.Response) *http.Cookie {
	// Returns the last cookie with the session name (latest Set-Cookie wins).
	var found *http.Cookie
	for _, c := range resp.Cookies() {
		if c.Name == auth.SessionCookieName {
			found = c
		}
	}
	return found
}

func TestRegister201(t *testing.T) {
	env := newAuthEnv(t, false)
	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/register", map[string]any{
		"email":        "reg@example.com",
		"password":     "supersecret",
		"display_name": "Reggie",
	})
	require.Equal(t, http.StatusCreated, resp.StatusCode)
	require.NotNil(t, sidCookie(resp))

	var body map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&body))
	data := body["data"].(map[string]any)
	assert.Equal(t, "reg@example.com", data["email"])
	assert.Equal(t, "Reggie", data["display_name"])
	assert.Equal(t, false, data["is_admin"])
	assert.Equal(t, false, data["ai_enabled"])
}

func TestRegisterDuplicate409(t *testing.T) {
	env := newAuthEnv(t, false)
	doJSON(t, env.router, http.MethodPost, "/api/auth/register", map[string]any{
		"email": "d@example.com", "password": "supersecret", "display_name": "D",
	})
	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/register", map[string]any{
		"email": "d@example.com", "password": "supersecret", "display_name": "D",
	})
	require.Equal(t, http.StatusConflict, resp.StatusCode)
	var body map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&body))
	assert.Equal(t, "EMAIL_TAKEN", body["error"].(map[string]any)["code"])
}

func TestRegisterValidationShortPassword400(t *testing.T) {
	env := newAuthEnv(t, false)
	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/register", map[string]any{
		"email": "v@example.com", "password": "short", "display_name": "V",
	})
	require.Equal(t, http.StatusBadRequest, resp.StatusCode)
	var body map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&body))
	errBody := body["error"].(map[string]any)
	assert.Equal(t, "VALIDATION", errBody["code"])
}

func TestRegisterDisabled403(t *testing.T) {
	env := newAuthEnv(t, true)
	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/register", map[string]any{
		"email": "x@example.com", "password": "supersecret", "display_name": "X",
	})
	require.Equal(t, http.StatusForbidden, resp.StatusCode)
	var body map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&body))
	assert.Equal(t, "REGISTRATION_DISABLED", body["error"].(map[string]any)["code"])
}

func TestLogin200(t *testing.T) {
	env := newAuthEnv(t, false)
	_, _, err := env.svc.Register(context.Background(), "li@example.com", "supersecret", "Li", "", "")
	require.NoError(t, err)

	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/login", map[string]any{
		"email": "li@example.com", "password": "supersecret",
	})
	require.Equal(t, http.StatusOK, resp.StatusCode)
	require.NotNil(t, sidCookie(resp))
}

func TestLoginInvalid401(t *testing.T) {
	env := newAuthEnv(t, false)
	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/login", map[string]any{
		"email": "missing@example.com", "password": "whatever",
	})
	require.Equal(t, http.StatusUnauthorized, resp.StatusCode)
	var body map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&body))
	assert.Equal(t, "INVALID_CREDENTIALS", body["error"].(map[string]any)["code"])
}

func TestLogout200ClearsCookie(t *testing.T) {
	env := newAuthEnv(t, false)
	_, sess, err := env.svc.Register(context.Background(), "out@example.com", "supersecret", "O", "", "")
	require.NoError(t, err)

	resp := doJSON(t, env.router, http.MethodPost, "/api/auth/logout", nil,
		&http.Cookie{Name: auth.SessionCookieName, Value: sess.ID})
	require.Equal(t, http.StatusOK, resp.StatusCode)

	c := sidCookie(resp)
	require.NotNil(t, c)
	// A clear cookie has empty value; MaxAge=-1 on the writer becomes Max-Age=0 on the wire.
	assert.Equal(t, "", c.Value)
}

func TestMe200WithCookie(t *testing.T) {
	env := newAuthEnv(t, false)
	u, sess, err := env.svc.Register(context.Background(), "me@example.com", "supersecret", "Me", "", "")
	require.NoError(t, err)

	resp := doJSON(t, env.router, http.MethodGet, "/api/auth/me", nil,
		&http.Cookie{Name: auth.SessionCookieName, Value: sess.ID})
	require.Equal(t, http.StatusOK, resp.StatusCode)

	var body map[string]any
	require.NoError(t, json.NewDecoder(resp.Body).Decode(&body))
	got := body["data"].(map[string]any)
	assert.Equal(t, u.Email, got["email"])
}

func TestMe401Anonymous(t *testing.T) {
	env := newAuthEnv(t, false)
	resp := doJSON(t, env.router, http.MethodGet, "/api/auth/me", nil)
	require.Equal(t, http.StatusUnauthorized, resp.StatusCode)
}
