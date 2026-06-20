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
    ManagedMemberCreateIn,
    MemberItem,
    MemberListOut,
    MemberStatusIn,
    RoleUpdateIn,
    UserOut,
)

router = APIRouter(prefix="/api/user", tags=["user"])


def _avatar_url(u: User) -> str | None:
    return f"/api/user/{u.id}/avatar" if u.avatar_path else None


def _user_out(u: User, *, family_id: int | None = None, family_role: str | None = None) -> UserOut:
    out = UserOut.model_validate(u)
    out.avatar_url = _avatar_url(u)
    out.family_id = family_id
    out.family_role = family_role
    out.account_type = u.account_type
    out.status = u.status
    return out


def _member_item(u: User, *, family_role: str | None = None, is_active: bool = True) -> MemberItem:
    out = MemberItem.model_validate(u)
    out.avatar_url = _avatar_url(u)
    out.account_type = u.account_type
    out.status = "active" if is_active else "disabled"
    out.family_role = family_role
    return out


@router.get("/whoami", response_model=ApiResponse[UserOut])
def whoami(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    membership = service.ensure_user_family(db, user=user)
    return ApiResponse.ok(_user_out(user, family_id=membership.family_id, family_role=membership.family_role))


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
    membership = service.ensure_user_family(db, user=updated)
    return ApiResponse.ok(_user_out(updated, family_id=membership.family_id, family_role=membership.family_role))


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
    rows = service.list_family_members(db, user=user, include_inactive=True)
    return ApiResponse.ok(
        MemberListOut(
            items=[
                _member_item(
                    member,
                    family_role=membership.family_role,
                    is_active=membership.is_active,
                )
                for member, membership in rows
            ]
        )
    )


@router.post("/members", response_model=ApiResponse[MemberItem])
def create_managed_member(
    body: ManagedMemberCreateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member, membership = service.create_managed_member(db, actor=user, nickname=body.nickname)
    return ApiResponse.ok(_member_item(member, family_role=membership.family_role))


@router.put("/members/{member_id}/role", response_model=ApiResponse[MemberItem])
def set_member_role(
    member_id: int,
    body: RoleUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member, membership = service.set_member_family_role(
        db,
        actor=user,
        member_id=member_id,
        family_role=body.role,
    )
    return ApiResponse.ok(
        _member_item(member, family_role=membership.family_role, is_active=membership.is_active)
    )


@router.put("/members/{member_id}/status", response_model=ApiResponse[MemberItem])
def set_member_status(
    member_id: int,
    body: MemberStatusIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    member, membership = service.set_member_active(
        db,
        actor=user,
        member_id=member_id,
        is_active=body.active,
    )
    return ApiResponse.ok(
        _member_item(member, family_role=membership.family_role, is_active=membership.is_active)
    )


@router.post("/members/{member_id}/profile", response_model=ApiResponse[MemberItem])
async def update_member_profile(
    member_id: int,
    nickname: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    avatar_arg = None
    if avatar is not None:
        avatar_arg = (await avatar.read(), avatar.filename, avatar.content_type)

    member, membership = service.update_member_profile(
        db,
        actor=user,
        member_id=member_id,
        nickname=nickname,
        avatar=avatar_arg,
    )
    return ApiResponse.ok(
        _member_item(member, family_role=membership.family_role, is_active=membership.is_active)
    )


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
