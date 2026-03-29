#!/bin/sh
set -e
alembic upgrade head
exec uvicorn app.main:app --host 127.0.0.1 --port 8000
