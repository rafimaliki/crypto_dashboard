#!/bin/bash
set -e

echo "Running database migrations..."

export PGHOST=${POSTGRES_HOST:-postgres}
export PGPORT=5432
export PGUSER=${POSTGRES_USER}
export PGDATABASE=${POSTGRES_DB}
export PGPASSWORD=${POSTGRES_PASSWORD}

for migration_file in /migrations/*.sql; do
	if [ -f "$migration_file" ]; then
		migration_name=$(basename "$migration_file")
        echo "Applying migration: $migration_name"
        psql -v ON_ERROR_STOP=1 -f "$migration_file"
	fi
done

