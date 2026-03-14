"""Test the invoice XML builder."""

import json
import pytest
from app.services.invoice_xml import build_invoice_xml


@pytest.fixture
def invoice_data():
    """Base invoice data for tests."""
    return {
        "invoiceID": "123",
        "issueDate": "2026-01-01",
        "dueDate": "2026-01-02",
        "currency": "AUD",
        "totalAmount": 1,
        "supplier": {"name": "invoice name", "ABN": "123"},
        "customer": {"name": "customer name", "ABN": "456"},
        "lines": [
            {
                "lineId": "1",
                "description": "item",
                "quantity": 1,
                "unitPrice": 1,
                "lineTotal": 1,
            }
        ],
    }


def test_build_invoice_xml_success(invoice_data):
    """Test the invoice XML builder success."""
    xml = build_invoice_xml(json.dumps(invoice_data))

    assert "<cbc:ID>123</cbc:ID>" in xml
    assert "invoice name" in xml
    assert "customer name" in xml


def test_total_must_match_lines(invoice_data):
    """Test the invoice XML builder total must match lines."""
    data = invoice_data.copy()
    data["totalAmount"] = 2

    with pytest.raises(ValueError):
        build_invoice_xml(json.dumps(data))


def test_missing_invoice_id(invoice_data):
    """Test the invoice XML builder missing invoice ID."""
    data = invoice_data.copy()
    del data["invoiceID"]

    with pytest.raises(ValueError):
        build_invoice_xml(json.dumps(data))


def test_invoices_template(invoice_data):
    """Test the invoice XML builder invoices template."""
    data = invoice_data.copy()
    data["invoiceID"] = "456"
    data["issueDate"] = "2026-02-01"
    data["dueDate"] = "2026-02-02"
    data["totalAmount"] = 5
    data["supplier"] = {"name": "template supplier", "ABN": "111"}
    data["customer"] = {"name": "template customer", "ABN": "222"}
    data["lines"] = [
        {
            "lineId": "1",
            "description": "template item",
            "quantity": 1,
            "unitPrice": 5,
            "lineTotal": 5,
        }
    ]

    xml = build_invoice_xml(json.dumps(data))

    assert "<cbc:ID>456</cbc:ID>" in xml
    assert "template supplier" in xml
    assert "template customer" in xml
    assert "template item" in xml