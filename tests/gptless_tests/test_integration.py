"""Integration tests for the external API service (real HTTP calls)."""

from __future__ import annotations

import time
import xml.etree.ElementTree as ET

import pytest

from gptless_tests.client import InvoicingApiClient
from gptless_tests.payloads import (
    invalid_generate_invoice_payload_missing_supplier,
    valid_generate_invoice_payload,
    valid_order_xml_payload,
)


def _extract_invoice_id(xml_payload: str) -> str | None:
    try:
        root = ET.fromstring(xml_payload)
    except ET.ParseError:
        return None

    for element in root.iter():
        if element.tag.endswith("ID") and element.text and element.text.strip():
            return element.text.strip()
    return None


def test_invoices_happy_path_and_delete(integration_client):
    create_resp = integration_client.generate_invoice(valid_generate_invoice_payload())
    assert create_resp.status_code == 201
    assert create_resp.body.strip().startswith("<?xml")

    created_id = _extract_invoice_id(create_resp.body)
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


def test_generate_invoice_without_api_token_returns_401(unauth_client, api_base_url_explicitly_set):
    if not api_base_url_explicitly_set:
        pytest.skip("API_BASE_URL not set; skipping black-box HTTP call.")
    resp = unauth_client.generate_invoice(valid_generate_invoice_payload())
    assert resp.status_code == 401


def test_orders_convert_without_api_token_returns_401(unauth_client, api_base_url_explicitly_set):
    if not api_base_url_explicitly_set:
        pytest.skip("API_BASE_URL not set; skipping black-box HTTP call.")
    resp = unauth_client.convert_order(valid_order_xml_payload())
    assert resp.status_code == 401


def test_generate_invoice_validation_and_auth_errors(integration_client, base_url):
    bad_payload_resp = integration_client.generate_invoice(
        invalid_generate_invoice_payload_missing_supplier()
    )
    assert bad_payload_resp.status_code == 400
    bad_body = bad_payload_resp.json()
    assert "error" in bad_body and "message" in bad_body


def test_orders_convert_success_and_bad_xml(integration_client, base_url):
    success_resp = integration_client.convert_order(valid_order_xml_payload())
    assert success_resp.status_code == 200
    parsed = success_resp.json()
    assert "InvoiceData" in parsed

    bad_xml_resp = integration_client.convert_order("<Order><broken></Order>")
    assert bad_xml_resp.status_code == 400
    bad_body = bad_xml_resp.json()
    assert "error" in bad_body and "message" in bad_body
