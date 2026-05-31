from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.exceptions import PikaException
from app.core.models_base import User


def get_current_user(
    x_pika_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """POC auth: token == openid. Resolve the family member from the header."""
    if not x_pika_token:
        raise PikaException("missing X-Pika-Token", code=401)
    user = db.query(User).filter(User.openid == x_pika_token).first()
    if not user:
        raise PikaException("invalid token", code=401)
    return user
