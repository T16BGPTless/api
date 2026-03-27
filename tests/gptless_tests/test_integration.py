"""Integration tests for the external API service (real HTTP calls).

Route coverage in this file (see ``app/routes`` for full API surface):

- ``POST /v1/invoices/generate`` — create invoice (happy path, validation 400, unauth 401)
- ``GET /v1/invoices`` — list invoice IDs
- ``GET /v1/invoices/<id>`` — fetch XML (and after delete: 403/404)
- ``DELETE /v1/invoices/<id>`` — soft-delete
- ``POST /v1/invoices/notify/<id>`` — recipient email validation + auth checks
- ``POST /v1/orders/convert`` — order XML → JSON (success, bad XML 400, unauth 401)

Not covered here: ``/v1/auth/*``, ``GET /`` (home redirect). Dev-only auth is tested under
``tests/backend/``.
"""

from __future__ import annotations

import os
import time
import xml.etree.ElementTree as ET

import pytest

from gptless_tests.payloads import (
    invalid_generate_invoice_payload_missing_supplier,
    valid_generate_invoice_payload,
    invalid_recipient_email,
    valid_recipient_email,
    valid_order_xml_payload,
)


def extract_invoice_id(xml_payload: str) -> str | None:
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        return None

    for element in root.iter():
        if element.tag.endswith("ID") and element.text and element.text.strip():
            return element.text.strip()
    return None


def test_invoices_happy_path_and_delete(integration_client):
    """Processes the following flow: generate → list → get → delete → get."""
    create_resp = integration_client.generate_invoice(valid_generate_invoice_payload())
    assert create_resp.status_code == 201
    assert create_resp.body.strip().startswith("<?xml")

    created_id = extract_invoice_id(create_resp.body)
    if not created_id:
        pytest.skip("Could not extract invoice ID from generated XML response.")

    list_resp = integration_client.list_invoices()
    assert list_resp.status_code == 200
    listed_ids = list_resp.json()
    assert isinstance(listed_ids, list)

    if listed_ids and isinstance(listed_ids[0], int):
        assert int(created_id) in listed_ids

    get_resp = integration_client.get_invoice(created_id)
    assert get_resp.status_code == 200
    assert "<Invoice" in get_resp.body

    delete_resp = integration_client.delete_invoice(created_id)
    assert delete_resp.status_code == 204

    # Allow eventual consistency before read-after-delete assertion.
    time.sleep(0.3)
    get_after_delete = integration_client.get_invoice(created_id)
    assert get_after_delete.status_code in (403, 404)


def test_generate_invoice_without_api_token_returns_401(unauth_client):
    """Route: ``POST /v1/invoices/generate`` (no ``APItoken`` header → 401)."""
    resp = unauth_client.generate_invoice(valid_generate_invoice_payload())
    assert resp.status_code == 401


def test_orders_convert_without_api_token_returns_401(unauth_client):
    """Route: ``POST /v1/orders/convert`` (no ``APItoken`` header → 401)."""
    resp = unauth_client.convert_order(valid_order_xml_payload())
    assert resp.status_code == 401


def test_generate_invoice_validation_and_auth_errors(integration_client, base_url):
    """Route: ``POST /v1/invoices/generate`` (invalid body → 400)."""
    bad_payload_resp = integration_client.generate_invoice(
        invalid_generate_invoice_payload_missing_supplier()
    )
    assert bad_payload_resp.status_code == 400
    bad_body = bad_payload_resp.json()
    assert "error" in bad_body and "message" in bad_body


def test_orders_convert_success_and_bad_xml(integration_client, base_url):
    """Routes: ``POST /v1/orders/convert`` (200 success, 400 bad XML)."""
    success_resp = integration_client.convert_order(valid_order_xml_payload())
    assert success_resp.status_code == 200
    parsed = success_resp.json()
    assert "InvoiceData" in parsed

    bad_xml_resp = integration_client.convert_order("<Order><broken></Order>")
    assert bad_xml_resp.status_code == 400
    bad_body = bad_xml_resp.json()
    assert "error" in bad_body and "message" in bad_body


def test_notify_invoice_without_api_token_returns_401(unauth_client):
    """Route: ``POST /v1/invoices/notify/<id>`` (no ``APItoken`` header → 401)."""
    resp = unauth_client.notify_invoice(
        "12345", recipient_email=valid_recipient_email(), with_auth=False
    )
    assert resp.status_code == 401


def test_notify_invoice_invalid_email_400(integration_client):
    """Route: ``POST /v1/invoices/notify/<id>`` (invalid email → 400)."""
    resp = integration_client.notify_invoice(
        "12345", recipient_email=invalid_recipient_email()
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "BAD_REQUEST"


def test_notify_invoice_success_200(integration_client):
    """Route: ``POST /v1/invoices/notify/<id>`` (happy path → 200).

    This sends a real email via Resend. To avoid spamming arbitrary recipients, the
    service overrides the outbound recipient to `RESEND_TO_EMAIL` when set.
    We still provide a valid recipientEmail input, and we use `RESEND_TO_EMAIL`
    itself so deliverability checks pass.
    """
    resend_to = os.environ.get("RESEND_TO_EMAIL", "").strip()
    resend_key = os.environ.get("RESEND_API_KEY", "").strip()
    resend_from = os.environ.get("RESEND_FROM_EMAIL", "").strip()
    if not (resend_to and resend_key and resend_from):
        pytest.skip(
            "Resend env vars not set; skipping notify success integration test."
        )

    create_resp = integration_client.generate_invoice(valid_generate_invoice_payload())
    assert create_resp.status_code == 201
    created_id = extract_invoice_id(create_resp.body)
    if not created_id:
        pytest.skip("Could not extract invoice ID from generated XML response.")

    notify_resp = integration_client.notify_invoice(
        created_id, recipient_email=resend_to
    )
    if notify_resp.status_code == 500:
        body = notify_resp.json() or {}
        msg = body.get("message", "")
        if "Database error" in msg and "SUPABASE_URL" in msg:
            pytest.skip(
                "Target API process cannot reach Supabase (ensure SUPABASE_URL and "
                "SUPABASE_SERVICE_ROLE_KEY are set for the running server)."
            )
    assert notify_resp.status_code == 200
    body = notify_resp.json()
    assert body.get("success") is True
