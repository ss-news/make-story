package auth

import (
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestNewSessionID(t *testing.T) {
	id1, err := NewSessionID()
	require.NoError(t, err)
	require.Len(t, id1, 64) // 32 bytes hex == 64 chars

	id2, err := NewSessionID()
	require.NoError(t, err)
	assert.NotEqual(t, id1, id2)
}

func TestSetSessionCookie(t *testing.T) {
	w := httptest.NewRecorder()
	expires := time.Now().Add(SessionDuration)
	SetSessionCookie(w, "abc123", expires, true)

	resp := w.Result()
	cookies := resp.Cookies()
	require.Len(t, cookies, 1)

	c := cookies[0]
	assert.Equal(t, SessionCookieName, c.Name)
	assert.Equal(t, "abc123", c.Value)
	assert.Equal(t, "/", c.Path)
	assert.True(t, c.HttpOnly)
	assert.True(t, c.Secure)
	assert.Equal(t, http.SameSiteLaxMode, c.SameSite)
	assert.WithinDuration(t, expires, c.Expires, time.Second)
}

func TestSetSessionCookieInsecure(t *testing.T) {
	w := httptest.NewRecorder()
	SetSessionCookie(w, "x", time.Now().Add(time.Hour), false)
	c := w.Result().Cookies()[0]
	assert.False(t, c.Secure)
}

func TestClearSessionCookie(t *testing.T) {
	w := httptest.NewRecorder()
	ClearSessionCookie(w, true)

	cookies := w.Result().Cookies()
	require.Len(t, cookies, 1)
	c := cookies[0]
	assert.Equal(t, SessionCookieName, c.Name)
	assert.Equal(t, "", c.Value)
	assert.Equal(t, -1, c.MaxAge)
	assert.Equal(t, "/", c.Path)
}

func TestSessionConstants(t *testing.T) {
	assert.Equal(t, 30*24*time.Hour, SessionDuration)
	assert.Equal(t, 7*24*time.Hour, SessionRenewWhenLessThan)
	assert.Equal(t, "sid", SessionCookieName)
}
