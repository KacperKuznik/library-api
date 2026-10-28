"""Server-rendered web UI for library staff, built on Jinja2 templates.

Plain HTML forms only support GET and POST, so state changes are POST endpoints that
redirect back to the list (POST/redirect/GET). Validation and business errors re-render
the page with a message instead of returning JSON.
"""

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Form, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app import services
from app.models import BookStatus
from app.routers.books import SerialNumber, SessionDep
from app.schemas import BookCreate, BorrowBook, ReturnBook

router = APIRouter(include_in_schema=False)

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")
# Time zone used to display dates (the API always returns UTC).
DISPLAY_TZ = ZoneInfo(os.environ.get("DISPLAY_TIMEZONE", "Europe/Warsaw"))


def _local_time(value: datetime) -> str:
    return value.astimezone(DISPLAY_TZ).strftime("%d.%m.%Y %H:%M")


templates.env.filters["local_time"] = _local_time

FIELD_ERRORS = {
    "serial_number": "Numer seryjny musi składać się z dokładnie 6 cyfr.",
    "title": "Tytuł jest wymagany i może mieć maksymalnie 255 znaków.",
    "author": "Autor jest wymagany i może mieć maksymalnie 255 znaków.",
    "borrower_card_number": "Numer karty bibliotecznej musi składać się z dokładnie 6 cyfr.",
}

FormStr = Annotated[str, Form()]


def _validation_message(exc: ValidationError) -> str:
    messages = (FIELD_ERRORS.get(str(error["loc"][-1]), error["msg"]) for error in exc.errors())
    return " ".join(dict.fromkeys(messages))


def _parse_view(view: str) -> BookStatus | None:
    return BookStatus(view) if view in BookStatus else None


def _render(
    request: Request,
    session: Session,
    *,
    view: BookStatus | None,
    notice: str | None = None,
    error: str | None = None,
    form: dict[str, str] | None = None,
    status_code: int = status.HTTP_200_OK,
) -> HTMLResponse:
    all_books = services.list_books(session)
    context: dict[str, Any] = {
        "books": [book for book in all_books if view is None or book.status is view],
        "counts": {
            None: len(all_books),
            **{s: sum(book.status is s for book in all_books) for s in BookStatus},
        },
        "view": view,
        "notice": notice,
        "error": error,
        "form": form or {},
    }
    return templates.TemplateResponse(request, "books.html", context, status_code=status_code)


def _redirect(view: BookStatus | None, notice: str) -> RedirectResponse:
    params = {"notice": notice} | ({"status": view.value} if view else {})
    return RedirectResponse(f"/?{urlencode(params)}", status_code=status.HTTP_303_SEE_OTHER)


def _perform(
    request: Request,
    session: Session,
    view: BookStatus | None,
    action: Callable[[], object],
    *,
    success: str,
    conflict: str,
) -> Response:
    try:
        action()
    except services.LibraryError as exc:
        error = "Nie znaleziono książki." if exc.status_code == 404 else conflict
        return _render(request, session, view=view, error=error, status_code=exc.status_code)
    return _redirect(view, success)


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    session: SessionDep,
    book_status: Annotated[BookStatus | None, Query(alias="status")] = None,
    notice: Annotated[str | None, Query(max_length=300)] = None,
) -> HTMLResponse:
    return _render(request, session, view=book_status, notice=notice)


@router.post("/ui/books")
def create_book(
    request: Request,
    session: SessionDep,
    serial_number: FormStr = "",
    title: FormStr = "",
    author: FormStr = "",
    view: FormStr = "",
) -> Response:
    current_view = _parse_view(view)
    form = {"serial_number": serial_number, "title": title, "author": author}
    try:
        data = BookCreate(serial_number=serial_number.strip(), title=title, author=author)
    except ValidationError as exc:
        return _render(
            request, session, view=current_view, error=_validation_message(exc), form=form,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    try:
        services.create_book(session, data)
    except services.LibraryError as exc:
        return _render(
            request, session, view=current_view, form=form,
            error=f"Książka o numerze seryjnym {data.serial_number} już istnieje.",
            status_code=exc.status_code,
        )
    return _redirect(current_view, f"Dodano książkę „{data.title}” ({data.serial_number}).")


@router.post("/ui/books/{serial_number}/borrow")
def borrow_book(
    request: Request,
    session: SessionDep,
    serial_number: SerialNumber,
    borrower_card_number: FormStr = "",
    view: FormStr = "",
) -> Response:
    current_view = _parse_view(view)
    try:
        update = BorrowBook(
            status=BookStatus.BORROWED, borrower_card_number=borrower_card_number.strip()
        )
    except ValidationError as exc:
        return _render(
            request, session, view=current_view, error=_validation_message(exc),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )
    return _perform(
        request, session, current_view,
        lambda: services.update_status(session, serial_number, update),
        success=(
            f"Książka {serial_number} wypożyczona na kartę {update.borrower_card_number}."
        ),
        conflict=f"Książka {serial_number} jest już wypożyczona.",
    )


@router.post("/ui/books/{serial_number}/return")
def return_book(
    request: Request, session: SessionDep, serial_number: SerialNumber, view: FormStr = ""
) -> Response:
    current_view = _parse_view(view)
    return _perform(
        request, session, current_view,
        lambda: services.update_status(
            session, serial_number, ReturnBook(status=BookStatus.AVAILABLE)
        ),
        success=f"Zarejestrowano zwrot książki {serial_number}.",
        conflict=f"Książka {serial_number} nie jest wypożyczona.",
    )


@router.post("/ui/books/{serial_number}/delete")
def delete_book(
    request: Request, session: SessionDep, serial_number: SerialNumber, view: FormStr = ""
) -> Response:
    current_view = _parse_view(view)
    return _perform(
        request, session, current_view,
        lambda: services.delete_book(session, serial_number),
        success=f"Usunięto książkę {serial_number}.",
        conflict=(
            f"Książka {serial_number} jest wypożyczona — zarejestruj zwrot przed usunięciem."
        ),
    )
