"""The standard error shape (spec 06 section 5): `{"error": {"code", "message", "details"}}`."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tts.store.repositories import NotFoundError, NotPublishableError


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str) -> ApiError:
    return ApiError(404, "not_found", what)


def _response(status: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, error: ApiError) -> JSONResponse:
        return _response(error.status, error.code, error.message, error.details)

    @app.exception_handler(NotFoundError)
    async def _missing(_: Request, error: NotFoundError) -> JSONResponse:
        return _response(404, "not_found", str(error.args[0]))

    @app.exception_handler(NotPublishableError)
    async def _not_publishable(_: Request, error: NotPublishableError) -> JSONResponse:
        return _response(409, "not_publishable", str(error))

    @app.exception_handler(RequestValidationError)
    async def _invalid(_: Request, error: RequestValidationError) -> JSONResponse:
        details = [
            {"where": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
            for e in error.errors()
        ]
        return _response(422, "validation_error", "the request is not valid", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, error: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed"}.get(error.status_code, "http_error")
        return _response(error.status_code, code, str(error.detail))
