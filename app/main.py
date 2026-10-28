from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import engine
from app.models import Base
from app.routers import books, ui
from app.services import LibraryError


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Creates missing tables; existing ones are left untouched.
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="Library API", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
app.include_router(books.router)
app.include_router(ui.router)


@app.exception_handler(LibraryError)
async def library_error_handler(_: Request, exc: LibraryError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
