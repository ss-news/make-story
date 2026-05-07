package domain

import (
	"time"

	"github.com/google/uuid"
)

// Session represents an authenticated session row.
type Session struct {
	ID         string
	UserID     uuid.UUID
	CreatedAt  time.Time
	LastSeenAt time.Time
	ExpiresAt  time.Time
	UserAgent  string
	IP         string
}

// Active reports whether the session is still valid at the given time.
func (s Session) Active(now time.Time) bool {
	return now.Before(s.ExpiresAt)
}
