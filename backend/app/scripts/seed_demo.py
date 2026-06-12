import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import delete, or_, select

from app.core.database import AsyncSessionLocal, create_database_schema
from app.core.security import hash_password
from app.models.achievement import Achievement
from app.models.category import Category
from app.models.group import GroupInvitation, GroupMember, GroupMilestone, GroupTask, ProductivityGroup
from app.models.social import (
    ActivityPost,
    AccountabilityCommitment,
    Challenge,
    ChallengeMember,
    Follow,
    GamificationRule,
    Notification,
    PostComment,
    PostReaction,
    QuestCompletion,
    XpAward,
)
from app.models.task import Task, TaskPriority, TaskStatus, TaskVisibility
from app.models.task_event import TaskEvent, TaskEventType
from app.models.user import User
from app.models.user_stats import UserStats
from app.services.achievement_service import check_and_award
from app.services.gamification_service import award_quest_rewards


DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "password123"
SOCIAL_USERS = [
    ("maya@example.com", "Maya Chen", "Finishing a data science portfolio one focused session at a time."),
    ("leo@example.com", "Leo Martins", "Training consistently while shipping my final university project."),
]

TASK_BLUEPRINTS = [
    ("Submit database coursework", "Study", TaskPriority.HIGH, 29, -1),
    ("Review distributed systems notes", "Study", TaskPriority.MEDIUM, 27, 1),
    ("Complete API authentication module", "Work", TaskPriority.HIGH, 25, -2),
    ("Prepare weekly client update", "Work", TaskPriority.MEDIUM, 23, 0),
    ("Run five kilometers", "Health", TaskPriority.MEDIUM, 21, -1),
    ("Read research paper on event sourcing", "Study", TaskPriority.LOW, 19, 2),
    ("Refactor analytics service", "Work", TaskPriority.HIGH, 17, -1),
    ("Book dental appointment", "Personal", TaskPriority.LOW, 16, 3),
    ("Finish React dashboard", "Work", TaskPriority.HIGH, 14, 0),
    ("Practice English presentation", "Study", TaskPriority.MEDIUM, 13, -1),
    ("Complete strength workout", "Health", TaskPriority.MEDIUM, 11, 1),
    ("Write bachelor project introduction", "Study", TaskPriority.HIGH, 10, -2),
    ("Organize monthly expenses", "Personal", TaskPriority.MEDIUM, 8, 0),
    ("Add backend test coverage", "Work", TaskPriority.HIGH, 7, -1),
    ("Prepare architecture diagrams", "Study", TaskPriority.HIGH, 5, 2),
    ("Plan meals for the week", "Health", TaskPriority.LOW, 4, -1),
    ("Update project documentation", "Work", TaskPriority.MEDIUM, 3, 0),
    ("Complete statistics chapter draft", "Study", TaskPriority.HIGH, 2, -1),
]

OPEN_TASKS = [
    ("Prepare project defense slides", "Study", TaskPriority.HIGH, 5, 0, 90, True, TaskStatus.IN_PROGRESS),
    ("Implement CSV analytics export", "Work", TaskPriority.MEDIUM, 8, 1, 60, True, TaskStatus.TODO),
    ("Schedule weekly running plan", "Health", TaskPriority.LOW, 4, 0, 25, False, TaskStatus.TODO),
    ("Renew cloud hosting subscription", "Personal", TaskPriority.MEDIUM, 2, -2, 15, False, TaskStatus.IN_PROGRESS),
    ("Research notification queues", "Work", TaskPriority.LOW, 10, 3, 45, False, TaskStatus.TODO),
    ("Outline usability testing plan", "Study", TaskPriority.MEDIUM, 7, -1, 50, True, TaskStatus.TODO),
]


def event_snapshot(
    status: TaskStatus,
    priority: TaskPriority,
    category_id: str,
    deadline: datetime | None,
    completed_at: datetime | None,
    scheduled_for: datetime | None = None,
    estimated_minutes: int | None = None,
    is_focus: bool = False,
) -> dict:
    return {
        "status": status.value,
        "priority": priority.value,
        "category_id": category_id,
        "deadline": deadline.isoformat() if deadline else None,
        "completed_at": completed_at.isoformat() if completed_at else None,
        "scheduled_for": scheduled_for.isoformat() if scheduled_for else None,
        "estimated_minutes": estimated_minutes,
        "is_focus": is_focus,
    }


