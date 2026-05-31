from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models_base import User
from app.core.schemas_base import ApiResponse
from app.core.wechat import code_to_openid
from app.modules.medical.schemas import LoginIn, LoginOut, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=ApiResponse[LoginOut])
def login(body: LoginIn, db: Session = Depends(get_db)):
    openid = code_to_openid(body.code)

    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=body.nickname)
        db.add(user)
    elif body.nickname and user.nickname != body.nickname:
        user.nickname = body.nickname
    db.commit()
    db.refresh(user)

    # POC: token == openid
    return ApiResponse.ok(LoginOut(token=openid, user=UserOut.model_validate(user)))
