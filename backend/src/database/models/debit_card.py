from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database.base import Base


class CardStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DebitCard(Base):
    __tablename__ = "debit_cards"
    __table_args__ = (
        CheckConstraint(
            "last_four ~ '^[0-9]{4}$'", name="ck_debit_cards_last_four_digits"
        ),
        Index(
            "one_active_card_per_account",
            "account_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id"), nullable=False, index=True
    )
    last_four: Mapped[str] = mapped_column(String(4), nullable=False)
    expires_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus, name="card_status"), nullable=False
    )
    cardholder_name: Mapped[str] = mapped_column(Text, nullable=False)
