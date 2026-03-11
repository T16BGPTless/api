import pytest
from unittest.mock import MagicMock
from app.app import app


@pytest.fixture
def client():
    """
    Creates a Flask test client.

    The Flask test client allows us to simulate HTTP requests
    (GET, POST, DELETE etc.) without actually running a server.
    """
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def mock_supabase_client(monkeypatch):
    """
    Replace the real Supabase client with a fake one.

    This prevents tests from connecting to the real database.
    Instead we control what the database returns.
    """

    mock_client = MagicMock()

    # Replace get_supabase() in invoices.py so it returns our fake client
    monkeypatch.setattr(
        "app.routes.invoices.get_supabase",
        lambda: mock_client
    )

    return mock_client