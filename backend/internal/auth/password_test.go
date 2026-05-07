package auth

import (
	"errors"
	"testing"

	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestHashAndVerifyPassword(t *testing.T) {
	hash, err := HashPassword("correct horse battery staple")
	require.NoError(t, err)
	require.NotEmpty(t, hash)

	require.NoError(t, VerifyPassword(hash, "correct horse battery staple"))

	err = VerifyPassword(hash, "wrong password")
	require.Error(t, err)
}

func TestHashPasswordTooShort(t *testing.T) {
	_, err := HashPassword("short")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrPasswordTooShort))
}

func TestHashPasswordMinLength(t *testing.T) {
	hash, err := HashPassword("12345678")
	require.NoError(t, err)
	require.NotEmpty(t, hash)
}
