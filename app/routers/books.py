from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

from app import services
from app.database import get_session
from app.schemas import BookCreate, BookRead, StatusUpdate

router = APIRouter(prefix="/books", tags=["books"])

SessionDep = Annotated[Session, Depends(get_session)]
SerialNumber = Annotated[str, Path(pattern=r"^[0-9]{6}$")]


@router.get("", response_model=list[BookRead])
def list_books(session: SessionDep):
    return services.list_books(session)


@router.post("", response_model=BookRead, status_code=201)
def create_book(data: BookCreate, session: SessionDep):
    return services.create_book(session, data)


@router.delete("/{serial_number}", status_code=204)
def delete_book(serial_number: SerialNumber, session: SessionDep) -> None:
    services.delete_book(session, serial_number)


@router.put("/{serial_number}/status", response_model=BookRead)
def update_status(serial_number: SerialNumber, update: StatusUpdate, session: SessionDep):
    """Mark a book as borrowed (with the borrower's card number) or as available again."""
    return services.update_status(session, serial_number, update)
