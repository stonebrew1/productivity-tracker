from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.gamification import GamificationDashboardRead
from app.services.gamification_service import gamification_dashboard


router = APIRouter(prefix="/gamification", tags=["gamification"])


@router.get("", response_model=GamificationDashboardRead)
async def read_gamification(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GamificationDashboardRead:
    return await gamification_dashboard(current_user.id, db)
