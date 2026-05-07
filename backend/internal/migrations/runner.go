package migrations

import (
	"strings"

	"github.com/golang-migrate/migrate/v4"
	_ "github.com/golang-migrate/migrate/v4/database/pgx/v5"
	"github.com/golang-migrate/migrate/v4/source/iofs"
	"github.com/samber/oops"
)

func Up(databaseURL string) error {
	src, err := iofs.New(FS, ".")
	if err != nil {
		return oops.Wrapf(err, "iofs new")
	}
	// migrate's pgx/v5 driver registers under the scheme "pgx5".
	// Accept the standard "postgres://" / "postgresql://" DSN and rewrite.
	migrateURL := databaseURL
	if strings.HasPrefix(migrateURL, "postgres://") {
		migrateURL = "pgx5://" + strings.TrimPrefix(migrateURL, "postgres://")
	} else if strings.HasPrefix(migrateURL, "postgresql://") {
		migrateURL = "pgx5://" + strings.TrimPrefix(migrateURL, "postgresql://")
	}
	m, err := migrate.NewWithSourceInstance("iofs", src, migrateURL)
	if err != nil {
		return oops.Wrapf(err, "migrate new")
	}
	if err := m.Up(); err != nil && err != migrate.ErrNoChange {
		return oops.Wrapf(err, "migrate up")
	}
	return nil
}
