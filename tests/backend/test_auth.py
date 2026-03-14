"""Auth route tests."""

import os
from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from app.app import app


@pytest.fixture
def valid_dev_token():
    """Token from VALID_DEV_TOKENS env (required for tests that call protected routes)."""
    raw = os.environ.get("VALID_DEV_TOKENS", "").strip()
    token = raw.split(",")[0].strip() if raw else ""
    if not token:
        pytest.skip(
            "VALID_DEV_TOKENS not set (set in CI via secrets or in .env locally)"
        )
    return token


@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class MockResponse:
    """Helper to simulate Supabase response objects."""

    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error


# ------------------------------ register ------------------------------


def test_register_success(client, valid_dev_token):
    """Happy path: new group is created and APItoken is returned."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[])
    created_resp = MockResponse(data=[{"api_token": "new-token"}])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", side_effect=[existing_resp, created_resp]),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.post(
            "/v1/auth/register",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.CREATED
    body = resp.get_json()
    assert "APItoken" in body
    assert isinstance(body["APItoken"], str) and body["APItoken"]


def test_register_missing_dev_token(client):
    """Missing APIdevToken header returns 401."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.post("/v1/auth/register", json={"groupName": "grp"})

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_register_forbidden_dev_token(client):
    """Invalid dev token returns 403."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.post(
            "/v1/auth/register",
            json={"groupName": "grp"},
            headers={"APIdevToken": "not-allowed"},
        )

    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_register_group_name_required(client, valid_dev_token):
    """Missing groupName returns 400."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.post(
            "/v1/auth/register",
            json={},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_register_group_already_registered(client, valid_dev_token):
    """Existing groupName returns 409."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[{"api_token": "existing"}])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", return_value=existing_resp),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.post(
            "/v1/auth/register",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.CONFLICT


def test_register_db_error_on_lookup(client, valid_dev_token):
    """If sb_execute(None) or error on lookup, return 500."""
    mock_supabase = MagicMock()

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", return_value=None),
    ):
        resp = client.post(
            "/v1/auth/register",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_register_get_db_failure(client, valid_dev_token):
    """If get_db returns None, return 500."""
    with patch("app.routes.helpers.get_db", return_value=None):
        resp = client.post(
            "/v1/auth/register",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_register_db_error_on_insert(client, valid_dev_token):
    """If insert sb_execute fails, return 500."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        # First call: lookup ok; second call: insert fails
        patch("app.routes.auth.sb_execute", side_effect=[existing_resp, None]),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.post(
            "/v1/auth/register",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# ------------------------------ reset ------------------------------


def test_reset_success(client, valid_dev_token):
    """Happy path: existing group gets a new token."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[{"api_token": "old-token"}])
    update_resp = MockResponse(data=[{"api_token": "new-token"}])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", side_effect=[existing_resp, update_resp]),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.put(
            "/v1/auth/reset",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.OK
    body = resp.get_json()
    assert "APItoken" in body
    assert body["APItoken"] != "old-token"


def test_reset_group_not_found(client, valid_dev_token):
    """Reset for unknown group returns 404."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", return_value=existing_resp),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.put(
            "/v1/auth/reset",
            json={"groupName": "missing"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_reset_get_db_failure(client, valid_dev_token):
    """If get_db() returns None for reset, return 500."""
    with patch("app.routes.helpers.get_db", return_value=None):
        resp = client.put(
            "/v1/auth/reset",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_reset_missing_dev_token(client):
    """Missing APIdevToken on reset returns 401."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.put("/v1/auth/reset", json={"groupName": "grp"})

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_reset_forbidden_dev_token(client):
    """Invalid dev token on reset returns 403."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.put(
            "/v1/auth/reset",
            json={"groupName": "grp"},
            headers={"APIdevToken": "not-allowed"},
        )

    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_reset_group_name_required(client, valid_dev_token):
    """Missing groupName on reset returns 400."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.put(
            "/v1/auth/reset",
            json={},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_reset_db_error_on_lookup(client, valid_dev_token):
    """If initial lookup in reset fails, return 500."""
    mock_supabase = MagicMock()

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", return_value=None),
    ):
        resp = client.put(
            "/v1/auth/reset",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_reset_db_error_on_update(client, valid_dev_token):
    """If update sb_execute fails in reset, return 500."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[{"api_token": "old"}])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", side_effect=[existing_resp, None]),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.put(
            "/v1/auth/reset",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# ------------------------------ revoke ------------------------------


def test_revoke_success(client, valid_dev_token):
    """Happy path: token is nulled and previous token is returned."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[{"api_token": "old-token"}])
    update_resp = MockResponse(data=[{"api_token": None}])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", side_effect=[existing_resp, update_resp]),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.delete(
            "/v1/auth/revoke",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.NO_CONTENT


def test_revoke_group_not_found(client, valid_dev_token):
    """Revoke for unknown group returns 404."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", return_value=existing_resp),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.delete(
            "/v1/auth/revoke",
            json={"groupName": "missing"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_revoke_get_db_failure(client, valid_dev_token):
    """If get_db() returns None for revoke, return 500."""
    with patch("app.routes.helpers.get_db", return_value=None):
        resp = client.delete(
            "/v1/auth/revoke",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_revoke_missing_dev_token(client):
    """Missing APIdevToken on revoke returns 401."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.delete("/v1/auth/revoke", json={"groupName": "grp"})

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_revoke_forbidden_dev_token(client):
    """Invalid dev token on revoke returns 403."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.delete(
            "/v1/auth/revoke",
            json={"groupName": "grp"},
            headers={"APIdevToken": "not-allowed"},
        )

    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_revoke_group_name_required(client, valid_dev_token):
    """Missing groupName on revoke returns 400."""
    with patch("app.routes.helpers.get_db", return_value=MagicMock()):
        resp = client.delete(
            "/v1/auth/revoke",
            json={},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.BAD_REQUEST


def test_revoke_db_error_on_lookup(client, valid_dev_token):
    """If initial lookup in revoke fails, return 500."""
    mock_supabase = MagicMock()

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", return_value=None),
    ):
        resp = client.delete(
            "/v1/auth/revoke",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


def test_revoke_db_error_on_update(client, valid_dev_token):
    """If delete sb_execute fails in revoke, return 500."""
    mock_supabase = MagicMock()
    existing_resp = MockResponse(data=[{"api_token": "old"}])

    with (
        patch("app.routes.helpers.get_db", return_value=mock_supabase),
        patch("app.routes.auth.sb_execute", side_effect=[existing_resp, None]),
        patch("app.routes.auth.sb_has_error", return_value=False),
    ):
        resp = client.delete(
            "/v1/auth/revoke",
            json={"groupName": "my-group"},
            headers={"APIdevToken": valid_dev_token},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
