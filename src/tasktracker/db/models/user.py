import uuid

from sqlalchemy import Boolean, CheckConstraint, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import text, true

from tasktracker.db.base import Base, TimestampMixin
from tasktracker.db.types import pg_enum
from tasktracker.domain.enums import UserRole


class User(TimestampMixin, Base):
    __tablename__ = 'users'
    __table_args__ = (
        UniqueConstraint('email', name='uq_users_email'),
        CheckConstraint('char_length(full_name) >= 1', name='ck_users_full_name_length'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, 'user_role'),
        default=UserRole.USER,
        server_default=text("'user'::user_role"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        nullable=False,
    )
