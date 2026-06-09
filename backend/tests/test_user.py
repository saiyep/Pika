import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
from app.core import models_base  # noqa: F401
from app.core.user import models as user_models  # noqa: F401
from app.core.user import service
from app.core.user.models import User
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
    u = User(openid="me", nickname="我")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
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
        other = User(openid="other", nickname="他")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)

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
