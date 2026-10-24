from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from src.database.session import get_session
from src.schemas.purchase import PurchaseCreate
from src.schemas.transaction import TransactionResponse
from src.services.card import CardNotFoundError
from src.services.deposit import AccountNotFoundError, IdempotencyConflictError
from src.services.purchase import create_purchase

router = APIRouter(prefix="/users/{user_id}/accounts/{account_id}/purchases", tags=["purchases"])


@router.post("", response_model=TransactionResponse, status_code=201,
             responses={200: {"model": TransactionResponse, "description": "Idempotent replay"}})
def purchase(
    user_id: int, account_id: int, request: PurchaseCreate, response: Response,
    session: Annotated[Session, Depends(get_session)],
    idempotency_key: Annotated[str, Header(min_length=1, max_length=255, pattern=r"\S")],
):
    """Process a purchase up to $1 trillion; approvals and business declines create ledger entries."""
    try:
        transaction, created = create_purchase(
            session, user_id=user_id, account_id=account_id,
            request=request, idempotency_key=idempotency_key,
        )
    except (AccountNotFoundError, CardNotFoundError) as error:
        raise HTTPException(status_code=404, detail="Account or card not found.") from error
    except IdempotencyConflictError as error:
        raise HTTPException(status_code=409,
                            detail="Idempotency key was already used for a different request.") from error
    if not created:
        response.status_code = 200
    return transaction
