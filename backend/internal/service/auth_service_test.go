package service_test

import (
	"context"
	"errors"
	"testing"
	"time"

	"github.com/duyld/make-story/backend/internal/adapter/repo"
	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/duyld/make-story/backend/internal/service"
	"github.com/duyld/make-story/backend/internal/testutil"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func newAuthService(t *testing.T, disableReg bool) *service.AuthService {
	t.Helper()
	pool := testutil.NewTestPool(t)
	users := repo.NewUsers(pool)
	sessions := repo.NewSessions(pool)
	return service.NewAuth(service.AuthDeps{
		Users:               users,
		Sessions:            sessions,
		DisableRegistration: disableReg,
	})
}

func TestAuthRegisterHappyPath(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	u, sess, err := svc.Register(ctx, "alice@example.com", "supersecret", "Alice", "ua", "127.0.0.1")
	require.NoError(t, err)
	assert.Equal(t, "alice@example.com", u.Email)
	assert.NotEmpty(t, sess.ID)
	assert.Equal(t, u.ID, sess.UserID)
	assert.True(t, sess.ExpiresAt.After(time.Now()))
}

func TestAuthRegisterDuplicateEmail(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, _, err := svc.Register(ctx, "dup@example.com", "supersecret", "Dup", "", "")
	require.NoError(t, err)

	_, _, err = svc.Register(ctx, "DUP@example.com", "supersecret", "Dup2", "", "")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrEmailTaken))
}

func TestAuthRegisterWeakPassword(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, _, err := svc.Register(ctx, "weak@example.com", "short", "Weak", "", "")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrPasswordTooShort))
}

func TestAuthRegisterDisabled(t *testing.T) {
	svc := newAuthService(t, true)
	ctx := context.Background()

	_, _, err := svc.Register(ctx, "x@example.com", "supersecret", "X", "", "")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrRegistrationDisabled))
}

func TestAuthLoginHappy(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, _, err := svc.Register(ctx, "login@example.com", "supersecret", "L", "", "")
	require.NoError(t, err)

	u, sess, err := svc.Login(ctx, "login@example.com", "supersecret", "ua", "1.2.3.4")
	require.NoError(t, err)
	assert.Equal(t, "login@example.com", u.Email)
	assert.NotEmpty(t, sess.ID)
}

func TestAuthLoginWrongPassword(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, _, err := svc.Register(ctx, "wrong@example.com", "supersecret", "W", "", "")
	require.NoError(t, err)

	_, _, err = svc.Login(ctx, "wrong@example.com", "badpassword", "", "")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrInvalidCredentials))
}

func TestAuthLoginUnknownEmail(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, _, err := svc.Login(ctx, "ghost@example.com", "irrelevant", "", "")
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrInvalidCredentials))
}

func TestAuthResolveSessionTouchOnly(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, sess, err := svc.Register(ctx, "tou@example.com", "supersecret", "T", "", "")
	require.NoError(t, err)
	originalExpires := sess.ExpiresAt

	// Freeze "now" to right after registration so expiry > 7d remains.
	now := sess.CreatedAt.Add(time.Hour)
	svc.Now = func() time.Time { return now }

	u, refreshed, err := svc.ResolveSession(ctx, sess.ID)
	require.NoError(t, err)
	assert.Equal(t, "tou@example.com", u.Email)
	// Expiry unchanged, last_seen advanced.
	assert.WithinDuration(t, originalExpires, refreshed.ExpiresAt, time.Second)
	assert.WithinDuration(t, now, refreshed.LastSeenAt, time.Second)
}

func TestAuthResolveSessionRenews(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, sess, err := svc.Register(ctx, "ren@example.com", "supersecret", "R", "", "")
	require.NoError(t, err)

	// Move "now" to within 7d of expiry → renewal expected.
	now := sess.ExpiresAt.Add(-3 * 24 * time.Hour)
	svc.Now = func() time.Time { return now }

	u, refreshed, err := svc.ResolveSession(ctx, sess.ID)
	require.NoError(t, err)
	assert.Equal(t, "ren@example.com", u.Email)
	expected := now.Add(auth.SessionDuration)
	assert.WithinDuration(t, expected, refreshed.ExpiresAt, time.Second)
}

func TestAuthResolveSessionExpired(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, sess, err := svc.Register(ctx, "exp@example.com", "supersecret", "E", "", "")
	require.NoError(t, err)

	// Move "now" past expiry.
	now := sess.ExpiresAt.Add(time.Hour)
	svc.Now = func() time.Time { return now }

	_, _, err = svc.ResolveSession(ctx, sess.ID)
	require.Error(t, err)
	assert.True(t, errors.Is(err, domain.ErrSessionExpired))
}

func TestAuthLogoutDeletesSession(t *testing.T) {
	svc := newAuthService(t, false)
	ctx := context.Background()

	_, sess, err := svc.Register(ctx, "out@example.com", "supersecret", "O", "", "")
	require.NoError(t, err)

	require.NoError(t, svc.Logout(ctx, sess.ID))

	_, _, err = svc.ResolveSession(ctx, sess.ID)
	require.Error(t, err)
}
