import hashlib
import json

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database.models import Account, Transaction
from src.database.repositories.ledger import append_transaction, get_by_idempotency_key
from src.enums import TransactionStatus, TransactionType
from src.schemas.deposit import MAX_DEPOSIT_CENTS

MAX_BALANCE_CENTS = 9_223_372_036_854_775_807


class AccountNotFoundError(Exception):
    pass


class IdempotencyConflictError(Exception):
    pass


class BalanceLimitError(Exception):
    pass


def _verify_account(session: Session, user_id: int, account_id: int) -> None:
    if session.scalar(
        select(Account.id).where(Account.id == account_id, Account.user_id == user_id)
    ) is None:
        raise AccountNotFoundError


def _verify_hash(transaction: Transaction, request_hash: str) -> None:
    if transaction.request_hash != request_hash:
        raise IdempotencyConflictError


def create_deposit(
    session: Session,
    *,
    user_id: int,
    account_id: int,
    amount_cents: int,
    idempotency_key: str,
) -> tuple[Transaction, bool]:
    """Return the entry and whether it was created; commit balance and ledger together."""
    if type(amount_cents) is not int or not 0 < amount_cents <= MAX_DEPOSIT_CENTS:
        raise ValueError("Deposit amount must be positive and at most $1 trillion.")
    if not idempotency_key.strip():
        raise ValueError("An idempotency key is required.")
    request_hash = hashlib.sha256(
        json.dumps(
            {"type": "DEPOSIT", "account_id": account_id, "amount_cents": amount_cents},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()
    try:
        with session.begin():
            _verify_account(session, user_id, account_id)
            existing = get_by_idempotency_key(
                session, account_id=account_id, key=idempotency_key
            )
            if existing is not None:
                _verify_hash(existing, request_hash)
                return existing, False

            updated_id = session.scalar(
                update(Account)
                .where(
                    Account.id == account_id,
                    Account.user_id == user_id,
                    Account.balance_cents <= MAX_BALANCE_CENTS - amount_cents,
                )
                .values(balance_cents=Account.balance_cents + amount_cents)
                .returning(Account.id)
            )
            if updated_id is None:
                _verify_account(session, user_id, account_id)
                raise BalanceLimitError
            transaction = append_transaction(
                session,
                account_id=account_id,
                card_id=None,
                amount_cents=amount_cents,
                balance_change_cents=amount_cents,
                category=None,
                type=TransactionType.DEPOSIT,
                status=TransactionStatus.APPROVED,
                decline_reason=None,
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )
        return transaction, True
    except IntegrityError as error:
        # The failed transaction has rolled back, including its balance increase.
        if not (
            getattr(error.orig, "sqlstate", None) == "23505"
            and getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            == "uq_transactions_account_idempotency"
        ):
            raise
        with session.begin():
            _verify_account(session, user_id, account_id)
            existing = get_by_idempotency_key(
                session, account_id=account_id, key=idempotency_key
            )
            if existing is None:
                raise
            _verify_hash(existing, request_hash)
        return existing, False
