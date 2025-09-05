#!/bin/sh
set -e

# Читаємо змінні з оточення
DB_HOST=${DB_HOST:-postgres}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-mydb}
DB_USER=${DB_USER:-admin}
DB_PASSWORD=${DB_PASSWORD:-admin123}

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 10
done

echo "PostgreSQL is up. Checking database $DB_NAME..."
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
  echo "Database $DB_NAME not found. Initializing..."
  PGPASSWORD="$DB_PASSWORD" python /app/scripts/init_db.py
else
  echo "Database $DB_NAME already exists. Skipping init."
fi

exec python /app/main.py
