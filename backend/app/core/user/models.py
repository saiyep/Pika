from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models_base import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    openid: Mapped[str | None] = mapped_column(String, unique=True, index=True, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String, nullable=True)
    avatar_path: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[str | None] = mapped_column(String, nullable=True)
    account_type: Mapped[str] = mapped_column(String, nullable=False, server_default="wechat")
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="active")


class FamilyGroup(Base, TimestampMixin):
    __tablename__ = "family_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)


class FamilyMembership(Base):
    __tablename__ = "family_memberships"
    __table_args__ = (UniqueConstraint("family_id", "user_id", name="uq_family_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("family_groups.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    family_role: Mapped[str] = mapped_column(String, nullable=False, server_default="member")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class FamilyInvite(Base):
    __tablename__ = "family_invites"
    __table_args__ = (UniqueConstraint("code", name="uq_family_invite_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("family_groups.id"), index=True)
    inviter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    code: Mapped[str] = mapped_column(String, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default="active")
    used_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class UserFavorite(Base):
    """A user's followed services (service market). Platform-level."""

    __tablename__ = "user_favorite"
    __table_args__ = (UniqueConstraint("user_id", "service_key", name="uq_user_service"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    service_key: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
