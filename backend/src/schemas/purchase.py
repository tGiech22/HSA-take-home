from pydantic import BaseModel, ConfigDict, Field

from src.enums import ExpenseCategory

MAX_PURCHASE_CENTS = 100_000_000_000_000


class PurchaseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: int = Field(strict=True, gt=0, le=2_147_483_647)
    amount_cents: int = Field(strict=True, gt=0, le=MAX_PURCHASE_CENTS)
    category: ExpenseCategory
