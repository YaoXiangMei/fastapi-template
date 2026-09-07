"""统一 API 响应封装。

所有 API 响应遵循以下结构：

    {
        "status": 1,            # 1=成功，0=失败
        "message": "success",
        "data": <实际数据或 null>
    }

错误响应遵循相同结构，status 固定为 0（具体错误类型由 HTTP 状态码区分）。

分页接口的 data 字段使用 app.core.pagination.PageData，其结构为：

    {
        "data": [...],   # 当前页数据列表
        "total": 100,
        "page": 1,
        "page_size": 20
    }
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """统一响应模型。status=1 表示成功，status=0 表示失败。"""

    status: int = 1
    message: str = "success"
    data: T | None = None


def success(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构建成功响应字典。"""
    return {"status": 1, "message": message, "data": data}


def error(message: str, data: Any = None) -> dict[str, Any]:
    """构建失败响应字典。失败时 status 恒为 0。"""
    return {"status": 0, "message": message, "data": data}
