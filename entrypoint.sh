#!/bin/sh
set -e

# Читаємо змінні з оточення
DB_HOST=${DB_HOST:-chatbot_db}
DB_PORT=${DB_PORT:-5432}
DB_NAME=${DB_NAME:-mydb}
DB_USER=${DB_USER:-admin}
DB_PASSWORD=${DB_PASSWORD:-admin123}

echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 10
done

echo "PostgreSQL is up. Checking database $DB_NAME..."

# Перевіряємо, чи існує база
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
  echo "Database $DB_NAME not found. Initializing..."
  PGPASSWORD="$DB_PASSWORD" python /app/scripts/init_db.py
else
  # База існує, перевіряємо, чи є таблиці
  TABLE_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -tAc "SELECT count(*) FROM pg_tables WHERE schemaname='public';")
  
  if [ "$TABLE_COUNT" -eq 0 ]; then
    echo "Database $DB_NAME exists but is empty. Initializing..."
    PGPASSWORD="$DB_PASSWORD" python /app/scripts/init_db.py
  else
    echo "Database $DB_NAME already initialized with $TABLE_COUNT tables."
  fi
fi

echo "Running Alembic migrations..."
alembic upgrade head || {
  echo "Alembic failed, attempting init_db fallback..."
  python /app/scripts/init_db.py
}

exec python /app/main.py
