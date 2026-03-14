"""Delete invoice tests."""

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


# CASE 1: SUCCESS (204 NO_CONTENT)
def test_delete_invoice_success(client):
    """Everything is correct: finds invoice, matches owner, and soft-deletes."""
    mock_xml = "<Invoice><ID>777</ID></Invoice>"
    # 1. First call: Finding the existing invoice
    mock_existing = MockResponse(
        data=[{"owner_token": "my-token", "xml": mock_xml, "deleted": False}]
    )
    # 2. Second call: The update operation success
    mock_update = MockResponse(data=[{"id": 777, "deleted": True}])

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.sb_execute", side_effect=[mock_existing, mock_update]
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "my-token"})

        assert response.status_code == HTTPStatus.NO_CONTENT


# CASE 2: NOT FOUND - ALREADY DELETED (404)
def test_delete_invoice_already_deleted(client):
    """The invoice exists but 'deleted' is already True."""
    mock_existing = MockResponse(data=[{"owner_token": "my-token", "deleted": True}])

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_existing),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "my-token"})
        assert response.status_code == HTTPStatus.NOT_FOUND


# CASE 3: FORBIDDEN - WRONG OWNER (403)
def test_delete_invoice_wrong_owner(client):
    """User tries to delete someone else's invoice."""
    mock_existing = MockResponse(
        data=[{"owner_token": "someone-else", "deleted": False}]
    )

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_existing),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "my-token"})
        assert response.status_code == HTTPStatus.FORBIDDEN


# CASE 4: UNAUTHORIZED (401)
def test_delete_invoice_unauthorized(client):
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=False),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "bad-token"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 5: NOT FOUND - DOES NOT EXIST (404)
def test_delete_invoice_not_found(client):
    """Database returns an empty list for that ID."""
    mock_empty = MockResponse(data=[])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_empty),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.delete("/v1/invoices/999", headers={"APItoken": "token"})
        assert response.status_code == HTTPStatus.NOT_FOUND


# CASE 6: UPDATE FAILURE (500)
def test_delete_invoice_update_error(client):
    """First DB call works, but the second call (the update) fails."""
    mock_existing = MockResponse(data=[{"owner_token": "token", "deleted": False}])

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", side_effect=[mock_existing, None]),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 7: DATABASE CONNECTION FAILURE (500)
def test_delete_invoice_db_connection_fail(client):
    """Scenario where get_db() returns None at the start of deletion."""
    with patch("app.routes.invoices.get_db", return_value=None):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 8: INITIAL QUERY EXECUTION FAILURE (500)
def test_delete_invoice_initial_query_error(client):
    """The first call to find the invoice (select) fails."""
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=None),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 9: INITIAL QUERY SUPABASE ERROR (500)
def test_delete_invoice_initial_supabase_error(client):
    """The select query runs but Supabase returns an error flag."""
    mock_err = MockResponse(error="Database select failed")
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_err),
        patch("app.routes.invoices.sb_has_error", return_value=True),
    ):
        response = client.delete("/v1/invoices/777", headers={"APItoken": "token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
