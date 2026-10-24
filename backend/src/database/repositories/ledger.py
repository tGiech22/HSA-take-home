"""Append and query ledger entries without committing or rolling back.

The caller must update the account balance and append its ledger entry in the
same database transaction. Database errors propagate to the caller.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import Transaction
from src.enums import DeclineReason, ExpenseCategory, TransactionStatus, TransactionType


def append_transaction(
    session: Session,
    *,
    account_id: int,
    card_id: int | None,
    amount_cents: int,
    balance_change_cents: int,
    category: ExpenseCategory | None,
    type: TransactionType,
    status: TransactionStatus,
    decline_reason: DeclineReason | None,
    idempotency_key: str,
    request_hash: str,
) -> Transaction:
    """Insert and flush an entry; persistence requires the caller to commit."""
    transaction = Transaction(
        account_id=account_id,
        card_id=card_id,
        amount_cents=amount_cents,
        balance_change_cents=balance_change_cents,
        category=category,
        type=type,
        status=status,
        decline_reason=decline_reason,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
    )
    session.add(transaction)
    session.flush()
    return transaction


def get_transaction(
    session: Session, *, account_id: int, transaction_id: int
) -> Transaction | None:
    """Return an entry only if it belongs to the supplied account."""
    return session.scalar(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.id == transaction_id,
        )
    )


def get_by_idempotency_key(
    session: Session, *, account_id: int, key: str
) -> Transaction | None:
    """Find a previous outcome; the caller must compare its request hash."""
    return session.scalar(
        select(Transaction).where(
            Transaction.account_id == account_id,
            Transaction.idempotency_key == key,
        )
    )


def list_transactions(
    session: Session, *, account_id: int, limit: int = 100, offset: int = 0
) -> list[Transaction]:
    """Return account history newest first, breaking timestamp ties by ID."""
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    if offset < 0:
        raise ValueError("offset must be nonnegative")
    return list(
        session.scalars(
            select(Transaction)
            .where(Transaction.account_id == account_id)
            .order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )


def sum_balance_changes(session: Session, *, account_id: int) -> int:
    """Return the ledger balance in cents, or zero when there are no entries."""
    total = session.execute(
        select(func.coalesce(func.sum(Transaction.balance_change_cents), 0)).where(
            Transaction.account_id == account_id
        )
    ).scalar_one()
    return int(total)
