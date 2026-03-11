# tests/test_get_invoice.py
import pytest
from unittest.mock import patch
from app.app import app
from http import HTTPStatus

# --------------------------------- FIXTURE --------------------------------- 
# Creates a mock of a server
@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

# ------------------------------ MOCK SUPABASE ------------------------------ 
# Creates a mock of a database
class MockResponse:
    def __init__(self, data, error=None):
        self.data = data
        self.error = error

# ------------------------------- TEST CASES --------------------------------
# CASE 1: SUCCESS (200 OK)
def test_get_invoice_success(client):
    """Everything is correct: valid token, invoice exists, and user owns it."""
    mock_db_data = MockResponse(data=[{
        "owner_token": "valid-token", 
        "xml": "<Invoice><ID>123</ID></Invoice>"
    }])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_db_data):
            response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})
            
            assert response.status_code == HTTPStatus.OK
            assert b"<ID>123</ID>" in response.data
            assert response.mimetype == "application/xml"

# CASE 2: MISSING TOKEN (401)
def test_get_invoice_no_header(client):
    """User forgot to provide the APItoken header."""
    response = client.get("/v1/invoices/123")
    assert response.status_code == HTTPStatus.UNAUTHORIZED

# CASE 3: INVALID TOKEN (401)
def test_get_invoice_bad_token(client):
    """User provided a token, but it's not a real one in our DB."""
    with patch("app.routes.invoices._is_valid_api_token", return_value=False):
        response = client.get("/v1/invoices/123", headers={"APItoken": "fake-token"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED

# CASE 4: DATABASE CRASH (500)
def test_get_invoice_db_failure(client):
    """The DB call fails (returns None) during the invoice lookup."""
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=None):
            response = client.get("/v1/invoices/123", headers={"APItoken": "valid-token"})
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

# CASE 5: NOT FOUND (404)
def test_get_invoice_not_found(client):
    """Token is fine, but the invoice ID doesn't exist in the database."""
    mock_empty = MockResponse(data=[])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_empty):
            response = client.get("/v1/invoices/999", headers={"APItoken": "valid-token"})
            
            assert response.status_code == HTTPStatus.NOT_FOUND
            assert response.get_json()["error"] == "NOT_FOUND"

# CASE 6: FORBIDDEN (403)
def test_get_invoice_wrong_owner(client):
    """The invoice exists, but it belongs to a different API token."""
    mock_db_data = MockResponse(data=[{
        "owner_token": "someone-else", 
        "xml": "<SecretInvoice/>"
    }])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_db_data):
            response = client.get("/v1/invoices/123", headers={"APItoken": "my-token"})
            
            assert response.status_code == HTTPStatus.FORBIDDEN
            assert response.get_json()["error"] == "FORBIDDEN"