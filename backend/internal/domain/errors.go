package domain

import "errors"

// Sentinel errors used by repositories and services.
var (
	ErrNotFound             = errors.New("not found")
	ErrEmailTaken           = errors.New("email taken")
	ErrInvalidCredentials   = errors.New("invalid credentials")
	ErrSessionExpired       = errors.New("session expired")
	ErrRegistrationDisabled = errors.New("registration disabled")
	ErrPasswordTooShort     = errors.New("password too short")
)
