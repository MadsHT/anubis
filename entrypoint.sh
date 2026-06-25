#!/bin/bash
set -e

# Parse DATABASE_URL to extract connection parameters
# Format: postgresql://user:password@host:port/database
if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL environment variable not set"
  exit 1
fi

# Extract components from DATABASE_URL using parameter expansion
DB_URL="${DATABASE_URL#postgresql://}"  # Remove protocol
DB_USERPASS="${DB_URL%@*}"               # Everything before @
DB_HOSTPORT="${DB_URL#*@}"               # Everything after @
DB_HOST="${DB_HOSTPORT%/*}"              # Host:port part
DB_NAME="${DB_HOSTPORT#*/}"              # Database name
DB_USER="${DB_USERPASS%:*}"              # Username
DB_PASS="${DB_USERPASS#*:}"              # Password

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready at $DB_HOST..."
HOST_ONLY="${DB_HOST%:*}"
until pg_isready -h "$HOST_ONLY" -U "$DB_USER" -d "$DB_NAME" 2>/dev/null; do
  echo "PostgreSQL is unavailable - sleeping"
  sleep 1
done
echo "PostgreSQL is ready!"

# Create pgvector extension
echo "Setting up pgvector extension..."
export PGPASSWORD="$DB_PASS"
psql \
  -h "$HOST_ONLY" \
  -U "$DB_USER" \
  -d "$DB_NAME" \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" || true

echo "pgvector extension setup complete"

# Start Anubis server
echo "Starting Anubis RAG server..."
exec python -m anubis.server
