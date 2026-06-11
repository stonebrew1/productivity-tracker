# Productivity Tracker

Full-stack personal productivity system with tasks, categories, achievements, statistics, task activity history, JWT auth, FastAPI, React, and PostgreSQL.

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
- `GET /api/tasks/history`
- `POST /api/tasks/{task_id}/complete`
- `GET /api/achievements`
- `GET /api/statistics`
- `GET /api/statistics/analytics`

## Notes

Task create, update, completion, status-change, and deletion events are stored in `task_events`. History remains available after task deletion and can be filtered by task, event type, and date range.

The analytics endpoint aggregates this history into daily, weekly, or monthly trends. It reports created, completed, and deleted tasks; on-time and overdue completion; and completed-task breakdowns by priority and category. The Statistics page exposes date and interval filters for the same report.

The backend currently creates new tables automatically on startup. Moving all schema changes to Alembic migrations is the next infrastructure milestone.

## Backend Tests

Inside the backend container:

```bash
pytest
```
