import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.core import models_base  # noqa: F401
from app.core.user import models as user_models  # noqa: F401
from app.core.user import service
from app.core.user.models import FamilyMembership, User
from app.modules.medical import models  # noqa: F401


@pytest.fixture
def db_session():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        os.remove(path)


@pytest.fixture
def user(db_session):
    u = User(openid="me", nickname="我", role="admin", account_type="wechat", status="active")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    service.ensure_user_family(db_session, user=u)
    return u


@pytest.fixture
def tmp_avatar(monkeypatch, tmp_path):
    from app.core import storage
    monkeypatch.setattr(storage.settings, "avatar_dir", str(tmp_path))
    return tmp_path


class TestFavorites:
    def test_add_list_remove(self, db_session, user):
        assert service.list_favorites(db_session, user_id=user.id) == []

        service.add_favorite(db_session, user_id=user.id, service_key="medical")
        service.add_favorite(db_session, user_id=user.id, service_key="medical")  # idempotent
        assert service.list_favorites(db_session, user_id=user.id) == ["medical"]

        service.add_favorite(db_session, user_id=user.id, service_key="billing")
        assert set(service.list_favorites(db_session, user_id=user.id)) == {"medical", "billing"}

        service.remove_favorite(db_session, user_id=user.id, service_key="medical")
        assert service.list_favorites(db_session, user_id=user.id) == ["billing"]

    def test_per_user(self, db_session, user):
        other = User(openid="other", nickname="他", account_type="wechat", status="active")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)
        service.ensure_user_family(db_session, user=other)

        service.add_favorite(db_session, user_id=user.id, service_key="medical")
        assert service.list_favorites(db_session, user_id=user.id) == ["medical"]
        assert service.list_favorites(db_session, user_id=other.id) == []


class TestProfile:
    def test_update_nickname_only(self, db_session, user):
        updated = service.update_profile(db_session, user=user, nickname="妈妈")
        assert updated.nickname == "妈妈"
        assert updated.avatar_path is None

    def test_update_avatar_saves_file(self, db_session, user, tmp_avatar):
        from app.core import storage

        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        updated = service.update_profile(
            db_session, user=user, avatar=(png, "a.png", "image/png")
        )
        assert updated.avatar_path is not None
        assert os.path.exists(storage.avatar_abs_path(updated.avatar_path))

    def test_update_both(self, db_session, user, tmp_avatar):
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        updated = service.update_profile(
            db_session, user=user, nickname="爸爸", avatar=(png, "a.png", "image/png")
        )
        assert updated.nickname == "爸爸"
        assert updated.avatar_path is not None


class TestFamilyMembership:
    def test_create_managed_member_under_admin(self, db_session, user):
        managed, membership = service.create_managed_member(db_session, actor=user, nickname="女儿")
        assert managed.openid is None
        assert managed.account_type == "managed"
        assert managed.nickname == "女儿"
        assert membership.family_role == "member"

        actor_m = service.get_active_membership(db_session, user_id=user.id)
        assert actor_m is not None
        assert membership.family_id == actor_m.family_id

    def test_non_admin_cannot_create_managed_member(self, db_session):
        member = User(openid="member-1", nickname="普通成员", role="member", account_type="wechat", status="active")
        db_session.add(member)
        db_session.commit()
        db_session.refresh(member)
        service.ensure_user_family(db_session, user=member)

        with pytest.raises(Exception):
            service.create_managed_member(db_session, actor=member, nickname="孩子")

    def test_set_member_family_role(self, db_session, user):
        managed, _ = service.create_managed_member(db_session, actor=user, nickname="女儿")
        _, updated_membership = service.set_member_family_role(
            db_session,
            actor=user,
            member_id=managed.id,
            family_role="admin",
        )
        assert updated_membership.family_role == "admin"

    def test_soft_remove_and_restore_member(self, db_session, user):
        managed, _ = service.create_managed_member(db_session, actor=user, nickname="女儿")

        member, membership = service.set_member_active(
            db_session,
            actor=user,
            member_id=managed.id,
            is_active=False,
        )
        assert member.status == "disabled"
        assert membership.is_active is False

        member, membership = service.set_member_active(
            db_session,
            actor=user,
            member_id=managed.id,
            is_active=True,
        )
        assert member.status == "active"
        assert membership.is_active is True

    def test_update_member_profile(self, db_session, user, tmp_avatar):
        managed, _ = service.create_managed_member(db_session, actor=user, nickname="旧昵称")
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        member, _ = service.update_member_profile(
            db_session,
            actor=user,
            member_id=managed.id,
            nickname="新昵称",
            avatar=(png, "a.png", "image/png"),
        )
        assert member.nickname == "新昵称"
        assert member.avatar_path is not None

    def test_in_same_family(self, db_session, user):
        managed, _ = service.create_managed_member(db_session, actor=user, nickname="女儿")
        assert service.in_same_family(db_session, actor_user_id=user.id, target_user_id=managed.id) is True

        outsider = User(openid="outsider", nickname="外人", role="member", account_type="wechat", status="active")
        db_session.add(outsider)
        db_session.commit()
        db_session.refresh(outsider)
        service.ensure_user_family(db_session, user=outsider)

        assert service.in_same_family(db_session, actor_user_id=user.id, target_user_id=outsider.id) is False
