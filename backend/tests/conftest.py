"""
Tests run as integration tests against a real, running Postgres — the same
DATABASE_URL the app itself uses (see CLAUDE.md for how to point this at a
disposable database rather than your dev one). The `apply_migrations` fixture
IS the migration test: if any migration in alembic/versions is broken, this
fixture fails and every test fails with it.
"""
import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from core.config import get_settings

BACKEND_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def event_loop():
    # Session-scoped rather than pytest-asyncio's function-scoped default: main.app's
    # real Depends(get_db) uses core.database's module-level `engine` singleton, which
    # binds to whichever event loop first touches it. A fresh loop per test (the
    # default) breaks that singleton the same way it broke the earlier db_engine
    # fixture — one loop for the whole session keeps it consistent throughout.
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(cfg, "head")
    yield


@pytest_asyncio.fixture
async def db_engine():
    # A fresh engine per test, deliberately not the core.database module-level
    # singleton: that singleton binds to whichever event loop first touches it,
    # and pytest-asyncio gives each test its own loop, which breaks asyncpg.
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
