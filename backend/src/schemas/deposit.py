from pydantic import BaseModel, ConfigDict, Field


MAX_DEPOSIT_CENTS = 100_000_000_000_000


class DepositCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount_cents: int = Field(strict=True, gt=0, le=MAX_DEPOSIT_CENTS)
