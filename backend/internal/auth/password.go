package auth

import (
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/samber/oops"
	"golang.org/x/crypto/bcrypt"
)

// MinPasswordLen is the minimum allowed password length.
const MinPasswordLen = 8

// BcryptCost is the bcrypt cost factor used for hashing.
const BcryptCost = 12

// HashPassword hashes a plaintext password using bcrypt with cost 12.
// Returns domain.ErrPasswordTooShort wrapped if the password is below MinPasswordLen.
func HashPassword(plain string) (string, error) {
	if len(plain) < MinPasswordLen {
		return "", oops.Wrapf(domain.ErrPasswordTooShort, "password must be at least %d characters", MinPasswordLen)
	}
	h, err := bcrypt.GenerateFromPassword([]byte(plain), BcryptCost)
	if err != nil {
		return "", oops.Wrapf(err, "bcrypt generate")
	}
	return string(h), nil
}

// VerifyPassword compares a bcrypt hash with a plaintext password.
// Returns nil on match, an error otherwise.
func VerifyPassword(hash, plain string) error {
	if err := bcrypt.CompareHashAndPassword([]byte(hash), []byte(plain)); err != nil {
		return oops.Wrapf(err, "bcrypt compare")
	}
	return nil
}
