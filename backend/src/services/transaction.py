from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Account, Transaction
from src.database.repositories.ledger import list_transactions
from src.services.deposit import AccountNotFoundError


def get_transaction_history(
    session: Session, *, user_id: int, account_id: int, limit: int = 100, offset: int = 0
) -> list[Transaction]:
    """Verify ownership before reading the account's ledger history."""
    if session.scalar(
        select(Account.id).where(Account.id == account_id, Account.user_id == user_id)
    ) is None:
        raise AccountNotFoundError
    return list_transactions(session, account_id=account_id, limit=limit, offset=offset)
