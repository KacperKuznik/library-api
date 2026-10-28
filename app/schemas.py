from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.models import BookStatus

# [0-9] rather than \d: the latter also matches non-ASCII digits such as "١٢٣٤٥٦".
SixDigits = Annotated[str, StringConstraints(pattern=r"^[0-9]{6}$")]
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class BookCreate(BaseModel):
    serial_number: SixDigits
    title: Text
    author: Text


class BookRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    serial_number: str
    title: str
    author: str
    status: BookStatus
    borrower_card_number: str | None
    borrowed_at: datetime | None


class BorrowBook(BaseModel):
    status: Literal[BookStatus.BORROWED]
    borrower_card_number: SixDigits


class ReturnBook(BaseModel):
    status: Literal[BookStatus.AVAILABLE]


StatusUpdate = Annotated[BorrowBook | ReturnBook, Field(discriminator="status")]
