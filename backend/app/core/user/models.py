from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models_base import TimestampMixin


class User(Base, TimestampMixin):
    """Platform-level family member. Identified by WeChat openid.

    POC: no permissions. Used to identify & display who uploaded / whose
    report. Shared across all modules.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)


class UserFavorite(Base):
    """A user's followed services (service market). Platform-level."""

    __tablename__ = "user_favorite"
    __table_args__ = (UniqueConstraint("user_id", "service_key", name="uq_user_service"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    service_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
