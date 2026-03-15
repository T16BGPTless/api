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


def test_require_decimal_value_none(invoice_data):
    """totalAmount (or other decimal field) missing → _require_decimal raises (line 49)."""
    data = invoice_data.copy()
    del data["totalAmount"]
    with pytest.raises(ValueError, match="totalAmount is required"):
        build_invoice_xml(data)


def test_require_decimal_invalid_number(invoice_data):
    """Decimal field not a valid number → _require_decimal raises (lines 52-53)."""
    data = invoice_data.copy()
    data["totalAmount"] = "not-a-number"
    with pytest.raises(ValueError, match="totalAmount must be valid number"):
        build_invoice_xml(data)


def test_require_decimal_negative(invoice_data):
    """Negative totalAmount → _require_decimal raises (line 55)."""
    data = invoice_data.copy()
    data["totalAmount"] = -1
    with pytest.raises(ValueError, match="totalAmount must not be negative"):
        build_invoice_xml(data)


def test_build_invoice_xml_invalid_json_string():
    """Pass invalid JSON string → JSONDecodeError path (lines 109-110)."""
    with pytest.raises(ValueError, match="Invoice data must be valid JSON"):
        build_invoice_xml("not valid json {{{")


def test_build_invoice_xml_data_not_dict():
    """Pass non-dict non-string (e.g. list) → line 113."""
    with pytest.raises(ValueError, match="Invoice data must be an object"):
        build_invoice_xml([1, 2, 3])


def test_build_invoice_xml_supplier_not_dict(invoice_data):
    """supplier not a dict → line 127."""
    data = invoice_data.copy()
    data["supplier"] = "not-a-dict"
    with pytest.raises(ValueError, match="supplier must be an object"):
        build_invoice_xml(data)


def test_build_invoice_xml_customer_not_dict(invoice_data):
    """customer not a dict → line 130."""
    data = invoice_data.copy()
    data["customer"] = []
    with pytest.raises(ValueError, match="customer must be an object"):
        build_invoice_xml(data)


def test_build_invoice_xml_lines_not_list_or_empty(invoice_data):
    """lines not a list or empty → line 133."""
    data = invoice_data.copy()
    data["lines"] = []
    with pytest.raises(ValueError, match="lines must be a non-empty array"):
        build_invoice_xml(data)


def test_build_invoice_xml_lines_not_list(invoice_data):
    """lines not a list (e.g. dict) → line 133."""
    data = invoice_data.copy()
    data["lines"] = {}
    with pytest.raises(ValueError, match="lines must be a non-empty array"):
        build_invoice_xml(data)


def test_build_invoice_xml_line_item_not_dict(invoice_data):
    """One line item is not a dict → line 137 (and 169 in second loop)."""
    data = invoice_data.copy()
    data["lines"] = [
        {
            "lineId": "1",
            "description": "item",
            "quantity": 1,
            "unitPrice": 1,
            "lineTotal": 1,
        },
        "not-a-dict",
    ]
    with pytest.raises(ValueError, match="Each line must be an object"):
        build_invoice_xml(data)
