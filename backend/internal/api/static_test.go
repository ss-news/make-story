package api_test

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/duyld/make-story/backend/internal/api"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newSPARouter() http.Handler {
	return api.NewRouter(api.RouterDeps{
		HealthDB:  func() bool { return true },
		HealthLLM: func() bool { return false },
	})
}

func TestSPAServesIndexAtRoot(t *testing.T) {
	r := newSPARouter()
	req := httptest.NewRequest(http.MethodGet, "/", nil)
	rr := httptest.NewRecorder()
	r.ServeHTTP(rr, req)

	require.Equal(t, http.StatusOK, rr.Code)
	assert.Contains(t, rr.Header().Get("Content-Type"), "text/html")
	assert.True(t, strings.Contains(rr.Body.String(), "<div id=\"root\">") ||
		strings.Contains(rr.Body.String(), "<div id='root'>"),
		"expected SPA root div in response, got: %s", rr.Body.String())
}

func TestSPAFallbackForUnknownRoute(t *testing.T) {
	r := newSPARouter()
	req := httptest.NewRequest(http.MethodGet, "/some-route-not-in-api", nil)
	rr := httptest.NewRecorder()
	r.ServeHTTP(rr, req)

	require.Equal(t, http.StatusOK, rr.Code)
	assert.Contains(t, rr.Header().Get("Content-Type"), "text/html")
}

func TestSPADoesNotShadowAPIRoutes(t *testing.T) {
	r := newSPARouter()
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rr := httptest.NewRecorder()
	r.ServeHTTP(rr, req)

	require.Equal(t, http.StatusOK, rr.Code)
	assert.Contains(t, rr.Header().Get("Content-Type"), "application/json")
}
