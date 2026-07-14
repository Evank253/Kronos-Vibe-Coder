import os
import pytest


@pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1", reason="Integration tests disabled"
)
def test_db_migrations_run():
    # This will run migrations and should not raise
    from backend.db_migrate import run_migrations

    run_migrations()
    # verify jobs.db exists
    assert os.path.exists(os.path.join(os.getcwd(), "jobs.db"))
