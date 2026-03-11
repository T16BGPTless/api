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
# ------------------------------- TEST CASES --------------------------------

# CASE 1: SUCCESS (200 OK)
def test_delete_invoice_success(client):
    """Everything is correct: user owns the invoice, so it gets deleted."""
    # 1. First DB response: The 'select' call to find the owner
    existing_data = MockResponse(data=[{"owner_token": "token123", "xml": "<invoice/>"}])
    # 2. Second DB response: The 'delete' call itself
    delete_result = MockResponse(data=[]) 

    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute") as mock_exec:
            # side_effect feeds the results in the order the code calls them
            mock_exec.side_effect = [existing_data, delete_result]
            
            response = client.delete("/v1/invoices/1", headers={"APItoken": "token123"})
            
            assert response.status_code == HTTPStatus.OK
            assert response.data == b"<invoice/>"

# CASE 2: MISSING HEADER (401)
def test_delete_invoice_no_header(client):
    """User forgot to provide the APItoken header."""
    response = client.delete("/v1/invoices/1")
    assert response.status_code == HTTPStatus.UNAUTHORIZED

# CASE 3: INVALID TOKEN (401)
def test_delete_invoice_bad_token(client):
    """Token provided doesn't exist in our records."""
    with patch("app.routes.invoices._is_valid_api_token", return_value=False):
        response = client.delete("/v1/invoices/1", headers={"APItoken": "fake-token"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED

# CASE 4: DATABASE ERROR ON FIND (500)
def test_delete_invoice_db_error_on_find(client):
    """The database fails while trying to look up the invoice."""
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=None):
            response = client.delete("/v1/invoices/1", headers={"APItoken": "token123"})
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

# CASE 5: NOT FOUND (404)
def test_delete_invoice_not_found(client):
    """User tried to delete an ID that doesn't exist."""
    mock_empty = MockResponse(data=[])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_empty):
            response = client.delete("/v1/invoices/999", headers={"APItoken": "token123"})
            assert response.status_code == HTTPStatus.NOT_FOUND

# CASE 6: FORBIDDEN (403)
def test_delete_invoice_wrong_owner(client):
    """Invoice exists, but belongs to someone else."""
    mock_other_owner = MockResponse(data=[{"owner_token": "someone-else", "xml": "<secret/>"}])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_other_owner):
            response = client.delete("/v1/invoices/1", headers={"APItoken": "my-token"})
            assert response.status_code == HTTPStatus.FORBIDDEN

# CASE 7: DATABASE ERROR ON DELETE (500)
def test_delete_invoice_db_error_on_delete(client):
    """Lookup worked, but the database crashed during the actual deletion."""
    existing_data = MockResponse(data=[{"owner_token": "token123", "xml": "<old/>"}])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute") as mock_exec:
            # First call succeeds, second call fails
            mock_exec.side_effect = [existing_data, None]
            
            response = client.delete("/v1/invoices/1", headers={"APItoken": "token123"})
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR