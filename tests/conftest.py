import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def postgres_engine():
    """Migrate a uniquely named disposable database; never clear the app database."""
    import os
    from pathlib import Path
    from uuid import uuid4

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, text

    from src.config import settings

    admin = create_engine(
        os.environ.get("TEST_DATABASE_ADMIN_URL", settings.database_url),
        isolation_level="AUTOCOMMIT",
    )
    database_name = "hsa_tests_" + uuid4().hex
    test_engine = None
    created = False
    original_url = settings.database_url
    try:
        with admin.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))
        created = True
        test_engine = create_engine(admin.url.set(database=database_name))
        settings.database_url = test_engine.url.render_as_string(hide_password=False)
        root = Path(__file__).resolve().parents[1]
        command.upgrade(Config(str(root / "backend/alembic.ini")), "head")
        settings.database_url = original_url
        yield test_engine
    finally:
        settings.database_url = original_url
        if test_engine is not None:
            test_engine.dispose()
        if created:
            with admin.connect() as connection:
                connection.execute(text(f'DROP DATABASE "{database_name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def db_connection(postgres_engine):
    # Endpoint commits release savepoints; rolling back this outer transaction
    # removes all data inserted by each test.
    with postgres_engine.connect() as connection:
        transaction = connection.begin()
        try:
            yield connection
        finally:
            transaction.rollback()


@pytest.fixture
def db_client(db_connection):
    from sqlalchemy.orm import Session

    from src.database.session import get_session

    def override_session():
        with Session(bind=db_connection, join_transaction_mode="create_savepoint") as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.pop(get_session, None)
