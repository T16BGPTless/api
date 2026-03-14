import pytest
from unittest.mock import patch, MagicMock
from app.app import app
from http import HTTPStatus


# --------------------------------- FIXTURE ---------------------------------
# Creates a mock of a server
@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ------------------------------ MOCK SUPABASE ------------------------------
# Creates a mock of a database
class MockResponse:
    """Helper class to simulate Supabase response objects."""

    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error


# ------------------------------- TEST CASES --------------------------------


# CASE 1: SUCCESS (200 OK)
def test_list_invoices_success(client):
    """Everything is correct: returns a list of invoice IDs."""
    # Simulating a database returning three invoice IDs
    mock_db_data = MockResponse(data=[{"id": 101}, {"id": 102}, {"id": 105}])

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_db_data),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})

        assert response.status_code == HTTPStatus.OK
        assert response.get_json() == [101, 102, 105]


# CASE 2: SUCCESS - NO INVOICES (200 OK)
def test_list_invoices_empty(client):
    """Valid token, but the user has no invoices. Should return empty list."""
    mock_db_data = MockResponse(data=[])

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_db_data),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})

        assert response.status_code == HTTPStatus.OK
        assert response.get_json() == []


# CASE 3: DATABASE INITIALIZATION FAILURE (500)
def test_list_invoices_db_connection_fail(client):
    with patch("app.routes.invoices.get_db", return_value=None):
        response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 4: UNAUTHORIZED - MISSING HEADER (401)
def test_list_invoices_missing_header(client):
    with patch("app.routes.invoices.get_db", return_value=MagicMock()):
        response = client.get("/v1/invoices")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 5: UNAUTHORIZED - INVALID TOKEN (401)
def test_list_invoices_invalid_token(client):
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=False),
    ):
        response = client.get("/v1/invoices", headers={"APItoken": "fake-token"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 6: DATABASE EXECUTION FAILURE (500)
def test_list_invoices_db_execution_error(client):
    """sb_execute returns None (e.g. database timeout)."""
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=None),
    ):
        response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 7: SUPABASE ERROR RESPONSE (500)
def test_list_invoices_supabase_has_error(client):
    """Supabase returns an error object."""
    mock_err = MockResponse(error="Database select failed")
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_err),
        patch("app.routes.invoices.sb_has_error", return_value=True),
    ):
        response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
