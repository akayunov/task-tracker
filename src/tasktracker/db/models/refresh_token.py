import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from tasktracker.db.base import Base, TimestampMixin


class RefreshToken(TimestampMixin, Base):
    __tablename__ = 'refresh_tokens'
    __table_args__ = (
        UniqueConstraint('token_hash', name='uq_refresh_tokens_token_hash'),
        Index('ix_refresh_tokens_user_id', 'user_id'),
        Index('ix_refresh_tokens_expires_at', 'expires_at'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey('users.id', name='fk_refresh_tokens_user_id_users', ondelete='CASCADE'),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
