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
                await conn.execute(text("ALTER TABLE achievements ADD COLUMN IF NOT EXISTS code VARCHAR(80)"))
                await conn.execute(
                    text(
                        "ALTER TABLE achievements ADD COLUMN IF NOT EXISTS category VARCHAR(40) "
                        "NOT NULL DEFAULT 'milestone'"
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE achievements ADD COLUMN IF NOT EXISTS rarity VARCHAR(20) "
                        "NOT NULL DEFAULT 'common'"
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE achievements ADD COLUMN IF NOT EXISTS icon VARCHAR(40) "
                        "NOT NULL DEFAULT 'medal'"
                    )
                )
                await conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_achievements_user_code "
                        "ON achievements (user_id, code) WHERE code IS NOT NULL"
                    )
                )
                await conn.execute(text("ALTER TABLE xp_awards ALTER COLUMN task_id DROP NOT NULL"))
                await conn.execute(text("ALTER TABLE xp_awards ADD COLUMN IF NOT EXISTS source_key VARCHAR(180)"))
                await conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ux_xp_awards_source_key "
                        "ON xp_awards (source_key) WHERE source_key IS NOT NULL"
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE group_tasks
                        ADD COLUMN IF NOT EXISTS milestone_id UUID
                        REFERENCES group_milestones(id) ON DELETE SET NULL
                        """
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_group_tasks_milestone_id "
                        "ON group_tasks (milestone_id)"
                    )
                )
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1)
    if last_error:
        raise last_error
