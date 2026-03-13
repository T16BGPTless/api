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

# CASE 1: SUCCESS (201 CREATED) - Using Template ID
def test_generate_invoice_success_template(client):
    """Valid token and template ID: creates and returns XML."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": "valid-token"}])
    mock_insert = MockResponse(data=[{"id": 500}])
    
    payload = {"templateInvoice": "T123"}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.sb_execute", side_effect=[mock_tmpl_check, mock_insert]), \
         patch("app.routes.invoices.sb_has_error", return_value=False):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        
        assert response.status_code == HTTPStatus.CREATED
        assert b"<Template>T123</Template>" in response.data
        assert response.mimetype == "application/xml"

# CASE 2: SUCCESS - Using Rich Invoice Data
def test_generate_invoice_success_rich_data(client):
    """If InvoiceData is provided, it calls build_invoice_xml."""
    mock_insert = MockResponse(data=[{"id": 501}])
    payload = {"InvoiceData": {"items": []}}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.build_invoice_xml", return_value="<RichXML/>"), \
         patch("app.routes.invoices.sb_execute", return_value=mock_insert), \
         patch("app.routes.invoices.sb_has_error", return_value=False):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        
        assert response.status_code == HTTPStatus.CREATED
        assert b"<RichXML/>" in response.data

# CASE 3: NOT FOUND - Template Doesn't Exist (404)
def test_generate_invoice_template_not_found(client):
    mock_tmpl_check = MockResponse(data=[]) # No rows found
    payload = {"templateInvoice": "NONEXISTENT"}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.sb_execute", return_value=mock_tmpl_check):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.NOT_FOUND

# CASE 4: FORBIDDEN - Template Owned by Someone Else (403)
def test_generate_invoice_template_wrong_owner(client):
    mock_tmpl_check = MockResponse(data=[{"owner_token": "someone-else"}])
    payload = {"templateInvoice": "T123"}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.sb_execute", return_value=mock_tmpl_check):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.FORBIDDEN

# CASE 5: BAD REQUEST - XML Build Failure (400)
def test_generate_invoice_xml_error(client):
    """Tests the try/except block for build_invoice_xml raising ValueError."""
    payload = {"InvoiceData": {"bad": "data"}}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.build_invoice_xml", side_effect=ValueError("Invalid data format")):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.get_json()["error"] == "BAD_REQUEST"

# CASE 6: UNAUTHORIZED (401)
def test_generate_invoice_unauthorized(client):
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=False):
        
        response = client.post("/v1/invoices/generate", headers={"APItoken": "bad"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED

# CASE 7: INTERNAL SERVER ERROR - Insert Fails (500)
def test_generate_invoice_insert_fail(client):
    """Template check passes, but the final insert fails."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": "token"}])
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.sb_execute", side_effect=[mock_tmpl_check, None]):
        
        response = client.post("/v1/invoices/generate", 
                               json={"templateInvoice": "T1"}, 
                               headers={"APItoken": "token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

# CASE 8: DATABASE INITIALIZATION FAILURE (500)
def test_generate_invoice_db_connection_fail(client):
    """Scenario where get_db() returns None at the start of generation."""
    with patch("app.routes.invoices.get_db", return_value=None):
        response = client.post("/v1/invoices/generate", 
                               json={"templateInvoice": "T1"}, 
                               headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

# CASE 9: TEMPLATE LOOKUP EXECUTION FAILURE (500)
def test_generate_invoice_template_lookup_error(client):
    """The query to check if the template exists fails (sb_execute returns None)."""
    # This specifically hits the line: if tmpl_rows_resp is None
    payload = {"templateInvoice": "T123"}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.sb_execute", return_value=None):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

# CASE 10: TEMPLATE LOOKUP SUPABASE ERROR (500)
def test_generate_invoice_template_supabase_error(client):
    """The template lookup runs but Supabase returns an error flag."""
    # This hits the line: or sb_has_error(tmpl_rows_resp)
    mock_err = MockResponse(error="Database Error")
    payload = {"templateInvoice": "T123"}
    
    with patch("app.routes.invoices.get_db", return_value=MagicMock()), \
         patch("app.routes.invoices.is_valid_api_token", return_value=True), \
         patch("app.routes.invoices.sb_execute", return_value=mock_err), \
         patch("app.routes.invoices.sb_has_error", return_value=True):
        
        response = client.post("/v1/invoices/generate", 
                               json=payload, 
                               headers={"APItoken": "valid-token"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR