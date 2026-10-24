from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from src.database.session import get_session
from src.schemas.account import AccountCreate, AccountResponse
from src.schemas.user import UserCreate, UserResponse
from src.services.account import UserNotFoundError, create_account
from src.services.user import DuplicateEmailError, create_user, list_users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserResponse])
def get_users(session: Annotated[Session, Depends(get_session)]):
    """List all users for manual inspection and testing through the OpenAPI docs."""
    return list_users(session)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(
    request: UserCreate,
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return create_user(session, name=request.name, email=request.email)
    except DuplicateEmailError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        ) from error


@router.post(
    "/{user_id}/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_account(
    user_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    request: AccountCreate,
    session: Annotated[Session, Depends(get_session)],
):
    try:
        return create_account(session, user_id=user_id)
    except UserNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        ) from error
