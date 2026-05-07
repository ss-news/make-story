package api_test

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/duyld/make-story/backend/internal/api"
	"github.com/stretchr/testify/require"
)

func TestHealth_OK(t *testing.T) {
	r := api.NewRouter(api.RouterDeps{
		HealthDB:  func() bool { return true },
		HealthLLM: func() bool { return false },
	})
	req := httptest.NewRequest(http.MethodGet, "/api/health", nil)
	rec := httptest.NewRecorder()
	r.ServeHTTP(rec, req)
	require.Equal(t, 200, rec.Code)
	require.Contains(t, rec.Body.String(), `"status":"ok"`)
	require.Contains(t, rec.Body.String(), `"db":"up"`)
	require.Contains(t, rec.Body.String(), `"llm":"down"`)
}
