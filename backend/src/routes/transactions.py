from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from src.database.session import get_session
from src.schemas.transaction import TransactionResponse
from src.services.deposit import AccountNotFoundError
from src.services.transaction import get_transaction_history

router = APIRouter(
    prefix="/users/{user_id}/accounts/{account_id}/transactions", tags=["transactions"]
)


@router.get("", response_model=list[TransactionResponse])
def transaction_history(
    user_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    account_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    session: Annotated[Session, Depends(get_session)],
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """List deposits and approved/declined purchases, newest first."""
    try:
        return get_transaction_history(
            session, user_id=user_id, account_id=account_id, limit=limit, offset=offset
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=404, detail="Account not found.") from error
