#!/bin/bash
set -e

# Wait for postgres to be ready (naive wait)
sleep 3

# Run Alembic migrations — safely creates or updates the database schema.
# "upgrade head" applies all pending migrations up to the latest version.
# On a fresh database this creates every table; on an existing database
# it only applies new migrations (e.g., adding a column).
echo "Running Alembic migrations..."
alembic upgrade head

# Run the seeder (inserts mock data if the database is empty)
python seed.py

# Start FastAPI
exec uvicorn main:app --host 0.0.0.0 --port 8000
