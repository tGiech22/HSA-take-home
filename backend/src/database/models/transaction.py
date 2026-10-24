from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base
from src.enums import ExpenseCategory


class TransactionType(StrEnum):
    DEPOSIT = "DEPOSIT"
    PURCHASE = "PURCHASE"


class TransactionStatus(StrEnum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class DeclineReason(StrEnum):
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    INVALID_EXPENSE = "INVALID_EXPENSE"
    INACTIVE_CARD = "INACTIVE_CARD"
    EXPIRED_CARD = "EXPIRED_CARD"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="ck_transactions_positive_amount"),
        CheckConstraint(
            "(type = 'DEPOSIT' AND card_id IS NULL AND category IS NULL) OR "
            "(type = 'PURCHASE' AND card_id IS NOT NULL AND category IS NOT NULL)",
            name="ck_transactions_type_fields",
        ),
        CheckConstraint(
            "(status = 'APPROVED' AND decline_reason IS NULL AND "
            "((type = 'DEPOSIT' AND balance_change_cents = amount_cents) OR "
            "(type = 'PURCHASE' AND balance_change_cents = -amount_cents))) OR "
            "(status = 'DECLINED' AND type = 'PURCHASE' AND "
            "decline_reason IS NOT NULL AND balance_change_cents = 0)",
            name="ck_transactions_outcome",
        ),
        UniqueConstraint(
            "account_id", "idempotency_key", name="uq_transactions_account_idempotency"
        ),
        Index("ix_transactions_account_history", "account_id", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    card_id: Mapped[int | None] = mapped_column(ForeignKey("debit_cards.id"))
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    balance_change_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    category: Mapped[ExpenseCategory | None] = mapped_column(
        Enum(ExpenseCategory, name="expense_category")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type"), nullable=False
    )
    status: Mapped[TransactionStatus] = mapped_column(
        Enum(TransactionStatus, name="transaction_status"), nullable=False
    )
    decline_reason: Mapped[DeclineReason | None] = mapped_column(
        Enum(DeclineReason, name="decline_reason")
    )
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    request_hash: Mapped[str] = mapped_column(Text, nullable=False)
