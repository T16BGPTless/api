import pytest
from app.services.invoice_xml import build_invoice_xml


def test_build_invoice_xml_success():
    data = {
        "invoiceID": "123",
        "issueDate": "2026-01-01",
        "dueDate": "2026-01-02",
        "currency": "AUD",
        "totalAmount": 1,
        "supplier": {
            "name": "invoice name",
            "ABN": "123"
        },
        "customer": {
            "name": "customer name",
            "ABN": "456"
        },
        "lines": [
            {
                "lineId": "1",
                "description": "item",
                "quantity": 1,
                "unitPrice": 1,
                "lineTotal": 1
            }
        ]
    }

    xml = build_invoice_xml(data)

    assert "<cbc:ID>123</cbc:ID>" in xml
    assert "invoice name" in xml
    assert "customer name" in xml


def test_total_must_match_lines():
    data = {
        "invoiceID": "123",
        "issueDate": "2026-01-01",
        "dueDate": "2026-01-02",
        "currency": "AUD",
        "totalAmount": 2,
        "supplier": {"name": "invoice name", "ABN": "123"},
        "customer": {"name": "customer name", "ABN": "456"},
        "lines": [
            {
                "lineId": "1",
                "description": "item",
                "quantity": 1,
                "unitPrice": 1,
                "lineTotal": 1
            }
        ]
    }

    with pytest.raises(ValueError):
        build_invoice_xml(data)


def test_missing_invoice_id():
    data = {
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
                "lineTotal": 1
            }
        ]
    }

    with pytest.raises(ValueError):
        build_invoice_xml(data)

def test_invoices_template():
    data = {
        "invoiceID": "456",
        "issueDate": "2026-02-01",
        "dueDate": "2026-02-02",
        "currency": "AUD",
        "totalAmount": 5,
        "supplier": {
            "name": "template supplier",
            "ABN": "111"
        },
        "customer": {
            "name": "template customer",
            "ABN": "222"
        },
        "lines": [
            {
                "lineId": "1",
                "description": "template item",
                "quantity": 1,
                "unitPrice": 5,
                "lineTotal": 5
            }
        ]
    }

    xml = build_invoice_xml(data)

    assert "<cbc:ID>456</cbc:ID>" in xml
    assert "template supplier" in xml
    assert "template customer" in xml
    assert "template item" in xml