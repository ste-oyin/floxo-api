#!/bin/sh
set -e

if [ "$SERVICE_TYPE" = "worker" ]; then
    exec celery -A app.celery_app worker --loglevel=info
else
    exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
fi
