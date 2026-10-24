import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from src.database.models import Account, DebitCard, Transaction
from src.database.repositories.ledger import append_transaction, get_by_idempotency_key
from src.enums import CardStatus, DeclineReason, ExpenseCategory, TransactionStatus, TransactionType
from src.schemas.purchase import PurchaseCreate
from src.services.card import CardNotFoundError, deactivate_expired_cards, lock_account
from src.services.deposit import IdempotencyConflictError

QUALIFIED_CATEGORIES = frozenset({
    ExpenseCategory.DOCTOR_VISIT, ExpenseCategory.PHARMACY, ExpenseCategory.HOSPITAL,
    ExpenseCategory.PRESCRIPTION, ExpenseCategory.DENTAL, ExpenseCategory.VISION,
    ExpenseCategory.OTC_MEDICINE, ExpenseCategory.PREVENTATIVE_CARE,
})


def create_purchase(
    session: Session, *, user_id: int, account_id: int,
    request: PurchaseCreate, idempotency_key: str,
) -> tuple[Transaction, bool]:
    if not idempotency_key.strip():
        raise ValueError("An idempotency key is required.")
    request_hash = hashlib.sha256(json.dumps(
        {"type": "PURCHASE", "account_id": account_id, **request.model_dump(mode="json")},
        sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    with session.begin():
        # Serialize account operations, including card changes and duplicate purchases.
        lock_account(session, user_id=user_id, account_id=account_id)
        today = datetime.now(timezone.utc).date()
        deactivate_expired_cards(session, account_id, today)
        existing = get_by_idempotency_key(session, account_id=account_id, key=idempotency_key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise IdempotencyConflictError
            return existing, False
        card = session.scalar(select(DebitCard).where(
            DebitCard.id == request.card_id, DebitCard.account_id == account_id
        ).with_for_update())
        if card is None:
            raise CardNotFoundError
        reason = None
        if card.expires_on < today:
            reason = DeclineReason.EXPIRED_CARD
        elif card.status != CardStatus.ACTIVE:
            reason = DeclineReason.INACTIVE_CARD
        elif request.category not in QUALIFIED_CATEGORIES:
            reason = DeclineReason.INVALID_EXPENSE
        else:
            updated = session.scalar(update(Account).where(
                Account.id == account_id,
                Account.balance_cents >= request.amount_cents,
            ).values(balance_cents=Account.balance_cents - request.amount_cents)
              .returning(Account.id))
            if updated is None:
                reason = DeclineReason.INSUFFICIENT_FUNDS
        transaction = append_transaction(
            session, account_id=account_id, card_id=card.id,
            amount_cents=request.amount_cents,
            balance_change_cents=0 if reason else -request.amount_cents,
            category=request.category, type=TransactionType.PURCHASE,
            status=TransactionStatus.DECLINED if reason else TransactionStatus.APPROVED,
            decline_reason=reason, idempotency_key=idempotency_key, request_hash=request_hash,
        )
    return transaction, True
