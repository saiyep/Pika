import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.db import Base
# Import models so they register on Base.metadata.
from app.core import models_base  # noqa: F401
from app.modules.medical import models  # noqa: F401


@pytest.fixture
def db_session():
    """Isolated on-disk SQLite per test. Schema via create_all (tests don't
    need Alembic; the real DB does)."""
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
