#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "${DATABASE_HOST:-postgres}" -U "${DB_USER:-anubis_user}" -d "${DB_NAME:-anubis_db}" 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is ready!"

# Create pgvector extension
echo "Setting up pgvector extension..."
PGPASSWORD="${DB_PASSWORD:-anubis_password}" psql \
  -h "${DATABASE_HOST:-postgres}" \
  -U "${DB_USER:-anubis_user}" \
  -d "${DB_NAME:-anubis_db}" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

echo "pgvector extension setup complete"

# Start Anubis server
echo "Starting Anubis RAG server..."
exec python -m anubis.server
