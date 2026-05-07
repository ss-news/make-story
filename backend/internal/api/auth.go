package api

import (
	"encoding/json"
	"errors"
	"net"
	"net/http"

	"github.com/duyld/make-story/backend/internal/auth"
	"github.com/duyld/make-story/backend/internal/domain"
	"github.com/duyld/make-story/backend/internal/service"
)

// userDTO is the safe serialisable shape returned for a user.
type userDTO struct {
	ID          string `json:"id"`
	Email       string `json:"email"`
	DisplayName string `json:"display_name"`
	IsAdmin     bool   `json:"is_admin"`
	AIEnabled   bool   `json:"ai_enabled"`
}

func toUserDTO(u domain.User) userDTO {
	return userDTO{
		ID:          u.ID.String(),
		Email:       u.Email,
		DisplayName: u.DisplayName,
		IsAdmin:     u.IsAdmin,
		AIEnabled:   u.AIEnabled,
	}
}

type registerReq struct {
	Email       string `json:"email"`
	Password    string `json:"password"`
	DisplayName string `json:"display_name"`
}

type loginReq struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}

func handleRegister(svc *service.AuthService, secureCookie bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req registerReq
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			Error(w, http.StatusBadRequest, "VALIDATION", "invalid JSON body", nil)
			return
		}
		u, sess, err := svc.Register(r.Context(), req.Email, req.Password, req.DisplayName, r.UserAgent(), clientIP(r))
		switch {
		case err == nil:
			auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, secureCookie)
			JSON(w, http.StatusCreated, toUserDTO(u))
		case errors.Is(err, domain.ErrEmailTaken):
			Error(w, http.StatusConflict, "EMAIL_TAKEN", "email already registered", nil)
		case errors.Is(err, domain.ErrPasswordTooShort):
			Error(w, http.StatusBadRequest, "VALIDATION", "password too short",
				map[string]string{"password": "min 8 characters"})
		case errors.Is(err, domain.ErrRegistrationDisabled):
			Error(w, http.StatusForbidden, "REGISTRATION_DISABLED", "registration is disabled", nil)
		default:
			Error(w, http.StatusInternalServerError, "INTERNAL", "internal error", nil)
		}
	}
}

func handleLogin(svc *service.AuthService, secureCookie bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		var req loginReq
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			Error(w, http.StatusBadRequest, "VALIDATION", "invalid JSON body", nil)
			return
		}
		u, sess, err := svc.Login(r.Context(), req.Email, req.Password, r.UserAgent(), clientIP(r))
		switch {
		case err == nil:
			auth.SetSessionCookie(w, sess.ID, sess.ExpiresAt, secureCookie)
			JSON(w, http.StatusOK, toUserDTO(u))
		case errors.Is(err, domain.ErrInvalidCredentials):
			Error(w, http.StatusUnauthorized, "INVALID_CREDENTIALS", "invalid email or password", nil)
		default:
			Error(w, http.StatusInternalServerError, "INTERNAL", "internal error", nil)
		}
	}
}

func handleLogout(svc *service.AuthService, secureCookie bool) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if c, err := r.Cookie(auth.SessionCookieName); err == nil && c.Value != "" {
			_ = svc.Logout(r.Context(), c.Value)
		}
		auth.ClearSessionCookie(w, secureCookie)
		JSON(w, http.StatusOK, map[string]any{"status": "ok"})
	}
}

func handleMe() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		u, ok := UserFrom(r.Context())
		if !ok {
			Error(w, http.StatusUnauthorized, "UNAUTHORIZED", "authentication required", nil)
			return
		}
		JSON(w, http.StatusOK, toUserDTO(u))
	}
}

// clientIP returns the host portion of the request remote addr (after middleware.RealIP).
// Returns "" if the value cannot be parsed as a valid IP — keeps the inet column NULL.
func clientIP(r *http.Request) string {
	host := r.RemoteAddr
	if h, _, err := net.SplitHostPort(host); err == nil {
		host = h
	}
	if net.ParseIP(host) == nil {
		return ""
	}
	return host
}
