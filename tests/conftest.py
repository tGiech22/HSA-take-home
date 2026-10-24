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


@pytest.fixture
def concurrent_account(postgres_engine):
    """Committed setup and independent request connections for concurrency tests."""
    from datetime import date
    from types import SimpleNamespace
    from uuid import uuid4

    from sqlalchemy import create_engine, delete
    from sqlalchemy.orm import Session

    from src.database.models import Account, DebitCard, Transaction, User
    from src.database.session import get_session
    from src.enums import CardStatus

    engine = create_engine(
        postgres_engine.url,
        connect_args={"options": "-c statement_timeout=10000 -c lock_timeout=5000"},
    )
    user_id = None
    account_id = None
    previous_override = app.dependency_overrides.get(get_session)

    def override_session():
        with Session(engine) as session:
            yield session

    try:
        with Session(engine) as session, session.begin():
            user = User(name="Concurrency", email=f"{uuid4().hex}@example.com")
            session.add(user)
            session.flush()
            user_id = user.id
            account = Account(user_id=user_id)
            session.add(account)
            session.flush()
            account_id = account.id
            card = DebitCard(
                account_id=account_id, last_four="0001", expires_on=date(2099, 12, 31),
                status=CardStatus.ACTIVE, cardholder_name="Concurrency",
            )
            session.add(card)
            session.flush()
            card_id = card.id
        # Set the override once before launching workers. Each request opens its
        # own session, and each worker constructs its own HTTP client.
        app.dependency_overrides[get_session] = override_session
        yield SimpleNamespace(
            base_url=f"/users/{user_id}/accounts/{account_id}",
            account_id=account_id,
            card_id=card_id,
            client=lambda: TestClient(app),
            session=lambda: Session(engine),
        )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = previous_override
        try:
            # Cleanup deletes are restricted to this fixture's committed data in
            # the disposable database, not the application's ledger repository.
            with engine.begin() as connection:
                if account_id is not None:
                    connection.execute(delete(Transaction).where(Transaction.account_id == account_id))
                    connection.execute(delete(DebitCard).where(DebitCard.account_id == account_id))
                    connection.execute(delete(Account).where(Account.id == account_id))
                if user_id is not None:
                    connection.execute(delete(User).where(User.id == user_id))
        finally:
            engine.dispose()
