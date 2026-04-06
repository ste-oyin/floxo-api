import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.location import Location
from app.models.organization import Organization
from app.models.user import User
from app.schemas.responses import LocationResponse, OrganizationResponse, UserResponse

router = APIRouter()


class OnboardingResponse:
    pass


from pydantic import BaseModel


class OnboardingResult(BaseModel):
    user: UserResponse
    organization: OrganizationResponse
    locations: list[LocationResponse]


@router.post("/setup", response_model=OnboardingResult)
async def setup_workspace(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[dict[str, Any], Depends(get_current_user)],
):
    """Ensures the authenticated user has a user record, organization, and
    at least one default location. Idempotent -- safe to call on every login."""

    user_id = uuid.UUID(str(current_user["id"]))
    email = current_user.get("email", "")

    user_row = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user_row is None:
        user_row = User(id=user_id, email=email, role="user")
        db.add(user_row)
        await db.flush()

    org_result = await db.execute(
        select(Organization).where(Organization.owner_user_id == user_id).limit(1)
    )
    org = org_result.scalar_one_or_none()
    if org is None:
        org = Organization(name=f"{email.split('@')[0]}'s Workspace", owner_user_id=user_id)
        db.add(org)
        await db.flush()
        await db.refresh(org)

    loc_result = await db.execute(
        select(Location).where(Location.org_id == org.id).limit(1)
    )
    loc = loc_result.scalar_one_or_none()
    if loc is None:
        loc = Location(org_id=org.id, name="Default Store")
        db.add(loc)
        await db.flush()
        await db.refresh(loc)

    all_locs = (await db.execute(select(Location).where(Location.org_id == org.id))).scalars().all()

    await db.commit()
    await db.refresh(user_row)
    await db.refresh(org)

    return OnboardingResult(
        user=UserResponse.model_validate(user_row),
        organization=OrganizationResponse.model_validate(org),
        locations=[LocationResponse.model_validate(l) for l in all_locs],
    )
