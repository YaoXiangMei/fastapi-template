"""统一 API 响应封装。

所有 API 响应遵循以下结构：

    {
        "status": 0,
        "message": "success",
        "data": <实际数据或 null>
    }

错误响应遵循相同结构，但 status 为非零值。
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应模型。"""

    status: int = 0
    message: str = "success"
    data: T | None = None


class PageData(BaseModel, Generic[T]):
    """分页数据负载。"""

    items: list[T]
    total: int
    page: int
    page_size: int


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构建成功响应字典。"""
    return {"status": 0, "message": message, "data": data}


def error(status: int, message: str, data: Any = None) -> dict[str, Any]:
    """构建错误响应字典。"""
    return {"status": status, "message": message, "data": data}
