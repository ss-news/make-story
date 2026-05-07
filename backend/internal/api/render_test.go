package api_test

import (
	"net/http/httptest"
	"testing"

	"github.com/duyld/make-story/backend/internal/api"
	"github.com/stretchr/testify/require"
)

func TestJSON_WrapsInDataEnvelope(t *testing.T) {
	rec := httptest.NewRecorder()
	api.JSON(rec, 200, map[string]string{"hello": "world"})
	require.Equal(t, 200, rec.Code)
	require.Equal(t, "application/json; charset=utf-8", rec.Header().Get("Content-Type"))
	require.JSONEq(t, `{"data":{"hello":"world"}}`, rec.Body.String())
}

func TestError_WrapsCodeAndMessage(t *testing.T) {
	rec := httptest.NewRecorder()
	api.Error(rec, 400, "VALIDATION", "bad input", map[string]string{"email": "required"})
	require.Equal(t, 400, rec.Code)
	require.JSONEq(t,
		`{"error":{"code":"VALIDATION","message":"bad input","fields":{"email":"required"}}}`,
		rec.Body.String(),
	)
}
