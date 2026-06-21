import secrets
import string

from sqlalchemy.orm import Session

from app.core import storage
from app.core.exceptions import PikaException
from app.core.user.models import FamilyGroup, FamilyInvite, FamilyMembership, User, UserFavorite


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
    if nickname is not None:
        user.nickname = nickname
    if avatar is not None:
        content, filename, content_type = avatar
        user.avatar_path = storage.save_avatar(content, filename, content_type)
    db.commit()
    db.refresh(user)
    return user


def ensure_user_family(db: Session, *, user: User, family_name: str | None = None) -> FamilyMembership:
    membership = (
        db.query(FamilyMembership)
        .filter(FamilyMembership.user_id == user.id, FamilyMembership.is_active.is_(True))
        .first()
    )
    if membership:
        if (user.role or "").lower() == "admin" and membership.family_role != "admin":
            membership.family_role = "admin"
            db.commit()
            db.refresh(membership)
        return membership

    family = FamilyGroup(name=(family_name or user.nickname or f"family-{user.id}"), owner_user_id=user.id)
    db.add(family)
    db.flush()

    role = "admin" if (user.role or "").lower() == "admin" else "member"
    membership = FamilyMembership(family_id=family.id, user_id=user.id, family_role=role, is_active=True)
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def get_active_membership(db: Session, *, user_id: int) -> FamilyMembership | None:
    return (
        db.query(FamilyMembership)
        .filter(FamilyMembership.user_id == user_id, FamilyMembership.is_active.is_(True))
        .first()
    )


def list_family_members(db: Session, *, user: User, include_inactive: bool = True) -> list[tuple[User, FamilyMembership]]:
    membership = ensure_user_family(db, user=user)
    q = (
        db.query(User, FamilyMembership)
        .join(FamilyMembership, FamilyMembership.user_id == User.id)
        .filter(FamilyMembership.family_id == membership.family_id)
    )
    if not include_inactive:
        q = q.filter(FamilyMembership.is_active.is_(True))
    rows = q.order_by(FamilyMembership.is_active.desc(), User.id.asc()).all()
    return rows


def require_family_admin(db: Session, *, user: User) -> FamilyMembership:
    membership = ensure_user_family(db, user=user)
    if membership.family_role != "admin":
        raise PikaException("admin required", code=403)
    return membership


def create_managed_member(db: Session, *, actor: User, nickname: str) -> tuple[User, FamilyMembership]:
    actor_membership = require_family_admin(db, user=actor)
    clean_name = (nickname or "").strip()
    if not clean_name:
        raise PikaException("nickname required", code=400)

    user = User(
        openid=None,
        nickname=clean_name,
        role="member",
        account_type="managed",
        status="active",
    )
    db.add(user)
    db.flush()

    membership = FamilyMembership(
        family_id=actor_membership.family_id,
        user_id=user.id,
        family_role="member",
        is_active=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(user)
    db.refresh(membership)
    return user, membership


def set_member_family_role(
    db: Session,
    *,
    actor: User,
    member_id: int,
    family_role: str,
) -> tuple[User, FamilyMembership]:
    if family_role not in {"admin", "member"}:
        raise PikaException("invalid role", code=400)

    actor_membership = require_family_admin(db, user=actor)
    target_membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.user_id == member_id,
            FamilyMembership.family_id == actor_membership.family_id,
        )
        .first()
    )
    if not target_membership:
        raise PikaException("member not found", code=404)
    if member_id == actor.id:
        raise PikaException("cannot change self role", code=400)

    target_membership.family_role = family_role
    member = db.get(User, member_id)
    if not member:
        raise PikaException("member not found", code=404)

    member.role = family_role
    db.commit()
    db.refresh(member)
    db.refresh(target_membership)
    return member, target_membership


