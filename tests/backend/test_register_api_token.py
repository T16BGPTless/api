import pytest
from unittest.mock import patch, MagicMock
from app.app import app
from http import HTTPStatus

# ------------------------------ MOCK SUPABASE ------------------------------ 
# Creates a mock of a database
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

# CASE 1: SUCCESS (201 CREATED) - API key is created
def test_regiser_API_token_success(client):
    mock_existing = MockResponse(data=[])
    mock_insert = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    
    payload = {"group_name": "test-group"}
    
    with patch("app.routes.auth.get_db", return_value=MagicMock()), \
         patch("app.routes.auth.sb_execute", side_effect=[mock_existing, mock_insert]), \
         patch("app.routes.auth.sb_has_error", return_value=False), \
         patch("app.routes.auth.uuid.uuid4") as mock_uuid:
        
        mock_uuid.return_value.hex = "fake-token-123456"

        response = client.post("/v1/auth/register", 
                               json=payload, 
                               headers={"APIdevToken": "dev-secret"})
        
        assert response.status_code == HTTPStatus.CREATED
        assert response.get_json == {"APItoken" : "fake-token-123456"}
        assert response.mimetype == "application/json"

# CASE 2: UNAUTHORIZED - Missing or Invalid API dev token
def test_generate_invoice_success_rich_data(client):
    mock_existing = MockResponse(data=[])
    mock_insert = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    
    payload = {"group_name": "test-group"}
    
    with patch("app.routes.auth.get_db", return_value=MagicMock()), \
        
        response = client.post("/v1/auth/register", 
                               json=payload, 
                               headers={"APIdevToken": ""})
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert response.get_json == {
            "error": UNAUTHORIZED,
            "message": ANY,
        }
        assert response.mimetype == "application/json"

# CASE 3: FORBIDDEN - API token is authorized to make these changes
def test_generate_invoice_template_not_found(client):
    mock_existing = MockResponse(data=[])
    mock_insert = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    
    payload = {"group_name": "test-group"}
    
    with patch("app.routes.auth.get_db", return_value=MagicMock()), \
        
        response = client.post("/v1/auth/register", 
                               json=payload, 
                               headers={"APIdevToken": "test12345"})
        
        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.get_json == {
            "error": FORBIDDEN,
            "message": ANY,
        }
        assert response.mimetype == "application/json"

# CASE 4: CONFLICT - Group name already exists
def test_generate_invoice_template_wrong_owner(client):
    mock_existing = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    mock_insert = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    
    payload = {"group_name": "test-group"}
    
    with patch("app.routes.auth.get_db", return_value=MagicMock()), \
         patch("app.routes.auth.sb_execute", side_effect=[mock_existing, mock_insert]), \
         patch("app.routes.auth.sb_has_error", return_value=False), \

        response = client.post("/v1/auth/register", 
                               json=payload, 
                               headers={"APIdevToken": "dev-secret"})
        
        assert response.status_code == HTTPStatus.CONFLICT
        assert response.get_json == {
            "error": FORBIDDEN,
            "message": ANY,
        }
        assert response.mimetype == "application/json"

# CASE 5: BAD_REQUEST - group name not provided  (400)
def test_generate_invoice_xml_error(client):
    mock_existing = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    mock_insert = MockResponse(data=[{"group_name": "test-group", "api_token" : "fake-token-123456"}])
    
    payload = {}
    
    with patch("app.routes.auth.get_db", return_value=MagicMock()), \
        response = client.post("/v1/auth/register", 
                               json=payload, 
                               headers={"APIdevToken": "dev-secret"})
        
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.get_json == {
            "error": GROUP_NAME_REQUIRED,
            "message": ANY,
        }
        assert response.mimetype == "application/json"

