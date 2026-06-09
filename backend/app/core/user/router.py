import os

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core import storage
from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.core.schemas_base import ApiResponse
from app.core.user import service
from app.core.user.models import User
from app.core.user.schemas import (
    FavoriteIn,
    FavoriteListOut,
    MemberItem,
    MemberListOut,
    RoleUpdateIn,
    UserOut,
)

router = APIRouter(prefix="/api/user", tags=["user"])


def _avatar_url(u: User) -> str | None:
    return f"/api/user/{u.id}/avatar" if u.avatar_path else None


def _user_out(u: User) -> UserOut:
    out = UserOut.model_validate(u)
    out.avatar_url = _avatar_url(u)
    return out


def _member_item(u: User) -> MemberItem:
    out = MemberItem.model_validate(u)
    out.avatar_url = _avatar_url(u)
    return out


@router.get("/whoami", response_model=ApiResponse[UserOut])
def whoami(user: User = Depends(get_current_user)):
    return ApiResponse.ok(_user_out(user))


@router.post("/profile", response_model=ApiResponse[UserOut])
async def update_profile(
    nickname: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    avatar_arg = None
    if avatar is not None:
        avatar_arg = (await avatar.read(), avatar.filename, avatar.content_type)
    updated = service.update_profile(db, user=user, nickname=nickname, avatar=avatar_arg)
    return ApiResponse.ok(_user_out(updated))


@router.get("/{user_id}/avatar")
def get_avatar(user_id: int, db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u or not u.avatar_path:
        raise NotFoundError("avatar not found")
    path = storage.avatar_abs_path(u.avatar_path)
    if not os.path.exists(path):
        raise NotFoundError("avatar file missing")
    return FileResponse(path)


@router.get("/members", response_model=ApiResponse[MemberListOut])
def list_members(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    members = db.query(User).order_by(User.id.asc()).all()
    return ApiResponse.ok(MemberListOut(items=[_member_item(m) for m in members]))


@router.put("/members/{member_id}/role", response_model=ApiResponse[MemberItem])
def set_member_role(
    member_id: int,
    body: RoleUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member = db.get(User, member_id)
    if not member:
        raise NotFoundError("member not found")
    member.role = body.role
    db.commit()
    db.refresh(member)
    return ApiResponse.ok(_member_item(member))


@router.get("/favorites", response_model=ApiResponse[FavoriteListOut])
def list_favorites(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return ApiResponse.ok(
        FavoriteListOut(service_keys=service.list_favorites(db, user_id=user.id))
    )


@router.post("/favorites", response_model=ApiResponse[FavoriteListOut])
def add_favorite(
    body: FavoriteIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.add_favorite(db, user_id=user.id, service_key=body.service_key)
    return ApiResponse.ok(
        FavoriteListOut(service_keys=service.list_favorites(db, user_id=user.id))
    )


@router.delete("/favorites/{service_key}", response_model=ApiResponse[FavoriteListOut])
def remove_favorite(
    service_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    service.remove_favorite(db, user_id=user.id, service_key=service_key)
    return ApiResponse.ok(
        FavoriteListOut(service_keys=service.list_favorites(db, user_id=user.id))
    )
