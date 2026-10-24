from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.enums import DeclineReason, ExpenseCategory, TransactionStatus, TransactionType


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    card_id: int | None
    amount_cents: int
    balance_change_cents: int
    category: ExpenseCategory | None
    created_at: datetime
    type: TransactionType
    status: TransactionStatus
    decline_reason: DeclineReason | None
    idempotency_key: str
