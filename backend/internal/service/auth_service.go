// Package service contains application services that orchestrate domain logic.
package service

import (
	"context"
	"errors"
	"time"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/google/uuid"
	"github.com/samber/oops"
)

// UsersRepo is the persistence contract AuthService needs for users.
type UsersRepo interface {
	Create(ctx context.Context, email, passwordHash, displayName string) (domain.User, error)
	FindByEmail(ctx context.Context, email string) (domain.User, error)
	FindByID(ctx context.Context, id uuid.UUID) (domain.User, error)
}

// SessionsRepo is the persistence contract AuthService needs for sessions.
type SessionsRepo interface {
	Create(ctx context.Context, sess domain.Session) error
	Get(ctx context.Context, id string) (domain.Session, error)
	Touch(ctx context.Context, id string, lastSeen, newExpires time.Time) error
	Delete(ctx context.Context, id string) error
}

// AuthDeps are the dependencies for AuthService.
type AuthDeps struct {
	Users               UsersRepo
	Sessions            SessionsRepo
	DisableRegistration bool
	// Now is injectable for tests; defaults to time.Now.
	Now func() time.Time
}

// AuthService implements user registration, login/logout, and session resolution.
type AuthService struct {
	users               UsersRepo
	sessions            SessionsRepo
	disableRegistration bool

	// Now is exported so tests can override the clock after construction.
	Now func() time.Time
}

// NewAuth constructs an AuthService.
func NewAuth(deps AuthDeps) *AuthService {
	now := deps.Now
	if now == nil {
		now = time.Now
	}
	return &AuthService{
		users:               deps.Users,
		sessions:            deps.Sessions,
		disableRegistration: deps.DisableRegistration,
		Now:                 now,
	}
}

// Register creates a new user account and starts a session.
func (s *AuthService) Register(ctx context.Context, email, password, displayName, userAgent, ip string) (domain.User, domain.Session, error) {
	if s.disableRegistration {
		return domain.User{}, domain.Session{}, oops.Wrapf(domain.ErrRegistrationDisabled, "register")
	}
	hash, err := auth.HashPassword(password)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	u, err := s.users.Create(ctx, email, hash, displayName)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	sess, err := s.startSession(ctx, u.ID, userAgent, ip)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	return u, sess, nil
}

// Login authenticates a user and starts a session.
// Returns domain.ErrInvalidCredentials for both unknown email and wrong password
// (no enumeration leak).
func (s *AuthService) Login(ctx context.Context, email, password, userAgent, ip string) (domain.User, domain.Session, error) {
	u, err := s.users.FindByEmail(ctx, email)
	if err != nil {
		if errors.Is(err, domain.ErrNotFound) {
			return domain.User{}, domain.Session{}, oops.Wrapf(domain.ErrInvalidCredentials, "login")
		}
		return domain.User{}, domain.Session{}, err
	}
	if err := auth.VerifyPassword(u.PasswordHash, password); err != nil {
		return domain.User{}, domain.Session{}, oops.Wrapf(domain.ErrInvalidCredentials, "login")
	}
	sess, err := s.startSession(ctx, u.ID, userAgent, ip)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	return u, sess, nil
}

// Logout deletes the session row by id.
func (s *AuthService) Logout(ctx context.Context, sessionID string) error {
	if err := s.sessions.Delete(ctx, sessionID); err != nil {
		return oops.Wrapf(err, "logout")
	}
	return nil
}

// ResolveSession looks up the session, returns ErrSessionExpired if past expiry
// (after deleting it), and otherwise returns the user and (possibly renewed) session.
func (s *AuthService) ResolveSession(ctx context.Context, sessionID string) (domain.User, domain.Session, error) {
	now := s.Now()
	sess, err := s.sessions.Get(ctx, sessionID)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}
	if !now.Before(sess.ExpiresAt) {
		// Best-effort cleanup.
		_ = s.sessions.Delete(ctx, sess.ID)
		return domain.User{}, domain.Session{}, oops.Wrapf(domain.ErrSessionExpired, "resolveSession")
	}
	u, err := s.users.FindByID(ctx, sess.UserID)
	if err != nil {
		return domain.User{}, domain.Session{}, err
	}

	newExpires := sess.ExpiresAt
	if sess.ExpiresAt.Sub(now) < auth.SessionRenewWhenLessThan {
		newExpires = now.Add(auth.SessionDuration)
	}
	if err := s.sessions.Touch(ctx, sess.ID, now, newExpires); err != nil {
		return domain.User{}, domain.Session{}, err
	}
	sess.LastSeenAt = now
	sess.ExpiresAt = newExpires
	return u, sess, nil
}

// startSession generates a fresh session id, persists the row, and returns the
// in-memory representation.
func (s *AuthService) startSession(ctx context.Context, userID uuid.UUID, userAgent, ip string) (domain.Session, error) {
	sid, err := auth.NewSessionID()
	if err != nil {
		return domain.Session{}, oops.Wrapf(err, "session id")
	}
	now := s.Now()
	sess := domain.Session{
		ID:         sid,
		UserID:     userID,
		CreatedAt:  now,
		LastSeenAt: now,
		ExpiresAt:  now.Add(auth.SessionDuration),
		UserAgent:  userAgent,
		IP:         ip,
	}
	if err := s.sessions.Create(ctx, sess); err != nil {
		return domain.Session{}, err
	}
	return sess, nil
}
