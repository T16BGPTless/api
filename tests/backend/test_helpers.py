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

