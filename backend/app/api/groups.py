from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupActivityCreate,
    GroupActivityCommentRead,
    GroupActivityRead,
    GroupAchievementRead,
    GroupAnalyticsRead,
    GroupChallengeCreate,
    GroupChallengeRead,
    GroupInvitationRead,
    GroupInvite,
    GroupJoin,
    GroupMilestoneCreate,
    GroupMilestoneRead,
    GroupMilestoneUpdate,
    GroupProgressRead,
    GroupRead,
    GroupTaskCreate,
    GroupTaskRead,
    GroupTaskUpdate,
)
from app.services.group_service import (
    create_group,
    invite_user,
    join_by_code,
    list_groups,
    list_invitations,
    respond_invitation,
    rotate_invite_code,
)
from app.services.group_task_service import (
    create_group_task,
    delete_group_task,
    list_group_tasks,
    update_group_task,
)
from app.services.group_milestone_service import (
    create_milestone,
    delete_milestone,
    list_milestones,
    update_milestone,
)
from app.services.group_progress_service import group_progress
from app.services.group_activity_service import (
    create_activity_comment,
    create_group_update,
    delete_activity_comment,
    list_group_activity,
    react_to_activity,
    remove_activity_reaction,
)
from app.services.group_analytics_service import group_analytics
from app.services.group_challenge_service import (
    create_group_challenge,
    delete_group_challenge,
    list_group_challenges,
)
from app.services.group_achievement_service import list_group_achievements


router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupRead])
async def read_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupRead]:
    return await list_groups(current_user.id, db)


@router.post("", response_model=GroupRead, status_code=201)
async def create_group_route(
    payload: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupRead:
    return await create_group(payload.name, payload.description, current_user, db)


@router.post("/join", response_model=GroupRead)
async def join_group(
    payload: GroupJoin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupRead:
    return await join_by_code(payload.invite_code, current_user, db)


@router.get("/invitations", response_model=list[GroupInvitationRead])
async def read_group_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupInvitationRead]:
    return await list_invitations(current_user.id, db)


@router.post("/invitations/{invitation_id}/accept", status_code=204)
async def accept_group_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await respond_invitation(invitation_id, current_user, True, db)


@router.post("/invitations/{invitation_id}/decline", status_code=204)
async def decline_group_invitation(
    invitation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await respond_invitation(invitation_id, current_user, False, db)


@router.post("/{group_id}/invitations", status_code=204)
async def invite_group_member(
    group_id: UUID,
    payload: GroupInvite,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await invite_user(group_id, payload.user_id, current_user, db)


@router.post("/{group_id}/invite-code", response_model=GroupRead)
async def regenerate_group_code(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupRead:
    return await rotate_invite_code(group_id, current_user.id, db)


@router.get("/{group_id}/tasks", response_model=list[GroupTaskRead])
async def read_group_tasks(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupTaskRead]:
    return await list_group_tasks(group_id, current_user.id, db)


@router.post("/{group_id}/tasks", response_model=GroupTaskRead, status_code=201)
async def create_group_task_route(
    group_id: UUID,
    payload: GroupTaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupTaskRead:
    return await create_group_task(group_id, payload, current_user, db)


@router.get("/{group_id}/progress", response_model=GroupProgressRead)
async def read_group_progress(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupProgressRead:
    return await group_progress(group_id, current_user.id, db)


@router.get("/{group_id}/activity", response_model=list[GroupActivityRead])
async def read_group_activity(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupActivityRead]:
    return await list_group_activity(group_id, current_user.id, db)


@router.get("/{group_id}/analytics", response_model=GroupAnalyticsRead)
async def read_group_analytics(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupAnalyticsRead:
    return await group_analytics(group_id, current_user.id, db)


@router.get("/{group_id}/challenges", response_model=list[GroupChallengeRead])
async def read_group_challenges(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupChallengeRead]:
    return await list_group_challenges(group_id, current_user.id, db)


@router.get("/{group_id}/achievements", response_model=list[GroupAchievementRead])
async def read_group_achievements(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupAchievementRead]:
    return await list_group_achievements(group_id, current_user.id, db)


@router.post("/{group_id}/challenges", response_model=GroupChallengeRead, status_code=201)
async def create_group_challenge_route(
    group_id: UUID,
    payload: GroupChallengeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupChallengeRead:
    return await create_group_challenge(group_id, payload, current_user, db)


@router.delete("/challenges/{challenge_id}", status_code=204)
async def delete_group_challenge_route(
    challenge_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_group_challenge(challenge_id, current_user.id, db)


@router.post("/{group_id}/activity", response_model=GroupActivityRead, status_code=201)
async def post_group_update(
    group_id: UUID,
    payload: GroupActivityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupActivityRead:
    return await create_group_update(group_id, payload.content, current_user, db)


@router.post(
    "/activity/{activity_id}/comments",
    response_model=GroupActivityCommentRead,
    status_code=201,
)
async def post_group_activity_comment(
    activity_id: UUID,
    payload: GroupActivityCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupActivityCommentRead:
    return await create_activity_comment(activity_id, payload.content, current_user, db)


@router.delete("/activity/comments/{comment_id}", status_code=204)
async def delete_group_activity_comment(
    comment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_activity_comment(comment_id, current_user.id, db)


@router.post(
    "/activity/{activity_id}/recognition",
    response_model=GroupActivityRead,
)
async def recognize_group_activity(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupActivityRead:
    return await react_to_activity(activity_id, current_user, db)


@router.delete("/activity/{activity_id}/recognition", status_code=204)
async def remove_group_activity_recognition(
    activity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await remove_activity_reaction(activity_id, current_user.id, db)


@router.put("/tasks/{task_id}", response_model=GroupTaskRead)
async def update_group_task_route(
    task_id: UUID,
    payload: GroupTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupTaskRead:
    return await update_group_task(task_id, payload, current_user, db)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_group_task_route(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_group_task(task_id, current_user.id, db)


@router.get("/{group_id}/milestones", response_model=list[GroupMilestoneRead])
async def read_group_milestones(
    group_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GroupMilestoneRead]:
    return await list_milestones(group_id, current_user.id, db)


@router.post("/{group_id}/milestones", response_model=GroupMilestoneRead, status_code=201)
async def create_group_milestone_route(
    group_id: UUID,
    payload: GroupMilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupMilestoneRead:
    return await create_milestone(group_id, payload, current_user.id, db)


@router.put("/milestones/{milestone_id}", response_model=GroupMilestoneRead)
async def update_group_milestone_route(
    milestone_id: UUID,
    payload: GroupMilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GroupMilestoneRead:
    return await update_milestone(milestone_id, payload, current_user.id, db)


@router.delete("/milestones/{milestone_id}", status_code=204)
async def delete_group_milestone_route(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await delete_milestone(milestone_id, current_user.id, db)
