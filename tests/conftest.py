# """
# Test fixtures. Uses SQLite in-memory for fast, isolated tests.
# """

# import pytest
# from fastapi.testclient import TestClient
# from sqlalchemy import create_engine
# from sqlalchemy.pool import StaticPool
# from sqlalchemy.orm import sessionmaker

# from app.db.database import Base, get_db
# from app.main import app

# TEST_DB_URL = "sqlite:///:memory:"


# # @pytest.fixture(scope="function")
# # def db_engine():
# #     engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
# #     Base.metadata.create_all(bind=engine)
# #     yield engine
# #     Base.metadata.drop_all(bind=engine)
# #     engine.dispose()

# @pytest.fixture(scope="function")
# def db_engine():
#     engine = create_engine(
#         TEST_DB_URL,
#         connect_args={"check_same_thread": False},
#         poolclass=StaticPool,
#     )
#     Base.metadata.create_all(bind=engine)
#     yield engine
#     Base.metadata.drop_all(bind=engine)
#     engine.dispose()


# @pytest.fixture(scope="function")
# def db_session(db_engine):
#     Session = sessionmaker(bind=db_engine)
#     session = Session()
#     yield session
#     session.close()


# @pytest.fixture(scope="function")
# def client(db_session):
#     def override_get_db():
#         try:
#             yield db_session
#         finally:
#             pass

#     app.dependency_overrides[get_db] = override_get_db
#     with TestClient(app) as c:
#         yield c
#     app.dependency_overrides.clear()


# # ── Shared event payloads ─────────────────────────────────────────────────────

# BASE_EVENT = {
#     "event_id": "evt-001",
#     "event_type": "payment_initiated",
#     "transaction_id": "txn-001",
#     "merchant_id": "merchant_1",
#     "merchant_name": "QuickMart",
#     "amount": 1000.00,
#     "currency": "INR",
#     "timestamp": "2026-03-01T10:00:00+00:00",
# }

"""
Test fixtures.
Uses SQLite in-memory for fast, isolated tests.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app


TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db_engine():
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(bind=db_engine)
    session = Session()

    yield session

    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


BASE_EVENT = {
    "event_id": "evt-001",
    "event_type": "payment_initiated",
    "transaction_id": "txn-001",
    "merchant_id": "merchant_1",
    "merchant_name": "QuickMart",
    "amount": 1000.00,
    "currency": "INR",
    "timestamp": "2026-03-01T10:00:00+00:00",
}