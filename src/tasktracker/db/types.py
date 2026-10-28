import enum

from sqlalchemy import Enum


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


def pg_enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Колонка PostgreSQL ENUM со значениями из StrEnum, а не из имён."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=_enum_values,
    )
