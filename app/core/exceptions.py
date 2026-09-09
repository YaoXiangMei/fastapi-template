"""应用异常层级与统一异常处理器。"""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.response import error


class AppException(Exception):  # noqa: N818
    """应用异常基类，携带 message、HTTP 状态码和可选 data。

    业务失败时响应体的 status 恒为 0，具体错误类型由 HTTP 状态码区分。
    """

    def __init__(
        self,
        message: str = "Internal error",
        status_code: int = 500,
        data: Any = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class UnauthorizedException(AppException):
    def __init__(self, message: str = "Not authenticated") -> None:
        super().__init__(message=message, status_code=401)


class ForbiddenException(AppException):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message=message, status_code=403)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, status_code=404)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message=message, status_code=409)


class BadRequestException(AppException):
    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message=message, status_code=400)


class RateLimitException(AppException):
    def __init__(self, message: str = "Too many requests") -> None:
        super().__init__(message=message, status_code=429)


def register_exception_handlers(app: FastAPI) -> None:
    """在 FastAPI 应用上注册所有统一异常处理器。"""

    @app.exception_handler(AppException)
    async def handle_app_exception(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error(exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error("Validation error", exc.errors()),
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(_: Request, exc: IntegrityError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=error("Data integrity conflict"),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error("Internal server error"),
        )
