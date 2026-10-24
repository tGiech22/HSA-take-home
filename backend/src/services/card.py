import calendar
import secrets
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.database.models import Account, DebitCard
from src.enums import CardStatus
from src.services.deposit import AccountNotFoundError


class CardNotFoundError(Exception):
    pass


class ActiveCardExistsError(Exception):
    pass


def lock_account(session: Session, *, user_id: int, account_id: int) -> None:
    """Card operations and purchases acquire the account lock before card locks."""
    if session.scalar(
        select(Account.id)
        .where(Account.id == account_id, Account.user_id == user_id)
        .with_for_update()
    ) is None:
        raise AccountNotFoundError


def deactivate_expired_cards(session: Session, account_id: int, today: date) -> None:
    session.execute(
        update(DebitCard)
        .where(
            DebitCard.account_id == account_id,
            DebitCard.status == CardStatus.ACTIVE,
            DebitCard.expires_on < today,
        )
        .values(status=CardStatus.INACTIVE)
    )


def issue_card(
    session: Session, *, user_id: int, account_id: int, cardholder_name: str
) -> DebitCard:
    with session.begin():
        lock_account(session, user_id=user_id, account_id=account_id)
        today = datetime.now(timezone.utc).date()
        deactivate_expired_cards(session, account_id, today)
        if session.scalar(select(DebitCard.id).where(
            DebitCard.account_id == account_id, DebitCard.status == CardStatus.ACTIVE
        )) is not None:
            raise ActiveCardExistsError
        year = today.year + 3
        expires_on = date(year, today.month, calendar.monthrange(year, today.month)[1])
        card = DebitCard(
            account_id=account_id,
            last_four=f"{secrets.randbelow(10000):04d}",
            expires_on=expires_on,
            status=CardStatus.ACTIVE,
            cardholder_name=cardholder_name,
        )
        session.add(card)
        session.flush()
    return card


def deactivate_card(
    session: Session, *, user_id: int, account_id: int, card_id: int
) -> DebitCard:
    with session.begin():
        lock_account(session, user_id=user_id, account_id=account_id)
        card = session.scalar(select(DebitCard).where(
            DebitCard.id == card_id, DebitCard.account_id == account_id
        ).with_for_update())
        if card is None:
            raise CardNotFoundError
        card.status = CardStatus.INACTIVE
        session.flush()
    return card
