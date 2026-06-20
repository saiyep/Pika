from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import PikaException
from app.core.user import service as user_service
from app.core.user.models import FamilyMembership, User


def get_current_user(
    x_pika_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not x_pika_token:
        raise PikaException("missing X-Pika-Token", code=401)
    user = db.query(User).filter(User.openid == x_pika_token).first()
    if not user:
        raise PikaException("invalid token", code=401)
    return user


def get_current_membership(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FamilyMembership:
    membership = user_service.ensure_user_family(db, user=user)
    if not membership or not membership.is_active:
        raise PikaException("family membership required", code=403)
    return membership
