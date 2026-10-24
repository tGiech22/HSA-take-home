from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    balance_cents: int
    created_at: datetime
