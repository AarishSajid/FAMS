#!/bin/bash
set -e

# Wait for postgres to be ready (naive wait)
sleep 3

# Run the seeder
python seed.py

# Start FastAPI
exec uvicorn main:app --host 0.0.0.0 --port 8000
