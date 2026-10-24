from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from src.enums import CardStatus


class CardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cardholder_name: str = Field(strict=True, min_length=1, pattern=r"\S")


class CardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    last_four: str
    expires_on: date
    created_at: datetime
    status: CardStatus
    cardholder_name: str
