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
