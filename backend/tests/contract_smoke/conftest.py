from __future__ import annotations

import os
import socket
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import text


def assert_safe_test_database(url: str, allow_reset: str | None) -> None:
    database = urlparse(url.replace("postgresql+psycopg", "postgresql")).path.lstrip("/")
    if "test" not in database.lower():
        raise RuntimeError("Contract smoke database name must contain 'test'")
    if allow_reset != "true":
        raise RuntimeError("ALLOW_TEST_DATABASE_RESET=true is required")


@pytest.fixture(scope="session", autouse=True)
def contract_environment():
    url = os.getenv("DATABASE_URL", "")
    if not url or os.getenv("ALLOW_TEST_DATABASE_RESET") != "true":
        pytest.skip("contract smoke requires the guarded disposable database runner")
    assert_safe_test_database(url, os.getenv("ALLOW_TEST_DATABASE_RESET"))
    upload_dir = Path(os.environ["UPLOAD_DIR"]).resolve()
    assert "contract" in str(upload_dir).lower() or "tmp" in str(upload_dir).lower()


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    original = socket.socket.connect

    def guarded_connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "localhost", "::1"}:
            raise RuntimeError(f"external network disabled in contract smoke tests: {address[0]}")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)


@pytest.fixture(autouse=True)
def clean_database(contract_environment):
    from app.core.database import engine

    with engine.begin() as connection:
        names = connection.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename <> 'alembic_version'")
        ).scalars().all()
        if names:
            quoted = ", ".join(f'"{name}"' for name in names)
            connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


@pytest.fixture
def client(clean_database):
    from app.main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db(clean_database):
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