def set_member_active(
    db: Session,
    *,
    actor: User,
    member_id: int,
    is_active: bool,
) -> tuple[User, FamilyMembership]:
    actor_membership = require_family_admin(db, user=actor)
    target_membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.user_id == member_id,
            FamilyMembership.family_id == actor_membership.family_id,
        )
        .first()
    )
    if not target_membership:
        raise PikaException("member not found", code=404)
    if member_id == actor.id and not is_active:
        raise PikaException("cannot remove self", code=400)

    member = db.get(User, member_id)
    if not member:
        raise PikaException("member not found", code=404)

    target_membership.is_active = is_active
    member.status = "active" if is_active else "disabled"
    db.commit()
    db.refresh(member)
    db.refresh(target_membership)
    return member, target_membership


def update_member_profile(
    db: Session,
    *,
    actor: User,
    member_id: int,
    nickname: str | None,
    avatar: tuple[bytes, str | None, str | None] | None,
) -> tuple[User, FamilyMembership]:
    actor_membership = require_family_admin(db, user=actor)
    target_membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.user_id == member_id,
            FamilyMembership.family_id == actor_membership.family_id,
        )
        .first()
    )
    if not target_membership:
        raise PikaException("member not found", code=404)

    member = db.get(User, member_id)
    if not member:
        raise PikaException("member not found", code=404)

    if nickname is not None:
        clean = nickname.strip()
        if not clean:
            raise PikaException("nickname required", code=400)
        member.nickname = clean
    if avatar is not None:
        content, filename, content_type = avatar
        member.avatar_path = storage.save_avatar(content, filename, content_type)

    db.commit()
    db.refresh(member)
    db.refresh(target_membership)
    return member, target_membership


def in_same_family(db: Session, *, actor_user_id: int, target_user_id: int) -> bool:
    actor = get_active_membership(db, user_id=actor_user_id)
    target = get_active_membership(db, user_id=target_user_id)
    return bool(actor and target and actor.family_id == target.family_id)


def can_edit_report(db: Session, *, actor: User, uploader_id: int, subject_id: int | None) -> bool:
    actor_membership = get_active_membership(db, user_id=actor.id)
    if not actor_membership:
        return False
    if actor_membership.family_role == "admin":
        return True
    if uploader_id == actor.id:
        return True
    if subject_id is not None and subject_id == actor.id:
        return True
    return False


def _new_invite_code(db: Session) -> str:
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        exists = db.query(FamilyInvite.id).filter(FamilyInvite.code == code).first()
        if not exists:
            return code


def create_family_invite(db: Session, *, actor: User) -> FamilyInvite:
    membership = require_family_admin(db, user=actor)
    code = _new_invite_code(db)
    invite = FamilyInvite(
        family_id=membership.family_id,
        inviter_user_id=actor.id,
        code=code,
        status="active",
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite


def join_family_by_invite(db: Session, *, actor: User, code: str) -> FamilyMembership:
    clean = (code or "").strip().upper()
    if not clean:
        raise PikaException("invite code required", code=400)

    invite = db.query(FamilyInvite).filter(FamilyInvite.code == clean).first()
    if not invite or invite.status != "active":
        raise PikaException("invalid invite code", code=404)

    existing = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.family_id == invite.family_id,
            FamilyMembership.user_id == actor.id,
            FamilyMembership.is_active.is_(True),
        )
        .first()
    )
    if existing:
        invite.status = "used"
        invite.used_by_user_id = actor.id
        db.commit()
        db.refresh(existing)
        return existing

    actor_membership = get_active_membership(db, user_id=actor.id)
    if actor_membership and actor_membership.family_id != invite.family_id:
        actor_membership.is_active = False

    membership = (
        db.query(FamilyMembership)
        .filter(
            FamilyMembership.family_id == invite.family_id,
            FamilyMembership.user_id == actor.id,
        )
        .first()
    )
    if membership:
        membership.is_active = True
        membership.family_role = membership.family_role or "member"
    else:
        membership = FamilyMembership(
            family_id=invite.family_id,
            user_id=actor.id,
            family_role="member",
            is_active=True,
        )
        db.add(membership)

    invite.status = "used"
    invite.used_by_user_id = actor.id
    db.commit()
    db.refresh(membership)
    return membership
