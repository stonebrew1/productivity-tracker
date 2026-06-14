from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import admin, achievements, auth, categories, gamification, groups, social, statistics, tasks
from app.core.config import get_settings
from app.core.database import create_database_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_database_schema()
    yield


settings = get_settings()
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Productivity Tracker API",
    description="Task, achievement, and productivity analytics API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_origin_regex=(
        r"^https?://("
        r"localhost|127\.0\.0\.1|"
        r"10(?:\.\d{1,3}){3}|"
        r"192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2}"
        r")(?::\d+)?$"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(achievements.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(social.router, prefix="/api")
app.include_router(gamification.router, prefix="/api")
app.include_router(groups.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
