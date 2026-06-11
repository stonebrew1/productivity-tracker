from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import achievements, auth, categories, social, statistics, tasks
from app.core.config import get_settings
from app.core.database import create_database_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_database_schema()
    yield


settings = get_settings()

app = FastAPI(
    title="Productivity Tracker API",
    description="Task, achievement, and productivity analytics API.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(categories.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")
app.include_router(achievements.router, prefix="/api")
app.include_router(statistics.router, prefix="/api")
app.include_router(social.router, prefix="/api")


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
