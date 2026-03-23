"""Unit tests for black-box client behavior with mocked transport."""

from __future__ import annotations

import pytest

from gptless_tests.client import ApiResponse
from gptless_tests.payloads import (
    invalid_generate_invoice_payload_missing_supplier,
    valid_generate_invoice_payload,
    valid_order_xml_payload
)

def _mock_request(monkeypatch, client, expected):
    captured = {}

    def fake_request(method, path, *, headers=None, body=None):
        captured["method"] = method
        captured["path"] = path
        captured["headers"] = headers or {}
        captured["body"] = body
        return ApiResponse(**expected)

    monkeypatch.setattr(client, "_request", fake_request)
    return captured


def test_generate_invoice_builds_expected_request(unit_client, monkeypatch):
    captured = _mock_request(
        monkeypatch,
        unit_client,
        {
            "status_code": 201,
            "headers": {"Content-Type": "application/xml"},
            "body": "<Invoice><cbc:ID>1</cbc:ID></Invoice>",
        },
    )

    resp = unit_client.generate_invoice(valid_generate_invoice_payload())

    assert resp.status_code == 201
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/invoices/generate"
    assert captured["headers"]["APItoken"] == "api-token"
    assert captured["headers"]["Accept"] == "application/xml"
    assert '"InvoiceData"' in captured["body"]


def test_list_invoices_builds_expected_request(unit_client, monkeypatch):
    captured = _mock_request(
        monkeypatch,
        unit_client,
        {"status_code": 200, "headers": {"Content-Type": "application/json"}, "body": "[1,2,3]"},
    )

    resp = unit_client.list_invoices()

    assert resp.status_code == 200
    assert resp.json() == [1, 2, 3]
    assert captured["method"] == "GET"
    assert captured["path"] == "/v1/invoices"
    assert captured["headers"]["APItoken"] == "api-token"


def test_convert_order_builds_expected_xml_request(unit_client, monkeypatch):
    captured = _mock_request(
        monkeypatch,
        unit_client,
        {
            "status_code": 200,
            "headers": {"Content-Type": "application/json"},
            "body": '{"InvoiceData": {"currency": "GBP"}}',
        },
    )

    resp = unit_client.convert_order(valid_order_xml_payload())

    assert resp.status_code == 200
    assert "InvoiceData" in resp.json()
    assert captured["method"] == "POST"
    assert captured["path"] == "/v1/orders/convert"
    assert captured["headers"]["Content-Type"] == "application/xml"
    assert captured["headers"]["APItoken"] == "api-token"
    assert captured["body"].startswith("<?xml")


@pytest.mark.parametrize(
    ("status_code", "error_code"),
    [
        (400, "BAD_REQUEST"),
        (401, "UNAUTHORIZED"),
        (403, "FORBIDDEN"),
        (404, "NOT_FOUND"),
        (500, "INTERNAL_SERVER_ERROR"),
    ],
)
def test_generate_invoice_error_mapping_shape(
    unit_client, monkeypatch, status_code, error_code
):
    _mock_request(
        monkeypatch,
        unit_client,
        {
            "status_code": status_code,
            "headers": {"Content-Type": "application/json"},
            "body": f'{{"error":"{error_code}","message":"x"}}',
        },
    )

    resp = unit_client.generate_invoice(invalid_generate_invoice_payload_missing_supplier())
    body = resp.json()

    assert resp.status_code == status_code
    assert body["error"] == error_code
    assert "message" in body
