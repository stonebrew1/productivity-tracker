import asyncio
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def create_database_schema() -> None:
    import app.models  # noqa: F401

    last_error: Exception | None = None
    for _ in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ"))
                await conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS estimated_minutes INTEGER"))
                await conn.execute(
                    text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_focus BOOLEAN NOT NULL DEFAULT FALSE")
                )
                await conn.execute(
                    text("CREATE INDEX IF NOT EXISTS ix_tasks_scheduled_for ON tasks (scheduled_for)")
                )
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS display_name VARCHAR(80)"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT"))
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_url VARCHAR(500)"))
                await conn.execute(
                    text("ALTER TABLE user_stats ADD COLUMN IF NOT EXISTS xp_total INTEGER NOT NULL DEFAULT 0")
                )
                await conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'taskvisibility') THEN
                                CREATE TYPE taskvisibility AS ENUM ('PRIVATE', 'PUBLIC');
                            END IF;
                        END
                        $$;
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE tasks
                        ADD COLUMN IF NOT EXISTS visibility taskvisibility NOT NULL DEFAULT 'PRIVATE'
                        """
                    )
                )
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1)
    if last_error:
        raise last_error
