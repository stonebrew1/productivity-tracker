# Productivity Tracker

Full-stack MVP for a personal productivity system with tasks, categories, achievements, statistics, JWT auth, FastAPI, React, and PostgreSQL.

## Project Structure

```text
backend/   FastAPI API, SQLAlchemy models, services, schemas
frontend/  React + Vite UI
docker-compose.yml
```

## Run With Docker

```bash
docker compose up --build
```

Then open:

- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Main API Areas

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET/POST /api/categories`
- `GET/POST /api/tasks`
- `POST /api/tasks/{task_id}/complete`
- `GET /api/achievements`
- `GET /api/statistics`

## Notes

The backend creates tables automatically on startup for the MVP. Alembic is included as a dependency so migrations can be added when the schema stabilizes.
