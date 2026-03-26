"""Notify invoice route tests (unit-style with mocked dependencies)."""

from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock, patch

import pytest

from app.app import app


@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class MockResponse:
    """Helper class to simulate Supabase response objects."""

    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error


def test_notify_invoice_success_200(client):
    invoice_id = 12345
    xml = "<Invoice><ID>12345</ID></Invoice>"

    with (
        patch("app.routes.invoices.is_valid_email", return_value=True),
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.get_group_id_from_token", return_value=(10, None)),
        patch(
            "app.routes.invoices.sb_execute",
            return_value=MockResponse(
                data=[{"owner_token": 10, "xml": xml, "deleted": False}]
            ),
        ),
        patch(
            "app.routes.invoices.convert_invoice_xml_to_pdf",
            return_value=b"%PDF-FAKE%",
        ),
        patch("app.routes.invoices.send_invoice_notification", return_value=None),
    ):
        resp = client.post(
            f"/v1/invoices/notify/{invoice_id}",
            json={"recipientEmail": "accounts@example.com"},
            headers={"APItoken": "valid-token"},
        )

    assert resp.status_code == HTTPStatus.OK
    assert resp.get_json()["success"] is True


def test_notify_invoice_invalid_email_400(client):
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
    ):
        resp = client.post(
            "/v1/invoices/notify/12345",
            json={"recipientEmail": "not-an-email"},
            headers={"APItoken": "valid-token"},
        )

    assert resp.status_code == HTTPStatus.BAD_REQUEST
    body = resp.get_json()
    assert body["error"] == "BAD_REQUEST"


def test_notify_invoice_missing_api_token_401(client):
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
    ):
        resp = client.post(
            "/v1/invoices/notify/12345",
            json={"recipientEmail": "accounts@example.com"},
        )

    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_notify_invoice_not_found_404(client):
    with (
        patch("app.routes.invoices.is_valid_email", return_value=True),
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.get_group_id_from_token", return_value=(10, None)),
        patch("app.routes.invoices.sb_execute", return_value=MockResponse(data=[])),
    ):
        resp = client.post(
            "/v1/invoices/notify/12345",
            json={"recipientEmail": "accounts@example.com"},
            headers={"APItoken": "valid-token"},
        )

    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.get_json()["error"] == "NOT_FOUND"


def test_notify_invoice_wrong_owner_403(client):
    with (
        patch("app.routes.invoices.is_valid_email", return_value=True),
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.get_group_id_from_token", return_value=(10, None)),
        patch(
            "app.routes.invoices.sb_execute",
            return_value=MockResponse(
                data=[{"owner_token": 999, "xml": "<Invoice/>", "deleted": False}]
            ),
        ),
    ):
        resp = client.post(
            "/v1/invoices/notify/12345",
            json={"recipientEmail": "accounts@example.com"},
            headers={"APItoken": "valid-token"},
        )

    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert resp.get_json()["error"] == "FORBIDDEN"


def test_notify_invoice_conversion_failure_500(client):
    with (
        patch("app.routes.invoices.is_valid_email", return_value=True),
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.get_group_id_from_token", return_value=(10, None)),
        patch(
            "app.routes.invoices.sb_execute",
            return_value=MockResponse(
                data=[{"owner_token": 10, "xml": "<Invoice/>", "deleted": False}]
            ),
        ),
        patch(
            "app.routes.invoices.convert_invoice_xml_to_pdf",
            side_effect=RuntimeError("CloudConvert failure"),
        ),
    ):
        resp = client.post(
            "/v1/invoices/notify/12345",
            json={"recipientEmail": "accounts@example.com"},
            headers={"APItoken": "valid-token"},
        )

    assert resp.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert resp.get_json()["error"] == "INTERNAL_SERVER_ERROR"

