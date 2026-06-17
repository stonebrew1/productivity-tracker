import asyncio
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.schemas.task import TaskUpdate
from app.services.task_service import validate_task_links


class EmptySession:
    async def get(self, _model: object, _identity: object) -> None:
        return None


def test_task_cannot_be_its_own_parent() -> None:
    task_id = uuid4()
    user = User(id=uuid4(), email="user@example.com", password_hash="unused")

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            validate_task_links(
                TaskUpdate(parent_id=task_id),
                user,
                EmptySession(),
                task_id,
            )
        )

    assert error.value.status_code == 400
    assert error.value.detail == "A task cannot be its own parent."
