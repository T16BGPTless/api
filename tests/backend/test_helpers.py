import pytest
from unittest.mock import patch, MagicMock
from postgrest.exceptions import APIError
from http import HTTPStatus
from app.routes.helpers import (
    sb_has_error, 
    sb_execute, 
    get_db, 
    return_error
)
from app.routes.invoices import is_valid_api_token
from app.app import app

# ------------------------------ MOCK SUPABASE ------------------------------ 
# Creates a mock of a database
class MockResponse:
    """Helper to simulate Supabase response objects."""
    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error

# -------------------------- is_valid_api_token --------------------------

def test_is_valid_api_token_true():
    """Returns True if database finds exactly one matching token."""
    mock_supabase = MagicMock()
    mock_resp = MockResponse(data=[{"api_token": "good-token"}])
    
    with patch("app.routes.invoices.sb_execute", return_value=mock_resp), \
         patch("app.routes.invoices.sb_has_error", return_value=False):
        assert is_valid_api_token(mock_supabase, "good-token") is True

def test_is_valid_api_token_false_empty():
    """Returns False if token is not in the database."""
    mock_supabase = MagicMock()
    mock_resp = MockResponse(data=[]) 
    
    with patch("app.routes.invoices.sb_execute", return_value=mock_resp), \
         patch("app.routes.invoices.sb_has_error", return_value=False):
        assert is_valid_api_token(mock_supabase, "bad-token") is False

def test_is_valid_api_token_db_error():
    """Returns False if sb_execute fails or has an error."""
    mock_supabase = MagicMock()
    
    with patch("app.routes.invoices.sb_execute", return_value=None):
        assert is_valid_api_token(mock_supabase, "token") is False

# -------------------------- sb_has_error --------------------------

def test_sb_has_error():
    assert sb_has_error(MockResponse(error="Some Error")) is True
    assert sb_has_error(MockResponse(data=[])) is False
    assert sb_has_error(None) is False 

# -------------------------- sb_execute --------------------------

def test_sb_execute_success():
    mock_builder = MagicMock()
    mock_builder.execute.return_value = "Success"
    assert sb_execute(mock_builder) == "Success"

def test_sb_execute_api_error():
    """Should catch APIError and return None."""
    mock_builder = MagicMock()
    mock_builder.execute.side_effect = APIError({"message": "Supabase Timeout"})
    assert sb_execute(mock_builder) is None
