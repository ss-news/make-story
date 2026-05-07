package auth

import (
	"crypto/rand"
	"encoding/hex"
	"net/http"
	"time"

	"github.com/samber/oops"
)

// Session-related cookie and lifetime constants.
const (
	// SessionCookieName is the HTTP cookie used to carry the session id.
	SessionCookieName = "sid"
	// SessionDuration is the lifetime granted on creation/renewal.
	SessionDuration = 30 * 24 * time.Hour
	// SessionRenewWhenLessThan controls sliding renewal: if the remaining
	// lifetime is less than this threshold, ResolveSession renews the session.
	SessionRenewWhenLessThan = 7 * 24 * time.Hour
)

// NewSessionID returns a 32-byte cryptographically random session id, hex-encoded (64 chars).
func NewSessionID() (string, error) {
	var b [32]byte
	if _, err := rand.Read(b[:]); err != nil {
		return "", oops.Wrapf(err, "rand read")
	}
	return hex.EncodeToString(b[:]), nil
}

// SetSessionCookie writes the session cookie with the given id and expiry.
// secure controls the Secure flag (set to true in production).
func SetSessionCookie(w http.ResponseWriter, sid string, expires time.Time, secure bool) {
	http.SetCookie(w, &http.Cookie{
		Name:     SessionCookieName,
		Value:    sid,
		Path:     "/",
		Expires:  expires,
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
}

// ClearSessionCookie deletes the session cookie by setting MaxAge=-1.
func ClearSessionCookie(w http.ResponseWriter, secure bool) {
	http.SetCookie(w, &http.Cookie{
		Name:     SessionCookieName,
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		Secure:   secure,
		SameSite: http.SameSiteLaxMode,
	})
}
