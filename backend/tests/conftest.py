"""Session-wide test setup: a real, ephemeral Postgres container.

app.storage.database.create_engine() requires DATABASE_URL to point at
Postgres (see that module's docstring) — no SQLite fallback, so every test
that spins up the app (any test using a `client` fixture built on
TestClient(app)) needs one. Starting a throwaway container here, once per
test session, means the suite still runs with a plain `pytest` and no
manually-started docker-compose, while still exercising the real
Postgres-specific SQL SQLite would silently paper over (native ENUM
columns, JSONB, transaction/locking semantics, ...).
"""

import os

import pytest
from testcontainers.community.postgres import PostgresContainer


@pytest.fixture(scope="session", autouse=True)
def _postgres_container():
    with PostgresContainer(
        "postgres:16-alpine", username="sorter", password="sorter", dbname="sorter", driver="asyncpg"
    ) as postgres:
        os.environ["DATABASE_URL"] = postgres.get_connection_url()
        yield postgres
