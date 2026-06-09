from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    openid: str
    nickname: str | None = None
    avatar_url: str | None = None
    role: str | None = None


class LoginIn(BaseModel):
    code: str
    nickname: str | None = None


class LoginOut(BaseModel):
    token: str
    user: UserOut


class MemberItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nickname: str | None = None
    avatar_url: str | None = None
    role: str | None = None


class MemberListOut(BaseModel):
    items: list[MemberItem]


class RoleUpdateIn(BaseModel):
    role: str  # 'admin' | 'user'


class FavoriteListOut(BaseModel):
    service_keys: list[str]


class FavoriteIn(BaseModel):
    service_key: str
