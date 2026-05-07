package api

import (
	"embed"
	"io/fs"
	"net/http"
	"path"
	"strings"
)

// distFS embeds the built frontend bundle. The directory must always exist
// at build time. A placeholder index.html is committed so `go build` works
// without first running the frontend build; the production Dockerfile
// overwrites this directory with the real Vite output.
//
//go:embed all:static/dist
var distFS embed.FS

// SPAHandler serves the embedded single-page application.
//
// Behavior:
//   - Files that exist under static/dist are served directly.
//   - Any other path falls back to index.html so client-side routing works.
//   - index.html is served with no-cache so deploys roll out immediately.
//   - Hashed assets (anything under /assets/) get a long max-age.
//
// API routes are registered before this handler in router.go, so /api/*
// requests never reach the SPA fallback.
func SPAHandler() http.Handler {
	sub, err := fs.Sub(distFS, "static/dist")
	if err != nil {
		// embed guarantees the directory exists; this would be a programmer error.
		panic("api: failed to open embedded static/dist: " + err.Error())
	}
	fileServer := http.FileServer(http.FS(sub))

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		reqPath := strings.TrimPrefix(r.URL.Path, "/")
		if reqPath == "" {
			serveIndex(w, r, sub)
			return
		}

		// If the file exists in the bundle, serve it with cache headers.
		if f, err := sub.Open(reqPath); err == nil {
			if stat, statErr := f.Stat(); statErr == nil && !stat.IsDir() {
				_ = f.Close()
				setCacheHeaders(w, reqPath)
				fileServer.ServeHTTP(w, r)
				return
			}
			_ = f.Close()
		}

		// Otherwise, SPA fallback to index.html.
		serveIndex(w, r, sub)
	})
}

func serveIndex(w http.ResponseWriter, r *http.Request, sub fs.FS) {
	data, err := fs.ReadFile(sub, "index.html")
	if err != nil {
		http.Error(w, "index.html not found", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-cache")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}

func setCacheHeaders(w http.ResponseWriter, reqPath string) {
	base := path.Base(reqPath)
	if base == "index.html" {
		w.Header().Set("Cache-Control", "no-cache")
		return
	}
	// Vite emits hashed filenames under /assets/ — safe to cache aggressively.
	if strings.HasPrefix(reqPath, "assets/") {
		w.Header().Set("Cache-Control", "public, max-age=31536000, immutable")
		return
	}
	w.Header().Set("Cache-Control", "public, max-age=3600")
}
