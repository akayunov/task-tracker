"""Реестр созданных e2e-ресурсов для очистки по HTTP после теста."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from typing import Any, Protocol


class Cleanable(Protocol):
    def delete(
        self,
        *,
        status_code: int = HTTPStatus.NO_CONTENT,
        expected_headers: dict[str, Any] | None = None,
        expected_body: dict[str, Any] | None = None,
    ) -> object: ...


_registry: list[Cleanable] = []


def track(resource: Cleanable) -> None:
    """Запомнить ресурс для удаления в конце теста.

    :param resource: объект с методом delete()
    """
    _registry.append(resource)


def untrack(resource: Cleanable) -> None:
    """Убрать ресурс из реестра после явного delete() в тесте.

    :param resource: ранее зарегистрированный объект
    """
    while resource in _registry:
        _registry.remove(resource)


def untrack_matching(predicate: Callable[[Cleanable], bool]) -> None:
    """Снять с очистки все ресурсы, для которых predicate истинен.

    :param predicate: условие снятия (например комментарии удалённой задачи)
    """
    kept = [resource for resource in _registry if not predicate(resource)]
    _registry.clear()
    _registry.extend(kept)


def cleanup_tracked() -> None:
    """Удалить всё созданное в обратном порядке; ошибки очистки не глотаем молча."""
    errors: list[str] = []
    while _registry:
        resource = _registry.pop()
        try:
            resource.delete()
        except Exception as error:  # noqa: BLE001 — собираем все сбои очистки
            errors.append(f'{type(resource).__name__}: {error}')
    if errors:
        raise AssertionError('e2e cleanup failed:\n' + '\n'.join(errors))
