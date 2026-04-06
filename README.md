# Floxo API

Backend API and video processing pipeline for Floxo.

## Tech stack

- **FastAPI** — HTTP API
- **Celery** — background jobs
- **Redis** — Celery broker and result backend
- **Supabase** — storage and PostgreSQL
- **YOLOv8** (Ultralytics) — person detection
- **ByteTrack** (via Supervision) — multi-object tracking

## Getting started

Copy `.env.example` to `.env`, fill in Supabase and database settings, then:

```bash
docker compose up --build
```

The API listens on [http://localhost:8000](http://localhost:8000). Health check: `GET /health`.

Celery workers load `process_video` and `cleanup_videos` tasks from `app.tasks.process_video` and `app.tasks.cleanup`.

## Branch strategy

| Branch        | Purpose                                      |
|---------------|----------------------------------------------|
| `main`        | Production-ready releases                    |
| `test`        | Staging and QA                               |
| `development` | Active development and integration testing   |
