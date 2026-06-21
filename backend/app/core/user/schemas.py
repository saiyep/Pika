from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    openid: str | None = None
    nickname: str | None = None
    avatar_url: str | None = None
    role: str | None = None
    family_id: int | None = None
    family_role: str | None = None
    account_type: str | None = None
    status: str | None = None


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
    account_type: str | None = None
    status: str | None = None
    family_role: str | None = None


class MemberListOut(BaseModel):
    items: list[MemberItem]


class RoleUpdateIn(BaseModel):
    role: str  # 'admin' | 'member'


class ManagedMemberCreateIn(BaseModel):
    nickname: str


class MemberStatusIn(BaseModel):
    active: bool


class InviteCreateOut(BaseModel):
    code: str


class InviteQrcodeOut(BaseModel):
    code: str
    qrcode_data_url: str


class InviteJoinIn(BaseModel):
    code: str


class FavoriteListOut(BaseModel):
    service_keys: list[str]


class FavoriteIn(BaseModel):
    service_key: str
