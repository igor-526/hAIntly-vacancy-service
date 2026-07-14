from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from api.dictionaries import router as dictionaries_router
from core.exceptions import AppError
from settings import settings
from utils.configure_sentry import configure_sentry
from utils.database import close_database
from utils.seeding import seed_dictionary_sync_states

configure_sentry()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        await seed_dictionary_sync_states()
        yield
    finally:
        await close_database()


app = FastAPI(title=settings.app_title, debug=settings.debug, lifespan=lifespan)
app.include_router(dictionaries_router)


@app.get("/health", tags=["Health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": exc.errors()})
