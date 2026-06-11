from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Follow(Base):
    __tablename__ = "follows"
    __table_args__ = (
        UniqueConstraint("follower_id", "followed_id", name="uq_follows_pair"),
        CheckConstraint("follower_id <> followed_id", name="ck_follows_not_self"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    follower_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    followed_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class XpAward(Base):
    __tablename__ = "xp_awards"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_xp_awards_task"),
        UniqueConstraint("source_key", name="uq_xp_awards_source"),
        Index("ix_xp_awards_user_awarded", "user_id", "awarded_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    amount: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(80), default="task_completed")
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    task_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    source_key: Mapped[str | None] = mapped_column(String(180), nullable=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    user = relationship("User", back_populates="xp_awards")


class GamificationRule(Base):
    __tablename__ = "gamification_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")


class QuestCompletion(Base):
    __tablename__ = "quest_completions"
    __table_args__ = (
        UniqueConstraint("user_id", "quest_code", "period_start", name="uq_quest_completion_period"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    quest_code: Mapped[str] = mapped_column(String(80))
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    xp_awarded: Mapped[int] = mapped_column(Integer)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class ActivityPost(Base):
    __tablename__ = "activity_posts"
    __table_args__ = (
        UniqueConstraint("task_id", name="uq_activity_posts_task"),
        Index("ix_activity_posts_created", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True))
    task_title: Mapped[str] = mapped_column(String(200))
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    user = relationship("User", back_populates="activity_posts")
    reactions = relationship("PostReaction", back_populates="post", cascade="all, delete-orphan")


class PostReaction(Base):
    __tablename__ = "post_reactions"
    __table_args__ = (UniqueConstraint("post_id", "user_id", name="uq_post_reactions_user"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    post_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("activity_posts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    post = relationship("ActivityPost", back_populates="reactions")
