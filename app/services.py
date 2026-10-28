from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Book, BookStatus
from app.schemas import BookCreate, BorrowBook, StatusUpdate


class LibraryError(Exception):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def list_books(session: Session) -> list[Book]:
    return list(session.scalars(select(Book).order_by(Book.serial_number)))


def _get_locked(session: Session, serial_number: str) -> Book:
    # Row lock prevents two concurrent requests from changing the same book.
    book = session.get(Book, serial_number, with_for_update=True)
    if book is None:
        raise LibraryError(404, f"Book {serial_number} not found")
    return book


def create_book(session: Session, data: BookCreate) -> Book:
    book = Book(**data.model_dump())
    session.add(book)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise LibraryError(409, f"Book {data.serial_number} already exists") from None
    return book


def delete_book(session: Session, serial_number: str) -> None:
    book = _get_locked(session, serial_number)
    if book.status is BookStatus.BORROWED:
        raise LibraryError(409, f"Book {serial_number} is borrowed, return it before removing")
    session.delete(book)
    session.commit()


def update_status(session: Session, serial_number: str, update: StatusUpdate) -> Book:
    book = _get_locked(session, serial_number)
    if isinstance(update, BorrowBook):
        if book.status is BookStatus.BORROWED:
            raise LibraryError(409, f"Book {serial_number} is already borrowed")
        book.borrower_card_number = update.borrower_card_number
        book.borrowed_at = datetime.now(UTC)
    else:
        if book.status is BookStatus.AVAILABLE:
            raise LibraryError(409, f"Book {serial_number} is not borrowed")
        book.borrower_card_number = None
        book.borrowed_at = None
    session.commit()
    return book
