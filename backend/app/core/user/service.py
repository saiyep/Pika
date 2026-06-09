from sqlalchemy.orm import Session

from app.core import storage
from app.core.user.models import User, UserFavorite


def list_favorites(db: Session, *, user_id: int) -> list[str]:
    rows = db.query(UserFavorite.service_key).filter_by(user_id=user_id).all()
    return [r[0] for r in rows]


def add_favorite(db: Session, *, user_id: int, service_key: str) -> None:
    exists = (
        db.query(UserFavorite.id)
        .filter_by(user_id=user_id, service_key=service_key)
        .first()
    )
    if exists:
        return
    db.add(UserFavorite(user_id=user_id, service_key=service_key))
    db.commit()


def remove_favorite(db: Session, *, user_id: int, service_key: str) -> None:
    db.query(UserFavorite).filter_by(user_id=user_id, service_key=service_key).delete()
    db.commit()


def update_profile(
    db: Session,
    *,
    user: User,
    nickname: str | None = None,
    avatar: tuple[bytes, str | None, str | None] | None = None,
) -> User:
    """Update the user's nickname and/or avatar. avatar = (bytes, filename,
    content_type); saved to the avatar dir on NAS."""
    if nickname is not None:
        user.nickname = nickname
    if avatar is not None:
        content, filename, content_type = avatar
        user.avatar_path = storage.save_avatar(content, filename, content_type)
    db.commit()
    db.refresh(user)
    return user
