from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupInvitationRead,
    GroupInvite,
    GroupJoin,
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
