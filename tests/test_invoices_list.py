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
# Key notes:
# the line ' with patch("app.routes.invoices._sb_execute", return_value=mock_invoices): '
# prevents access to the supabase data. NOTE THIS IS UNIT TESTING

# CASE 1: SUCCESS (DATA FOUND)
def test_list_invoices_success(client):
    """Checks if the API correctly returns a list of IDs when everything works."""
    mock_invoices = MockResponse(data=[{"id": 10}, {"id": 20}])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_invoices):
            response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
            
            assert response.status_code == HTTPStatus.OK
            assert response.get_json() == [10, 20]

# CASE 2: SUCCESS (NO DATA FOUND)
def test_list_invoices_empty(client):
    """Checks if the API returns an empty list [] if the user has no invoices."""
    # We return an empty list in 'data' to simulate a fresh account
    mock_invoices = MockResponse(data=[])
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_invoices):
            response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
            
            assert response.status_code == HTTPStatus.OK
            assert response.get_json() == []

# CASE 3: 401 UNAUTHORIZED (INVALID TOKEN)
def test_list_invoices_invalid_token(client):
    """Checks if the API rejects a token that isn't in our database."""
    with patch("app.routes.invoices._is_valid_api_token", return_value=False):
        response = client.get("/v1/invoices", headers={"APItoken": "wrong-token"})
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.get_json()["error"] == "UNAUTHORIZED"

# CASE 4: 401 UNAUTHORIZED (MISSING HEADER)
def test_list_invoices_missing_token(client):
    """Checks if the API rejects a request that forgot to include the header."""
    # We don't need to mock _is_valid_api_token here because the code 
    # should stop early when it sees 'api_token' is None.
    response = client.get("/v1/invoices") # No headers sent
    
    assert response.status_code == HTTPStatus.UNAUTHORIZED

# CASE 5: 500 INTERNAL SERVER ERROR (DATABASE RETURNED NONE)
def test_list_invoices_db_none(client):
    """Checks how the API handles a total database timeout or crash."""
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        # We simulate the _sb_execute helper returning None (a common crash case)
        with patch("app.routes.invoices._sb_execute", return_value=None):
            response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
            
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert "Database error" in response.get_json()["message"]

# CASE 6: 500 INTERNAL SERVER ERROR (DATABASE RETURNED ERROR OBJECT)
def test_list_invoices_db_error_object(client):
    """Checks how the API handles the database saying 'Something went wrong'."""
    # We create a response that actually contains an error message
    mock_error = MockResponse(data=None, error="Table does not exist")
    
    with patch("app.routes.invoices._is_valid_api_token", return_value=True):
        with patch("app.routes.invoices._sb_execute", return_value=mock_error):
            response = client.get("/v1/invoices", headers={"APItoken": "valid-token"})
            
            assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
            assert response.get_json()["error"] == "INTERNAL_SERVER_ERROR"