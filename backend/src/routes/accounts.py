from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.database.session import get_session
from src.schemas.account import AccountResponse
from src.services.account import list_accounts

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("", response_model=list[AccountResponse])
def get_accounts(session: Annotated[Session, Depends(get_session)]):
    """List all accounts for manual inspection and testing through the OpenAPI docs."""
    return list_accounts(session)
