"""请求 ID 和访问日志中间件。"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger


class RequestIDMiddleware(BaseHTTPMiddleware):
    """注入请求 ID 请求头并将其绑定到日志上下文。"""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        with logger.contextualize(request_id=request_id):
            logger.info(
                "{} {} from {}",
                request.method,
                request.url.path,
                request.client.host if request.client else "unknown",
            )

            response = await call_next(request)

            elapsed_ms = round(time.perf_counter() * 1000)
            logger.info(
                "{} {} completed {} in {}ms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response
