package domain

import (
	"time"

	"github.com/google/uuid"
)

// User represents a registered user.
type User struct {
	ID           uuid.UUID
	Email        string
	PasswordHash string
	DisplayName  string
	CreatedAt    time.Time
	IsAdmin      bool
	AIEnabled    bool
}
