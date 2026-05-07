package app

import (
	"os"
	"strconv"

	"github.com/samber/oops"
)

type Config struct {
	Port                string
	DatabaseURL         string
	SessionSecret       string
	LogLevel            string // debug|info|warn|error
	LogFormat           string // json|text
	AllowedOrigins      []string
	DisableRegistration bool
	SeedDemo            bool

	LLMBaseURL      string
	LLMAPIKey       string
	LLMDefaultModel string
	LLMMaxTokens    int
	LLMTimeoutSec   int
	AIDailyLimit    int
}

func LoadConfig() (Config, error) {
	cfg := Config{
		Port:            envOr("PORT", "8080"),
		DatabaseURL:     os.Getenv("DATABASE_URL"),
		SessionSecret:   os.Getenv("SESSION_SECRET"),
		LogLevel:        envOr("LOG_LEVEL", "info"),
		LogFormat:       envOr("LOG_FORMAT", "json"),
		LLMBaseURL:      envOr("LLM_BASE_URL", "https://llm.musia.store/v1"),
		LLMAPIKey:       os.Getenv("LLM_API_KEY"),
		LLMDefaultModel: envOr("LLM_DEFAULT_MODEL", "claude-sonnet-4-5"),
		LLMMaxTokens:    envInt("LLM_MAX_TOKENS", 2048),
		LLMTimeoutSec:   envInt("LLM_TIMEOUT_SEC", 60),
		AIDailyLimit:    envInt("AI_DAILY_LIMIT", 0),
	}
	cfg.DisableRegistration = envBool("DISABLE_REGISTRATION", false)
	cfg.SeedDemo = envBool("SEED_DEMO", false)
	cfg.AllowedOrigins = splitCSV(os.Getenv("ALLOWED_ORIGINS"))

	if cfg.DatabaseURL == "" {
		return Config{}, oops.Errorf("DATABASE_URL is required")
	}
	if cfg.SessionSecret == "" {
		return Config{}, oops.Errorf("SESSION_SECRET is required")
	}
	return cfg, nil
}

func envOr(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func envInt(k string, def int) int {
	if v := os.Getenv(k); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			return n
		}
	}
	return def
}

func envBool(k string, def bool) bool {
	if v := os.Getenv(k); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return def
}

func splitCSV(s string) []string {
	if s == "" {
		return nil
	}
	var out []string
	cur := ""
	for _, r := range s {
		if r == ',' {
			if cur != "" {
				out = append(out, cur)
				cur = ""
			}
			continue
		}
		cur += string(r)
	}
	if cur != "" {
		out = append(out, cur)
	}
	return out
}
