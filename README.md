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

To access the app from another device on the same local network, open
`http://<computer-ip>:5173`. The frontend resolves its API through the same
hostname on port `8000`, and the backend accepts private-network browser origins.

## Main API Areas

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`
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
- `GET /api/social/leaderboard`
- `GET/POST /api/social/posts/{post_id}/comments`
- `DELETE /api/social/comments/{comment_id}`
- `GET /api/social/notifications`
- `POST /api/social/notifications/read`
- `GET /api/social/challenges`
- `POST/DELETE /api/social/challenges/{challenge_id}/join`
- `GET /api/social/commitments`
- `POST /api/social/tasks/{task_id}/accountability`
- `POST /api/social/commitments/{commitment_id}/accept`
- `POST /api/social/commitments/{commitment_id}/decline`
- `POST/DELETE /api/social/posts/{post_id}/reaction`
- `GET/POST /api/groups`
- `POST /api/groups/join`
- `GET /api/groups/invitations`
- `POST /api/groups/{group_id}/invitations`
- `POST /api/groups/{group_id}/invite-code`
- `GET/POST /api/groups/{group_id}/tasks`
- `PUT/DELETE /api/groups/tasks/{task_id}`
- `GET/POST /api/groups/{group_id}/milestones`
- `PUT/DELETE /api/groups/milestones/{milestone_id}`
- `GET /api/gamification`

## Notes

Authentication uses short-lived signed JWT access tokens and rotating opaque refresh tokens. Access tokens are kept in browser memory; refresh tokens are stored as hashes and delivered only through an `HttpOnly` cookie. Set a unique `SECRET_KEY` in production and enable `REFRESH_COOKIE_SECURE=true` behind HTTPS.

New registrations require a display name, a strong password, and email confirmation before login. Docker development sends messages through Mailpit; open `http://localhost:8025` to inspect the local inbox. For real delivery, configure the SMTP variables in the repository-root `.env`, set `FRONTEND_ORIGIN` to the public HTTPS URL, and use `SMTP_USE_SSL=true` for implicit TLS providers or `SMTP_USE_TLS=true` for STARTTLS.

Docker Compose reads SMTP overrides from a `.env` file in the repository root. Copy `.env.example` to `.env` and replace the sample Gmail values with a provider account and app password. Verification emails include both a magic link and a six-digit confirmation code.

On Windows, the file location is:

```text
C:\Users\user\Documents\Codex\2026-06-07\files-mentioned-by-the-user-req\.env
```

For Gmail, enable 2-Step Verification, create a Google app password, and use that app password as `SMTP_PASSWORD`. Restart the backend after changing `.env`, then inspect delivery diagnostics:

```bash
docker compose -p productivity-tracker up -d --force-recreate backend
docker compose -p productivity-tracker logs -f backend
```

SMTP logs report connection, TLS, authentication, send progress, and exceptions without printing the password, verification link, or confirmation code.

Task create, update, completion, status-change, and deletion events are stored in `task_events`. History remains available after task deletion and can be filtered by task, event type, and date range.

The analytics endpoint aggregates this history into daily, weekly, or monthly trends. It reports created, completed, and deleted tasks; on-time and overdue completion; and completed-task breakdowns by priority and category. The Statistics page exposes date and interval filters for the same report.

The default **Today** screen groups planned work into overdue, today, and next-seven-days queues. Tasks support a planned date (`scheduled_for`), effort estimate (`estimated_minutes`), and focus flag (`is_focus`), with quick creation and inline complete, start, and reschedule actions.

Phase 1 of the social loop awards 20 XP for a task's first completion, with a 200 XP daily cap. Public completions create one feed post; private tasks never enter the feed. Users can edit a profile, follow demo users, and react once to visible completion posts.

Phase 2 adds database-configurable XP rules, daily and weekly quests, quest bonus XP, a seven-badge catalog, locked-badge progress, streak milestones, and a three-badge profile showcase. Quest rewards are idempotent per user and period, and reset naturally at the next UTC day or week.

Phase 3 connects social activity back into progression. The Social page includes a follower-scoped weekly XP leaderboard, recent connection activity, and a weekly encouragement quest. Encouraging three followed-user updates awards 25 XP once per week and immediately updates progression and leaderboard position. Users cannot react to their own posts.

Phase 4 adds inline comments and an in-app notification inbox for follows, reactions, and comments. Commenting on two connection updates completes the weekly **Keep the conversation moving** quest for 20 XP. Feed access rules also apply to comments, comment authors can delete their own messages, and notifications can be marked read in one action.

Phase 5 introduces collaborative community challenges. Users can join time-boxed challenges where only public tasks completed after joining contribute to the shared target. When the team reaches its goal, every participant receives the challenge XP reward exactly once, and non-finishing participants receive a completion notification. Completed challenges cannot be left.

Phase 6 adds one-to-one accountability commitments. Owners can invite a followed user to support an unfinished public task. The invited partner accepts or declines in Social; after acceptance, both users see the commitment and each receives a one-time 15 XP bonus when the owner completes the task. Either participant may cancel before completion, while completed commitments remain immutable.

Group Phase 1 adds persistent group workspaces with leader and member roles. A leader can create a group, invite followed connections, copy or rotate a join code, and inspect the participant roster. Users can accept or decline direct invitations or join immediately with a code; join codes are visible only to the leader.

Group Phase 2 adds a shared task board. Leaders create tasks, set priority and deadlines, assign or reassign group members, update any task, and remove obsolete work. Assigned participants can move their own tasks through to-do, in-progress, and done states, while other members retain read-only visibility.

Group Phase 3 adds leader-configured milestones. Shared tasks can be linked or moved between milestones, and progress is derived automatically from the linked tasks' completion state. Deleting a milestone preserves its tasks and returns them to the unlinked pool.

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

For the Phase 3 demo, open **Social** and note the weekly leaderboard and the partially completed **Lift the circle** quest. Encourage an unreacted Maya or Leo update to complete the quest, then observe the awarded XP in Progression and the refreshed weekly ranking.

For the Phase 4 demo, the seeded account begins with one of two required comments and two unread notifications. Expand a Maya or Leo post, add one constructive comment, and observe the quest complete, the 20 XP award, the updated leaderboard, and the new notification on the post owner's account.

For the Phase 5 demo, the seeded **Public momentum sprint** begins at 12/13 with Alex, Maya, and Leo participating. Create and complete one public task to finish the team target. All three participants receive 40 XP once, the Social challenge card becomes complete, and the result appears under Team challenges in Progression. A second 6/8 challenge remains available to join.

For the Phase 6 demo, **Prepare project defense slides** is a public in-progress task with Maya already accepted as Alex's accountability partner. Complete it from Tasks or Today: Alex and Maya each receive 15 XP, Maya receives a completion notification, and the commitment moves from accepted to completed.

For the group demo, Alex leads **Bachelor Project Lab** with Maya already participating. Three milestones show completed, active, and early-stage progress driven by four linked tasks. Alex can configure milestones and create, reassign, drag, update, or delete tasks; sign in as Maya to move her assigned work while seeing Alex's tasks as read-only. The leader can also copy the seeded `MOMENTUM` code, rotate it, or invite followed connections. Sign in as `leo@example.com` with the same demo password to accept the pending invitation.
