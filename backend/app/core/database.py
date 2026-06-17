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
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_blocked BOOLEAN NOT NULL DEFAULT FALSE")
                )
                await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS blocked_at TIMESTAMPTZ"))
                await conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                            IF NOT EXISTS (
                                SELECT 1
                                FROM information_schema.columns
                                WHERE table_name = 'users'
                                  AND column_name = 'is_email_verified'
                            ) THEN
                                ALTER TABLE users
                                ADD COLUMN is_email_verified BOOLEAN NOT NULL DEFAULT TRUE;
                                ALTER TABLE users
                                ALTER COLUMN is_email_verified SET DEFAULT FALSE;
                            END IF;
                        END
                        $$;
                        """
                    )
                )
                await conn.execute(text("DROP TABLE IF EXISTS follows"))
                await conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS friendships (
                            id UUID PRIMARY KEY,
                            requester_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            addressee_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                            status VARCHAR(20) NOT NULL DEFAULT 'pending',
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                            responded_at TIMESTAMPTZ,
                            CONSTRAINT uq_friendships_pair UNIQUE (requester_id, addressee_id),
                            CONSTRAINT ck_friendships_not_self CHECK (requester_id <> addressee_id)
                        )
                        """
                    )
                )
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_friendships_requester_id ON friendships (requester_id)"))
                await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_friendships_addressee_id ON friendships (addressee_id)"))
                await conn.execute(
                    text(
                        """
                        DO $$
                        BEGIN
                            IF to_regclass('public.follows') IS NOT NULL THEN
                                INSERT INTO friendships (
                                    id, requester_id, addressee_id, status, created_at, responded_at
                                )
                                SELECT
                                    gen_random_uuid(),
                                    f.follower_id,
                                    f.followed_id,
                                    CASE WHEN reverse_follow.id IS NULL THEN 'pending' ELSE 'accepted' END,
                                    f.created_at,
                                    CASE WHEN reverse_follow.id IS NULL THEN NULL ELSE GREATEST(f.created_at, reverse_follow.created_at) END
                                FROM follows f
                                LEFT JOIN follows reverse_follow
                                  ON reverse_follow.follower_id = f.followed_id
                                 AND reverse_follow.followed_id = f.follower_id
                                WHERE f.follower_id::text < f.followed_id::text OR reverse_follow.id IS NULL
                                ON CONFLICT (requester_id, addressee_id) DO NOTHING;
                            END IF;
                        END
                        $$;
                        """
                    )
                )
                await conn.execute(
                    text(
                        """
                        ALTER TABLE notifications
                        ADD COLUMN IF NOT EXISTS friendship_id UUID
                        REFERENCES friendships(id) ON DELETE CASCADE
                        """
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                        "email_verification_token VARCHAR(64)"
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                        "email_verification_expires_at TIMESTAMPTZ"
                    )
                )
                await conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                        "email_verification_code VARCHAR(64)"
                    )
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_users_email_verification_token "
                        "ON users (email_verification_token)"
                    )
                )
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
                await conn.execute(
                    text(
                        "ALTER TABLE group_milestones "
                        "ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ"
                    )
                )
                await conn.execute(
                    text("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ")
                )
                await conn.execute(
                    text("UPDATE refresh_tokens SET created_at = NOW() WHERE created_at IS NULL")
                )
                await conn.execute(
                    text("ALTER TABLE refresh_tokens ALTER COLUMN created_at SET NOT NULL")
                )
                await conn.execute(
                    text("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ")
                )
                await conn.execute(
                    text("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS family_id UUID")
                )
                await conn.execute(
                    text("UPDATE refresh_tokens SET family_id = id WHERE family_id IS NULL")
                )
                await conn.execute(
                    text("ALTER TABLE refresh_tokens ALTER COLUMN family_id SET NOT NULL")
                )
                await conn.execute(
                    text("ALTER TABLE refresh_tokens ADD COLUMN IF NOT EXISTS replaced_by_token VARCHAR(255)")
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_family "
                        "ON refresh_tokens (family_id)"
                    )
                )
                await conn.execute(
                    text(
                        """
                        UPDATE refresh_tokens
                        SET revoked_at = COALESCE(revoked_at, NOW()),
                            token = md5(token || id::text) || md5(id::text || token)
                        WHERE token !~ '^[0-9a-f]{64}$'
                        """
                    )
                )
            return
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(1)
    if last_error:
        raise last_error
