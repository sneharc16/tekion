"""Always isolate tests; PostgreSQL uses a fresh, disposable schema."""

import os
import tempfile
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

# Explicit test configuration, never DATABASE_URL from a running demo.
_test_url = os.getenv("TEST_DATABASE_URL")
_directory = tempfile.TemporaryDirectory(prefix="battery-pytest-")
_admin = None
_schema = None
if _test_url:
    url = make_url(_test_url)
    if url.get_backend_name() != "postgresql":
        raise RuntimeError(
            "TEST_DATABASE_URL must be PostgreSQL; SQLite tests already isolate automatically"
        )
    _admin = create_engine(url)
    _schema = "battery_test_" + uuid.uuid4().hex
    with _admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{_schema}"'))
    os.environ["DATABASE_URL"] = url.update_query_dict(
        {"options": "-csearch_path=" + _schema}
    ).render_as_string(hide_password=False)
else:
    os.environ["DATABASE_URL"] = "sqlite:///" + _directory.name + "/test.db"
os.environ["DEMO_MODE"] = "true"
os.environ["DATA_MODE"] = "fixture"
os.environ["ASSESSMENT_DATE"] = "2026-11-16"


def pytest_sessionfinish(session, exitstatus):
    from apps.api.app.store import engine

    engine.dispose()
    if _admin is not None:
        with _admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{_schema}" CASCADE'))
        _admin.dispose()
    _directory.cleanup()
