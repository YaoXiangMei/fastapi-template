"""分页依赖和响应模式。"""

from dataclasses import dataclass

from fastapi import Query
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PageParams:
    """分页查询参数。"""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_page_params(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
) -> PageParams:
    """分页的 FastAPI 依赖。"""
    return PageParams(page=page, page_size=page_size)


class PageData(BaseModel, Generic[T]):
    """分页数据负载，统一作为 ApiResponse 的 data 字段。

    用法：response_model=ApiResponse[PageData[UserRead]]
    """

    data: list[T]
    total: int
    page: int
    page_size: int
