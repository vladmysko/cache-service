import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, SQLModel, create_engine

from app.db.database import get_session
from app.main import app


@pytest.fixture
def engine(tmp_path):
    database_url = os.environ.get("TEST_DATABASE_URL")
    if database_url:
        test_engine = create_engine(database_url, pool_pre_ping=True)
        schema = "test_" + uuid4().hex
        with test_engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        # Each test has its own schema; existing database tables stay untouched.
        test_engine = test_engine.execution_options(schema_translate_map={None: schema})
    else:
        test_engine = create_engine(
            f"sqlite:///{tmp_path / 'test.db'}",
            connect_args={"check_same_thread": False, "timeout": 10},
        )
    try:
        SQLModel.metadata.create_all(test_engine)
        yield test_engine
    finally:
        if database_url:
            with test_engine.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        test_engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    def get_test_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()