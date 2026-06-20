from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.schemas_base import ApiResponse
from app.core.user import service as user_service
from app.core.user.models import User
from app.core.user.schemas import LoginIn, LoginOut, UserOut
from app.core.wechat import code_to_openid
from app.settings import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[LoginOut])
def login(body: LoginIn, db: Session = Depends(get_db)):
    openid = code_to_openid(body.code)
    role = "admin" if openid and openid == settings.admin_openid else "member"

    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(
            openid=openid,
            nickname=body.nickname,
            role=role,
            account_type="wechat",
            status="active",
        )
        db.add(user)
    else:
        if body.nickname and user.nickname != body.nickname:
            user.nickname = body.nickname
        if role == "admin" and user.role != "admin":
            user.role = "admin"
        elif not user.role:
            user.role = "member"
        if not user.account_type:
            user.account_type = "wechat"
        if not user.status:
            user.status = "active"
    db.commit()
    db.refresh(user)

    membership = user_service.ensure_user_family(db, user=user)

    out = UserOut.model_validate(user)
    out.avatar_url = f"/api/user/{user.id}/avatar" if user.avatar_path else None
    out.family_id = membership.family_id
    out.family_role = membership.family_role
    out.account_type = user.account_type
    out.status = user.status
    return ApiResponse.ok(LoginOut(token=openid, user=out))
