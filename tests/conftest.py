import pytest
from unittest.mock import MagicMock, patch
from app.app import app as flask_app 

@pytest.fixture
def client():
    """
    Pytest fixture to create a Flask test client.
    The test client allows us to make fake HTTP requests to the app
    without actually running a server.
    """
    with flask_app.test_client() as client:
        yield client


@pytest.fixture
def mock_supabase():
    """
    Pytest fixture to mock the Supabase client.
    This allows us to simulate database responses without connecting to a real DB.
    """
    with patch("app.routes.invoices.get_supabase") as mock_get_client:
        # Create a MagicMock object to represent the Supabase client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        yield mock_client