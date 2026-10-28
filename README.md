# Library API

A simple API for library staff to track the book collection: add and remove books, list
them, and mark them as borrowed or available. A small server-rendered web UI is included.

**Stack:** Python 3.13, FastAPI, Jinja2, SQLAlchemy 2, PostgreSQL 17, pytest, uv, Docker Compose.

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`; the Docker image
installs them with `uv sync --locked`. After changing dependencies, run `uv lock` (or
`uv add <package>`) to update the lock file.

## Running

```bash
docker compose up --build
```

- Web UI: http://localhost:8000
- API docs (Swagger UI): http://localhost:8000/docs

The database table is created automatically when the app starts.

## Tests

The tests run against a separate, throwaway in-memory PostgreSQL container, so they never
touch the application's data:

```bash
docker compose --profile test run --rm tests
```

## API

| Method   | Path                            | Description                            |
|----------|---------------------------------|----------------------------------------|
| `GET`    | `/books`                        | List all books                         |
| `POST`   | `/books`                        | Add a book                             |
| `DELETE` | `/books/{serial_number}`        | Remove a book                          |
| `PUT`    | `/books/{serial_number}/status` | Change the state: borrowed / available |

```bash
# Add a book
curl -X POST localhost:8000/books -H "Content-Type: application/json" \
  -d '{"serial_number": "004217", "title": "Lalka", "author": "Bolesław Prus"}'

# Borrow
curl -X PUT localhost:8000/books/004217/status -H "Content-Type: application/json" \
  -d '{"status": "borrowed", "borrower_card_number": "123456"}'

# Return
curl -X PUT localhost:8000/books/004217/status -H "Content-Type: application/json" \
  -d '{"status": "available"}'
```

Example book:

```json
{
  "serial_number": "004217",
  "title": "Lalka",
  "author": "Bolesław Prus",
  "status": "borrowed",
  "borrower_card_number": "123456",
  "borrowed_at": "2026-10-28T17:12:03.512Z"
}
```

## Design decisions

- **The serial number is the primary key, stored as text.** It is unique and entered by
  staff, so no extra ID is needed, and text keeps leading zeros (`000123`).
- **Data is validated twice:** by the API (`422` for anything other than six digits) and by
  `CHECK` constraints in the database.
- **The status is derived from the data:** a book is borrowed when it has a borrower card
  number. A database constraint keeps the card number and borrow date set together.
- **Invalid transitions are rejected with `409`:** borrowing a borrowed book, returning an
  available one, or removing a borrowed one (so it's never lost who holds the copy).
- **Concurrent changes are safe:** updates lock the book's row (`SELECT ... FOR UPDATE`), so
  the same copy can't be lent to two people at once.

## Web UI

The `/` page (Jinja2 templates, no JavaScript apart from the delete confirmation) lets staff:

- add a book,
- browse the list filtered by all / available / borrowed (with counts),
- borrow a book (by entering a library card number) and register its return,
- remove a book (the button is disabled for borrowed books).

HTML forms only support `GET` and `POST`, so the UI has its own `POST /ui/...` routes that
follow the POST/redirect/GET pattern. They use the same business logic (`services.py`) and the
same validation schemas as the API. Errors (e.g. a malformed number or a duplicate) are shown on
the page, and the values typed into the add form are kept. Dates are displayed in the
`Europe/Warsaw` time zone (configurable with `DISPLAY_TIMEZONE`); the API always returns UTC.
The UI text is in Polish.

## Project structure

```
app/
  main.py              # FastAPI app, table creation, error handling
  database.py          # database connection
  models.py            # Book table
  schemas.py           # request/response validation
  services.py          # business logic
  routers/books.py     # JSON API
  routers/ui.py        # web UI (forms)
  templates/           # Jinja2 templates
  static/              # CSS
tests/                 # API tests
pyproject.toml         # dependencies
uv.lock                # pinned dependency versions
```
