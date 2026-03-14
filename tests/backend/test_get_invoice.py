"""Get invoice tests."""
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
def test_get_invoice_success(client):
    """Everything is correct: valid token, invoice exists, and user owns it."""
    mock_db_data = MockResponse(
        data=[
            {
                "owner_token": "valid-token",
                "xml": "<Invoice><ID>123</ID></Invoice>",
                "deleted": False,
            }
        ]
    )

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_db_data),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})

        assert response.status_code == HTTPStatus.OK
        assert b"<ID>123</ID>" in response.data
        assert response.mimetype == "application/xml"


# CASE 2: DATABASE INITIALIZATION FAILURE (500)
def test_get_invoice_db_connection_fail(client):
    """Scenario where get_db() returns None (e.g., missing env vars)."""
    with patch("app.routes.invoices.get_db", return_value=None):
        response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 3: UNAUTHORIZED - MISSING HEADER (401)
def test_get_invoice_missing_header(client):
    """User forgot to provide the APItoken header."""
    with patch("app.routes.invoices.get_db", return_value=MagicMock()):
        response = client.get("/v1/invoices/123")
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 4: UNAUTHORIZED - INVALID TOKEN (401)
def test_get_invoice_invalid_token(client):
    """Token provided but is_valid_api_token returns False."""
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=False),
    ):
        response = client.get("/v1/invoices/123", headers={"APItoken": "fake-token"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 5: DATABASE EXECUTION FAILURE (500)
def test_get_invoice_db_execution_error(client):
    """The query execution fails (sb_execute returns None)."""
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=None),
    ):
        response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 6: SUPABASE ERROR RESPONSE (500)
def test_get_invoice_supabase_has_error(client):
    """The query runs but Supabase returns an error flag."""
    mock_err = MockResponse(error="Database Error")
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_err),
        patch("app.routes.invoices.sb_has_error", return_value=True),
    ):
        response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 7: NOT FOUND - INVOICE DOES NOT EXIST (404)
def test_get_invoice_not_found(client):
    """The invoice ID doesn't exist in the database (empty data array)."""
    mock_empty = MockResponse(data=[])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_empty),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.get("/v1/invoices/999", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.NOT_FOUND


# CASE 8: NOT FOUND - SOFT DELETED (404)
def test_get_invoice_deleted(client):
    """The invoice exists but has the 'deleted' flag set to True."""
    mock_deleted = MockResponse(
        data=[{"owner_token": "valid-token", "xml": "<Invoice/>", "deleted": True}]
    )
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_deleted),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.NOT_FOUND


# CASE 9: FORBIDDEN - WRONG OWNER (403)
def test_get_invoice_wrong_owner(client):
    """The invoice exists but belongs to a different owner_token."""
    mock_wrong_owner = MockResponse(
        data=[
            {
                "owner_token": "attacker-token",
                "xml": "<SecretInvoice/>",
                "deleted": False,
            }
        ]
    )
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_wrong_owner),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.get("/v1/invoices/123", headers={"APItoken": "my-token"})
        assert response.status_code == HTTPStatus.FORBIDDEN