async def seed_demo() -> None:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    await create_database_schema()

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if not user:
            user = User(email=DEMO_EMAIL, password_hash=hash_password(DEMO_PASSWORD))
            db.add(user)
            await db.flush()
        else:
            user.password_hash = hash_password(DEMO_PASSWORD)
        user.display_name = "Alex Morgan"
        user.bio = "Building a strong bachelor project through small, consistent wins."

        peers: list[User] = []
        for email, display_name, bio in SOCIAL_USERS:
            peer = await db.scalar(select(User).where(User.email == email))
            if not peer:
                peer = User(email=email, password_hash=hash_password(DEMO_PASSWORD))
                db.add(peer)
                await db.flush()
            peer.password_hash = hash_password(DEMO_PASSWORD)
            peer.display_name = display_name
            peer.bio = bio
            peers.append(peer)

        seeded_users = [user, *peers]
        seeded_user_ids = [item.id for item in seeded_users]
        seeded_group_ids = list(
            await db.scalars(
                select(ProductivityGroup.id).where(ProductivityGroup.leader_id.in_(seeded_user_ids))
            )
        )
        if seeded_group_ids:
            await db.execute(delete(GroupTask).where(GroupTask.group_id.in_(seeded_group_ids)))
            await db.execute(
                delete(GroupMilestone).where(GroupMilestone.group_id.in_(seeded_group_ids))
            )
            await db.execute(
                delete(GroupInvitation).where(GroupInvitation.group_id.in_(seeded_group_ids))
            )
            await db.execute(delete(GroupMember).where(GroupMember.group_id.in_(seeded_group_ids)))
            await db.execute(
                delete(ProductivityGroup).where(ProductivityGroup.id.in_(seeded_group_ids))
            )
        await db.execute(
            delete(AccountabilityCommitment).where(
                or_(
                    AccountabilityCommitment.owner_id.in_(seeded_user_ids),
                    AccountabilityCommitment.partner_id.in_(seeded_user_ids),
                )
            )
        )
        await db.execute(delete(ChallengeMember).where(ChallengeMember.user_id.in_(seeded_user_ids)))
        await db.execute(delete(Challenge))
        await db.execute(
            delete(Notification).where(
                or_(
                    Notification.recipient_id.in_(seeded_user_ids),
                    Notification.actor_id.in_(seeded_user_ids),
                )
            )
        )
        await db.execute(delete(PostComment).where(PostComment.user_id.in_(seeded_user_ids)))
        await db.execute(delete(PostReaction).where(PostReaction.user_id.in_(seeded_user_ids)))
        await db.execute(delete(ActivityPost).where(ActivityPost.user_id.in_(seeded_user_ids)))
        await db.execute(
            delete(Follow).where(
                or_(Follow.follower_id.in_(seeded_user_ids), Follow.followed_id.in_(seeded_user_ids))
            )
        )
        await db.execute(delete(QuestCompletion).where(QuestCompletion.user_id.in_(seeded_user_ids)))
        await db.execute(delete(XpAward).where(XpAward.user_id.in_(seeded_user_ids)))
        await db.execute(delete(GamificationRule))

        await db.execute(delete(Achievement).where(Achievement.user_id.in_(seeded_user_ids)))
        await db.execute(delete(TaskEvent).where(TaskEvent.user_id.in_(seeded_user_ids)))
        await db.execute(delete(Task).where(Task.user_id.in_(seeded_user_ids)))
        await db.execute(delete(Category).where(Category.user_id.in_(seeded_user_ids)))
        await db.execute(delete(UserStats).where(UserStats.user_id.in_(seeded_user_ids)))
        await db.flush()

        categories = {
            name: Category(name=name, user_id=user.id)
            for name in ("Study", "Work", "Health", "Personal")
        }
        db.add_all(categories.values())
        await db.flush()

        completed_tasks: list[Task] = []
        for index, (title, category_name, priority, age_days, timing_days) in enumerate(TASK_BLUEPRINTS):
            created_at = now - timedelta(days=age_days, hours=2 + index % 5)
            deadline = created_at + timedelta(days=3 + index % 4)
            completed_at = min(
                deadline + timedelta(days=timing_days),
                now - timedelta(hours=index + 1),
            )
            if index >= len(TASK_BLUEPRINTS) - 4:
                completed_at = now - timedelta(days=len(TASK_BLUEPRINTS) - 1 - index, hours=1)
            category = categories[category_name]
            task = Task(
                title=title,
                description=f"Demo activity for the {category_name.lower()} category.",
                priority=priority,
                status=TaskStatus.DONE,
                deadline=deadline,
                completed_at=completed_at,
                user_id=user.id,
                category_id=category.id,
                visibility=TaskVisibility.PUBLIC if index >= len(TASK_BLUEPRINTS) - 6 else TaskVisibility.PRIVATE,
            )
            db.add(task)
            await db.flush()
            completed_tasks.append(task)
            db.add(
                XpAward(
                    task_id=task.id,
                    source_key=f"task:{task.id}",
                    user_id=user.id,
                    amount=20,
                    awarded_at=completed_at,
                )
            )
            if task.visibility == TaskVisibility.PUBLIC:
                db.add(
                    ActivityPost(
                        task_id=task.id,
                        task_title=task.title,
                        xp_awarded=20,
                        created_at=completed_at,
                        user_id=user.id,
                    )
                )

            db.add(
                TaskEvent(
                    event_type=TaskEventType.CREATED,
                    task_id=task.id,
                    task_title=task.title,
                    user_id=user.id,
                    occurred_at=created_at,
                    changes={
                        "title": {"from": None, "to": task.title},
                        "_snapshot": event_snapshot(
                            TaskStatus.TODO,
                            priority,
                            str(category.id),
                            deadline,
                            None,
                        ),
                    },
                )
            )
            db.add(
                TaskEvent(
                    event_type=TaskEventType.COMPLETED,
                    task_id=task.id,
                    task_title=task.title,
                    user_id=user.id,
                    occurred_at=completed_at,
                    changes={
                        "status": {"from": TaskStatus.TODO.value, "to": TaskStatus.DONE.value},
                        "_snapshot": event_snapshot(
                            TaskStatus.DONE,
                            priority,
                            str(category.id),
                            deadline,
                            completed_at,
                        ),
                    },
                )
            )

        open_tasks_created: list[Task] = []
        for index, (
            title,
            category_name,
            priority,
            due_in_days,
            schedule_offset,
            estimated_minutes,
            is_focus,
            task_status,
        ) in enumerate(OPEN_TASKS):
            created_at = now - timedelta(days=6 - index, hours=index)
            deadline = now + timedelta(days=due_in_days)
            scheduled_for = now.replace(hour=9 + index, minute=0, second=0) + timedelta(days=schedule_offset)
            category = categories[category_name]
            task = Task(
                title=title,
                description="Upcoming demo task.",
                priority=priority,
                status=task_status,
                deadline=deadline,
                scheduled_for=scheduled_for,
                estimated_minutes=estimated_minutes,
                is_focus=is_focus,
                visibility=TaskVisibility.PUBLIC if index == 0 else TaskVisibility.PRIVATE,
                user_id=user.id,
                category_id=category.id,
            )
            db.add(task)
            await db.flush()
            open_tasks_created.append(task)
            db.add(
                TaskEvent(
                    event_type=TaskEventType.CREATED,
                    task_id=task.id,
                    task_title=task.title,
                    user_id=user.id,
                    occurred_at=created_at,
                    changes={
                        "_snapshot": event_snapshot(
                            TaskStatus.TODO,
                            priority,
                            str(category.id),
                            deadline,
                            None,
                            scheduled_for,
                            estimated_minutes,
                            is_focus,
                        )
                    },
                )
            )
            if task_status == TaskStatus.IN_PROGRESS:
                db.add(
                    TaskEvent(
                        event_type=TaskEventType.STATUS_CHANGED,
                        task_id=task.id,
                        task_title=task.title,
                        user_id=user.id,
                        occurred_at=created_at + timedelta(hours=8),
                        changes={
                            "status": {
                                "from": TaskStatus.TODO.value,
                                "to": TaskStatus.IN_PROGRESS.value,
                            },
                            "_snapshot": event_snapshot(
                                TaskStatus.IN_PROGRESS,
                                priority,
                                str(category.id),
                                deadline,
                                None,
                                scheduled_for,
                                estimated_minutes,
                                is_focus,
                            ),
                        },
                    )
                )

        for index, category_name in enumerate(("Work", "Personal", "Study")):
            task_id = uuid4()
            created_at = now - timedelta(days=22 - index * 6)
            deleted_at = created_at + timedelta(days=2)
            category = categories[category_name]
            snapshot = event_snapshot(
                TaskStatus.TODO,
                TaskPriority.LOW,
                str(category.id),
                created_at + timedelta(days=5),
                None,
            )
            db.add_all(
                [
                    TaskEvent(
                        event_type=TaskEventType.CREATED,
                        task_id=task_id,
                        task_title=f"Archived {category_name.lower()} idea",
                        user_id=user.id,
                        occurred_at=created_at,
                        changes={"_snapshot": snapshot},
                    ),
                    TaskEvent(
                        event_type=TaskEventType.DELETED,
                        task_id=task_id,
                        task_title=f"Archived {category_name.lower()} idea",
                        user_id=user.id,
                        occurred_at=deleted_at,
                        changes={"snapshot": snapshot, "_snapshot": snapshot},
                    ),
                ]
            )

        stats = UserStats(
            total_tasks=len(TASK_BLUEPRINTS) + len(OPEN_TASKS),
            completed_tasks=len(TASK_BLUEPRINTS),
            current_streak=4,
            xp_total=len(TASK_BLUEPRINTS) * 20,
            user_id=user.id,
        )
        db.add(stats)
        await db.flush()
        await check_and_award(user.id, completed_tasks[-1], db)
        await award_quest_rewards(user.id, db)

        peer_posts: list[ActivityPost] = []
        peer_task_titles = [
            ["Publish portfolio case study", "Complete Python practice set", "Review model evaluation notes"],
            ["Finish interval training", "Write system design section", "Prepare supervisor meeting notes"],
        ]
        peer_xp = [260, 180]
        for peer_index, peer in enumerate(peers):
            category = Category(name="Shared goals", user_id=peer.id)
            db.add(category)
            await db.flush()
            db.add(
                UserStats(
                    total_tasks=3,
                    completed_tasks=3,
                    current_streak=7 - peer_index * 2,
                    xp_total=peer_xp[peer_index],
                    user_id=peer.id,
                )
            )
            for task_index, title in enumerate(peer_task_titles[peer_index]):
                completed_at = now - timedelta(hours=4 + peer_index * 3 + task_index * 19)
                task = Task(
                    title=title,
                    priority=TaskPriority.MEDIUM,
                    status=TaskStatus.DONE,
                    completed_at=completed_at,
                    visibility=TaskVisibility.PUBLIC,
                    user_id=peer.id,
                    category_id=category.id,
                )
                db.add(task)
                await db.flush()
                db.add(
                    XpAward(
                        task_id=task.id,
                        source_key=f"task:{task.id}",
                        user_id=peer.id,
                        amount=20,
                        awarded_at=completed_at,
                    )
                )
                post = ActivityPost(
                    task_id=task.id,
                    task_title=task.title,
                    xp_awarded=20,
                    created_at=completed_at,
                    user_id=peer.id,
                )
                db.add(post)
                peer_posts.append(post)

        await db.flush()
        db.add_all(
            [
                Follow(follower_id=user.id, followed_id=peers[0].id),
                Follow(follower_id=user.id, followed_id=peers[1].id),
                Follow(follower_id=peers[0].id, followed_id=user.id),
                Follow(follower_id=peers[1].id, followed_id=user.id),
            ]
        )
        demo_posts = list(
            await db.scalars(
                select(ActivityPost)
                .where(ActivityPost.user_id == user.id)
                .order_by(ActivityPost.created_at.desc())
                .limit(3)
            )
        )
        db.add_all(
            [
                PostReaction(post_id=peer_posts[0].id, user_id=user.id),
                PostReaction(post_id=peer_posts[3].id, user_id=user.id),
                PostReaction(post_id=demo_posts[0].id, user_id=peers[0].id),
                PostReaction(post_id=demo_posts[0].id, user_id=peers[1].id),
                PostReaction(post_id=demo_posts[1].id, user_id=peers[0].id),
            ]
        )
        db.add_all(
            [
                PostComment(
                    post_id=peer_posts[1].id,
                    user_id=user.id,
                    content="The consistency is showing. Nice work keeping the practice loop moving.",
                    created_at=now - timedelta(hours=2),
                ),
                PostComment(
                    post_id=demo_posts[0].id,
                    user_id=peers[0].id,
                    content="This is a strong milestone for the project. Keep the next step just as concrete.",
                    created_at=now - timedelta(hours=1, minutes=20),
                ),
                PostComment(
                    post_id=demo_posts[1].id,
                    user_id=peers[1].id,
                    content="Great progress. The steady pace is doing the heavy lifting here.",
                    created_at=now - timedelta(minutes=45),
                ),
                Notification(
                    kind="comment",
                    message=f"commented on your completion of {demo_posts[0].task_title}",
                    recipient_id=user.id,
                    actor_id=peers[0].id,
                    post_id=demo_posts[0].id,
                    created_at=now - timedelta(hours=1, minutes=20),
                ),
                Notification(
                    kind="comment",
                    message=f"commented on your completion of {demo_posts[1].task_title}",
                    recipient_id=user.id,
                    actor_id=peers[1].id,
                    post_id=demo_posts[1].id,
                    created_at=now - timedelta(minutes=45),
                ),
                Notification(
                    kind="reaction",
                    message=f"encouraged your completion of {demo_posts[0].task_title}",
                    recipient_id=user.id,
                    actor_id=peers[1].id,
                    post_id=demo_posts[0].id,
                    is_read=True,
                    created_at=now - timedelta(hours=3),
                ),
            ]
        )
        challenge_start = now - timedelta(days=7)
        challenge_end = now + timedelta(days=7)
        momentum_challenge = Challenge(
            code="public_momentum_sprint",
            title="Public momentum sprint",
            description="Complete 13 public tasks together before the sprint closes.",
            target=13,
            reward_xp=40,
            starts_at=challenge_start,
            ends_at=challenge_end,
        )
        focus_relay = Challenge(
            code="community_finish_line",
            title="Community finish line",
            description="Join the circle and help complete eight public tasks as a team.",
            target=8,
            reward_xp=30,
            starts_at=challenge_start,
            ends_at=challenge_end,
        )
        db.add_all([momentum_challenge, focus_relay])
        await db.flush()
        db.add_all(
            [
                ChallengeMember(
                    challenge_id=momentum_challenge.id,
                    user_id=member.id,
                    joined_at=challenge_start,
                )
                for member in seeded_users
            ]
            + [
                ChallengeMember(
                    challenge_id=focus_relay.id,
                    user_id=peer.id,
                    joined_at=challenge_start,
                )
                for peer in peers
            ]
        )
        db.add(
            AccountabilityCommitment(
                task_id=open_tasks_created[0].id,
                owner_id=user.id,
                partner_id=peers[0].id,
                status="accepted",
                responded_at=now - timedelta(hours=3),
                created_at=now - timedelta(hours=5),
            )
        )
        demo_group = ProductivityGroup(
            name="Bachelor Project Lab",
            description="A shared workspace for planning, building, and preparing the project defense.",
            invite_code="MOMENTUM",
            leader_id=user.id,
            created_at=now - timedelta(days=12),
        )
        db.add(demo_group)
        await db.flush()
        scope_milestone = GroupMilestone(
            group_id=demo_group.id,
            title="Scope approved",
            description="Research question, project boundaries, and evaluation criteria are agreed.",
            target_date=now - timedelta(days=5),
            created_at=now - timedelta(days=12),
        )
        prototype_milestone = GroupMilestone(
            group_id=demo_group.id,
            title="Prototype validation ready",
            description="Architecture and usability materials are ready for the validation session.",
            target_date=now + timedelta(days=5),
            created_at=now - timedelta(days=6),
        )
        defense_milestone = GroupMilestone(
            group_id=demo_group.id,
            title="Defense preparation complete",
            description="Questions, slides, and final demonstration are rehearsed.",
            target_date=now + timedelta(days=14),
            created_at=now - timedelta(days=2),
        )
        db.add_all([scope_milestone, prototype_milestone, defense_milestone])
        await db.flush()
        db.add_all(
            [
                GroupMember(
                    group_id=demo_group.id,
                    user_id=user.id,
                    role="leader",
                    joined_at=demo_group.created_at,
                ),
                GroupMember(
                    group_id=demo_group.id,
                    user_id=peers[0].id,
                    role="member",
                    joined_at=now - timedelta(days=9),
                ),
                GroupInvitation(
                    group_id=demo_group.id,
                    invited_user_id=peers[1].id,
                    invited_by_id=user.id,
                    created_at=now - timedelta(hours=8),
                ),
                Notification(
                    kind="group",
                    message=f"invited you to join {demo_group.name}",
                    recipient_id=peers[1].id,
                    actor_id=user.id,
                    created_at=now - timedelta(hours=8),
                ),
                GroupTask(
                    group_id=demo_group.id,
                    title="Approve project scope",
                    description="Confirm the final research question and success criteria.",
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.DONE,
                    deadline=now - timedelta(days=5),
                    completed_at=now - timedelta(days=6),
                    assigned_to_id=user.id,
                    created_by_id=user.id,
                    milestone_id=scope_milestone.id,
                    created_at=now - timedelta(days=11),
                ),
                GroupTask(
                    group_id=demo_group.id,
                    title="Prepare usability test script",
                    description="Write the five moderated testing prompts for the prototype.",
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.IN_PROGRESS,
                    deadline=now + timedelta(days=2),
                    assigned_to_id=peers[0].id,
                    created_by_id=user.id,
                    milestone_id=prototype_milestone.id,
                    created_at=now - timedelta(days=4),
                ),
                GroupTask(
                    group_id=demo_group.id,
                    title="Review architecture diagram",
                    description="Check service boundaries and database relationships.",
                    priority=TaskPriority.MEDIUM,
                    status=TaskStatus.DONE,
                    deadline=now + timedelta(days=4),
                    completed_at=now - timedelta(hours=14),
                    assigned_to_id=user.id,
                    created_by_id=user.id,
                    milestone_id=prototype_milestone.id,
                    created_at=now - timedelta(days=2),
                ),
                GroupTask(
                    group_id=demo_group.id,
                    title="Collect defense questions",
                    description="Add likely examiner questions to the shared preparation list.",
                    priority=TaskPriority.LOW,
                    status=TaskStatus.TODO,
                    deadline=now + timedelta(days=7),
                    assigned_to_id=peers[0].id,
                    created_by_id=user.id,
                    milestone_id=defense_milestone.id,
                    created_at=now - timedelta(days=1),
                ),
            ]
        )
        await db.commit()

    print(
        f"Seeded {DEMO_EMAIL}: {len(TASK_BLUEPRINTS)} completed tasks, "
        f"{len(OPEN_TASKS)} active tasks, 3 deleted-task histories, gamification progress, "
        f"{len(SOCIAL_USERS)} social demo users, 2 collaborative challenges, "
        "1 accepted accountability commitment, and 1 group workspace with 3 milestones and 4 shared tasks."
    )


if __name__ == "__main__":
    asyncio.run(seed_demo())
