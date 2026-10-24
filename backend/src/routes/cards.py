from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session

from src.database.session import get_session
from src.schemas.card import CardCreate, CardResponse
from src.services.card import ActiveCardExistsError, CardNotFoundError, deactivate_card, issue_card, list_cards
from src.services.deposit import AccountNotFoundError

router = APIRouter(prefix="/users/{user_id}/accounts/{account_id}/cards", tags=["cards"])


@router.get("", response_model=list[CardResponse])
def get_cards(
    user_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    account_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    session: Annotated[Session, Depends(get_session)],
):
    """List active, inactive, and expired cards for the selected user's account."""
    try:
        return list_cards(session, user_id=user_id, account_id=account_id)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=404, detail="Account not found.") from error


@router.post("", response_model=CardResponse, status_code=201)
def create_card(
    user_id: Annotated[int, Path(gt=0, le=2_147_483_647)], account_id: Annotated[int, Path(gt=0, le=2_147_483_647)], request: CardCreate,
    session: Annotated[Session, Depends(get_session)],
):
    """Issue a simulated card, automatically deactivating expired cards first."""
    try:
        return issue_card(session, user_id=user_id, account_id=account_id,
                          cardholder_name=request.cardholder_name)
    except AccountNotFoundError as error:
        raise HTTPException(status_code=404, detail="Account not found.") from error
    except ActiveCardExistsError as error:
        raise HTTPException(status_code=409, detail="Account already has an active card.") from error


@router.post("/{card_id}/deactivate", response_model=CardResponse)
def make_card_inactive(
    user_id: Annotated[int, Path(gt=0, le=2_147_483_647)], account_id: Annotated[int, Path(gt=0, le=2_147_483_647)], card_id: Annotated[int, Path(gt=0, le=2_147_483_647)],
    session: Annotated[Session, Depends(get_session)],
):
    """Deactivate a card, including one that has not expired. Repeats are harmless."""
    try:
        return deactivate_card(session, user_id=user_id, account_id=account_id, card_id=card_id)
    except (AccountNotFoundError, CardNotFoundError) as error:
        raise HTTPException(status_code=404, detail="Account or card not found.") from error
