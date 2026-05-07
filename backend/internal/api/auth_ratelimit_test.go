package api_test

import (
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestLoginRateLimit429AfterTen(t *testing.T) {
	env := newAuthEnv(t, false)

	var lastStatus int
	for i := 0; i < 11; i++ {
		resp := doJSON(t, env.router, http.MethodPost, "/api/auth/login", map[string]any{
			"email": "rl@example.com", "password": "whatever",
		})
		lastStatus = resp.StatusCode
		_ = resp.Body.Close()
		if i < 10 {
			// First 10 should be 401 (invalid credentials), not 429.
			require.NotEqual(t, http.StatusTooManyRequests, lastStatus)
		}
	}
	assert.Equal(t, http.StatusTooManyRequests, lastStatus)
}
