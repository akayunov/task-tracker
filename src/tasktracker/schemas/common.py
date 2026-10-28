import math
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar('T')


class Page(BaseModel, Generic[T]):
    """Страница коллекции."""

    model_config = ConfigDict(extra='forbid')

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def paginate(items: list[T], total: int, page: int, page_size: int) -> Page[T]:
    """Собрать страницу из уже отрезанного списка и общего числа строк.

    :param items: элементы текущей страницы
    :param total: число строк без учёта limit
    :param page: номер страницы, с 1
    :param page_size: размер страницы
    :return: страница с числом страниц
    """
    pages = math.ceil(total / page_size) if total else 0
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
