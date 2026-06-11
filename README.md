# Productivity Tracker

Full-stack social productivity system with tasks, profiles, XP progression, private sharing controls, follows, activity feeds, reactions, achievements, analytics, JWT auth, FastAPI, React, and PostgreSQL.

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
- `GET/PUT /api/social/profile`
- `GET /api/social/people`
- `POST/DELETE /api/social/people/{user_id}/follow`
- `GET /api/social/feed`
- `POST/DELETE /api/social/posts/{post_id}/reaction`
- `GET /api/gamification`

## Notes

Task create, update, completion, status-change, and deletion events are stored in `task_events`. History remains available after task deletion and can be filtered by task, event type, and date range.

The analytics endpoint aggregates this history into daily, weekly, or monthly trends. It reports created, completed, and deleted tasks; on-time and overdue completion; and completed-task breakdowns by priority and category. The Statistics page exposes date and interval filters for the same report.

The default **Today** screen groups planned work into overdue, today, and next-seven-days queues. Tasks support a planned date (`scheduled_for`), effort estimate (`estimated_minutes`), and focus flag (`is_focus`), with quick creation and inline complete, start, and reschedule actions.

Phase 1 of the social loop awards 20 XP for a task's first completion, with a 200 XP daily cap. Public completions create one feed post; private tasks never enter the feed. Users can edit a profile, follow demo users, and react once to visible completion posts.

Phase 2 adds database-configurable XP rules, daily and weekly quests, quest bonus XP, a seven-badge catalog, locked-badge progress, streak milestones, and a three-badge profile showcase. Quest rewards are idempotent per user and period, and reset naturally at the next UTC day or week.

The backend currently creates new tables automatically on startup. Moving all schema changes to Alembic migrations is the next infrastructure milestone.

## Backend Tests

Inside the backend container:

```bash
pytest
```

## Demo Data

Populate or reset the primary demo account and two connected social accounts:

```bash
docker compose run --rm backend python -m app.scripts.seed_demo
```

Demo credentials:

- Email: `demo@example.com`
- Password: `password123`

The seeded account follows Maya and Leo and opens with public completion posts and reactions. To demo the full loop, create a task using the globe privacy control, complete it, and open **Social** to see the new post and XP progress.

For the Phase 2 demo, open **Gamification** first to see the mixed quest and badge state. Completing a public focus task advances the remaining quests, awards any earned bonus XP once, and updates the level bar and profile badge showcase.
