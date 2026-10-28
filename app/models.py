from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class BookStatus(StrEnum):
    AVAILABLE = "available"
    BORROWED = "borrowed"


class Book(Base):
    __tablename__ = "books"
    __table_args__ = (
        CheckConstraint("serial_number ~ '^[0-9]{6}$'"),
        CheckConstraint("borrower_card_number ~ '^[0-9]{6}$'"),
        # A book is either fully borrowed (who + when) or fully available.
        CheckConstraint("(borrower_card_number IS NULL) = (borrowed_at IS NULL)"),
    )

    # Stored as text so that leading zeros ("000123") are preserved.
    serial_number: Mapped[str] = mapped_column(String(6), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    author: Mapped[str] = mapped_column(String(255))
    borrower_card_number: Mapped[str | None] = mapped_column(String(6))
    borrowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    @property
    def status(self) -> BookStatus:
        return BookStatus.BORROWED if self.borrower_card_number else BookStatus.AVAILABLE
