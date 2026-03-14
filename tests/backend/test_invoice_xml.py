"""Test the invoice XML builder."""

import pytest

from app.services.invoice_xml import build_invoice_xml


def _base_invoice(**overrides):
    """Return a baseline valid invoice dict, optionally overridden."""
    data = {
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
    data.update(overrides)
    return data


def test_build_invoice_xml_success():
    """Happy path: builds XML with expected content."""
    xml = build_invoice_xml(_base_invoice())

    assert "<cbc:ID>123</cbc:ID>" in xml
    assert "invoice name" in xml
    assert "customer name" in xml


def test_total_must_match_lines():
    """overalltotal must equal sum of line totals."""
    bad = _base_invoice(totalAmount=2)

    with pytest.raises(ValueError, match="overalltotal must equal sum"):
        build_invoice_xml(bad)


def test_missing_invoice_id():
    """invoiceID is required (via _require_string)."""
    bad = _base_invoice()
    bad.pop("invoiceID", None)

    with pytest.raises(ValueError, match="invoiceID is required"):
        build_invoice_xml(bad)


def test_invoices_template():
    """Another happy-path example with different values."""
    xml = build_invoice_xml(
        _base_invoice(
            invoiceID="456",
            totalAmount=5,
            supplier={"name": "template supplier", "ABN": "111"},
            customer={"name": "template customer", "ABN": "222"},
            lines=[
                {
                    "lineId": "1",
                    "description": "template item",
                    "quantity": 1,
                    "unitPrice": 5,
                    "lineTotal": 5,
                }
            ],
        )
    )

    assert "<cbc:ID>456</cbc:ID>" in xml
    assert "template supplier" in xml
    assert "template customer" in xml
    assert "template item" in xml


# ---------------------- _require_decimal branches ----------------------


def test_total_amount_required():
    """totalAmount is required (value is None)."""
    bad = _base_invoice(totalAmount=None)

    with pytest.raises(ValueError, match="totalAmount is required"):
        build_invoice_xml(bad)


def test_total_amount_must_be_valid_number():
    """totalAmount must be a valid number (invalid string)."""
    bad = _base_invoice(totalAmount="not-a-number")

    with pytest.raises(ValueError, match="totalAmount must be valid number"):
        build_invoice_xml(bad)


def test_total_amount_must_not_be_negative():
    """totalAmount must not be negative."""
    bad = _base_invoice(totalAmount=-1)

    with pytest.raises(ValueError, match="totalAmount must not be negative"):
        build_invoice_xml(bad)


# ---------------------- build_invoice_xml guards ----------------------


def test_invoice_data_must_be_object():
    """Top-level data must be a dict."""
    with pytest.raises(ValueError, match="Invoice data must be an object"):
        build_invoice_xml("not-a-dict")  # type: ignore[arg-type]


def test_supplier_must_be_object():
    """supplier must be an object (dict)."""
    bad = _base_invoice(supplier="not-a-dict")

    with pytest.raises(ValueError, match="supplier must be an object"):
        build_invoice_xml(bad)


def test_customer_must_be_object():
    """customer must be an object (dict)."""
    bad = _base_invoice(customer=["not-dict"])

    with pytest.raises(ValueError, match="customer must be an object"):
        build_invoice_xml(bad)


def test_lines_must_be_non_empty_array():
    """lines must be a non-empty list."""
    bad_empty = _base_invoice(lines=[])
    with pytest.raises(ValueError, match="lines must be a non-empty array"):
        build_invoice_xml(bad_empty)

    bad_not_list = _base_invoice(lines="not-a-list")
    with pytest.raises(ValueError, match="lines must be a non-empty array"):
        build_invoice_xml(bad_not_list)


def test_each_line_must_be_object_in_validation_loop():
    """Each line must be a dict during initial validation loop."""
    bad = _base_invoice(
        lines=[
            {
                "lineId": "1",
                "description": "ok",
                "quantity": 1,
                "unitPrice": 1,
                "lineTotal": 1,
            },
            123,  # which is not a dict
        ]
    )

    with pytest.raises(ValueError, match="Each line must be an object"):
        build_invoice_xml(bad)


def test_each_line_must_be_object_in_render_loop():
    """Second 'Each line must be an object' guard (render loop)."""

    class WeirdLines(list):
        """Iterates with a dict first, then a non-dict on second pass."""

        def __iter__(self):
            count = getattr(self, "_count", 0)
            self._count = count + 1
            # First two iterations (validation loop + line_sum) see a valid dict.
            if count < 2:
                return iter(
                    [
                        {
                            "lineId": "1",
                            "description": "ok",
                            "quantity": 1,
                            "unitPrice": 1,
                            "lineTotal": 1,
                        }
                    ]
                )
            # Third iteration (render loop) sees a non-dict and should trigger the guard.
            return iter([123])

    lines = WeirdLines()
    lines.append(
        {
            "lineId": "1",
            "description": "ok",
            "quantity": 1,
            "unitPrice": 1,
            "lineTotal": 1,
        }
    )

    bad = _base_invoice(totalAmount=1, lines=lines)

    with pytest.raises(ValueError, match="Each line must be an object"):
        build_invoice_xml(bad)
