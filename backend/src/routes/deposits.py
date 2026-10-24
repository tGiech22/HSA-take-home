from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, HTTPException, Response, status
from sqlalchemy.orm import Session

from src.database.session import get_session
from src.schemas.deposit import DepositCreate
from src.schemas.transaction import TransactionResponse
from src.services.deposit import (
    AccountNotFoundError,
    BalanceLimitError,
    IdempotencyConflictError,
    create_deposit,
)

router = APIRouter(prefix="/users/{user_id}/accounts/{account_id}/deposits", tags=["deposits"])


@router.post(
    "",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"model": TransactionResponse, "description": "Idempotent replay"}},
)
def deposit(
    user_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    account_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    request: DepositCreate,
    response: Response,
    session: Annotated[Session, Depends(get_session)],
    idempotency_key: Annotated[
        str, Header(min_length=1, max_length=255, pattern=r"\S")
    ],
):
    """Deposit up to $1 trillion; retries with the same key return the original entry."""
    try:
        transaction, created = create_deposit(
            session,
            user_id=user_id,
            account_id=account_id,
            amount_cents=request.amount_cents,
            idempotency_key=idempotency_key,
        )
    except AccountNotFoundError as error:
        raise HTTPException(status_code=404, detail="Account not found.") from error
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=409, detail="Idempotency key was already used for a different request."
        ) from error
    except BalanceLimitError as error:
        raise HTTPException(
            status_code=409, detail="Deposit would exceed the maximum account balance."
        ) from error
    if not created:
        response.status_code = status.HTTP_200_OK
    return transaction
