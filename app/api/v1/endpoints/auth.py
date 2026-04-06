import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.responses import AuthVerifyResponse, UserResponse

router = APIRouter()


@router.post("/verify", response_model=AuthVerifyResponse, status_code=status.HTTP_200_OK)
async def verify_token(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[dict, Depends(get_current_user)],
):
    try:
        user_id = uuid.UUID(str(user["id"]))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user id in token",
        ) from exc
    result = await db.execute(select(User).where(User.id == user_id))
    row = result.scalar_one_or_none()
    if row is None:
        row = User(id=user_id, email=user["email"], role=str(user.get("role", "user")))
        db.add(row)
    else:
        row.email = user["email"]
        if user.get("role") is not None:
            row.role = str(user["role"])
    await db.commit()
    await db.refresh(row)
    return AuthVerifyResponse(user=UserResponse.model_validate(row))
