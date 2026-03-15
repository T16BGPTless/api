"""Unit tests for order_to_invoice module (coverage for helpers and edge cases)."""

import pytest

from app.services.order_to_invoice import (
    _decimal,
    _first,
    _order_line_to_invoice_line,
    _party_to_supplier_customer,
    _text,
    order_json_to_invoice_data,
)


# ------------------- _first -------------------


def test_first_returns_none_when_not_dict():
    """_first returns None when first arg is not a dict (line 9)."""
    assert _first(None, "a") is None
    assert _first([], "a") is None
    assert _first("x", "a") is None


def test_first_returns_value_when_key_present():
    """_first returns d[k] when key is in d (line 13)."""
    assert _first({"a": 1, "b": 2}, "a") == 1
    assert _first({"cbc:ID": "x"}, "cbc:ID") == "x"
    assert _first({"Order": {"x": 1}}, "Order") == {"x": 1}


def test_first_returns_none_when_no_key_match():
    """_first returns None when no key in keys is in d."""
    assert _first({"a": 1}, "b", "c") is None


# ------------------- _text -------------------


def test_text_dict_with_text_key():
    """_text returns stripped #text or value from dict (line 19)."""
    assert _text({"#text": "  foo  "}) == "foo"
    assert _text({"value": "bar"}) == "bar"
    assert _text({"#text": "x", "value": "y"}) == "x"


def test_text_none_returns_empty():
    """_text returns empty string for None (line 18)."""
    assert _text(None) == ""


def test_text_non_dict_returns_stripped_str():
    """_text returns str(val).strip() for non-dict (line 21)."""
    assert _text("  hi  ") == "hi"
    assert _text(42) == "42"


# ------------------- _decimal -------------------


def test_decimal_none_returns_zero():
    """_decimal returns Decimal('0') when val is None (line 28)."""
    assert _decimal(None) == 0


def test_decimal_valid_string():
    """_decimal parses valid string (line 32)."""
    assert _decimal("10.5") == 10.5
    assert _decimal("0") == 0


def test_decimal_invalid_returns_zero():
    """_decimal returns Decimal('0') on parse error (line 32-33 except)."""
    assert _decimal("not-a-number") == 0
    assert _decimal({"#text": "bad"}) == 0


def test_decimal_dict_with_text():
    """_decimal uses _text when val is dict (line 29)."""
    assert float(_decimal({"#text": "3.14"})) == 3.14


def test_decimal_empty_string_returns_zero():
    """_decimal returns 0 when s is empty (line 32)."""
    assert _decimal("") == 0


# ------------------- _party_to_supplier_customer -------------------


def test_party_none_or_not_dict_returns_unknown():
    """_party_to_supplier_customer returns Unknown when party is None or not dict (line 39)."""
    assert _party_to_supplier_customer(None) == {
        "name": "Unknown",
        "ABN": "00000000000",
    }
    assert _party_to_supplier_customer([]) == {"name": "Unknown", "ABN": "00000000000"}
    assert _party_to_supplier_customer("x") == {"name": "Unknown", "ABN": "00000000000"}


def test_party_with_nested_cac_party():
    """_party extracts name and ABN from nested cac:Party structure."""
    party = {
        "cac:Party": {
            "cac:PartyName": {"cbc:Name": "Acme"},
            "cac:PartyTaxScheme": {"cbc:CompanyID": "12 345 678"},
        }
    }
    assert _party_to_supplier_customer(party) == {"name": "Acme", "ABN": "12 345 678"}


def test_party_missing_name_uses_unknown():
    """_party uses Unknown when name is missing (line 43)."""
    party = {"cac:Party": {"cac:PartyTaxScheme": {"cbc:CompanyID": "123"}}}
    assert _party_to_supplier_customer(party)["name"] == "Unknown"


def test_party_missing_tax_uses_default_abn():
    """_party uses 00000000000 when CompanyID missing (line 47)."""
    party = {"cac:Party": {"cac:PartyName": {"cbc:Name": "X"}}}
    assert _party_to_supplier_customer(party)["ABN"] == "00000000000"


# ------------------- _order_line_to_invoice_line -------------------


def test_order_line_none_or_not_dict_returns_none():
    """_order_line_to_invoice_line returns None when input is None or not dict (line 55)."""
    assert _order_line_to_invoice_line(None) is None
    assert _order_line_to_invoice_line([]) is None
    assert _order_line_to_invoice_line("x") is None


def test_order_line_qty_zero_forced_to_one():
    """_order_line_to_invoice_line uses qty 1 when quantity <= 0 (line 61)."""
    line = {
        "cac:LineItem": {
            "cbc:ID": "1",
            "cbc:Quantity": "0",
            "cbc:LineExtensionAmount": "50.00",
            "cac:Item": {"cbc:Description": "Item"},
        }
    }
    result = _order_line_to_invoice_line(line)
    assert result["quantity"] == 1
    assert result["lineTotal"] == 50


def test_order_line_extension_amount_not_dict():
    """_order_line uses _decimal(ext_el) when ext_el is not dict (line 66)."""
    line = {
        "cac:LineItem": {
            "cbc:ID": "1",
            "cbc:Quantity": "2",
            "cbc:LineExtensionAmount": "100.00",
            "cac:Item": {"cbc:Description": "Thing"},
        }
    }
    result = _order_line_to_invoice_line(line)
    assert result["lineTotal"] == 100


def test_order_line_extension_amount_dict_with_text():
    """_order_line uses dict #text for line total when ext_el is dict (line 63-64)."""
    line = {
        "cac:LineItem": {
            "cbc:ID": "1",
            "cbc:Quantity": "1",
            "cbc:LineExtensionAmount": {"#text": "25.50"},
            "cac:Item": {"cbc:Description": "X"},
        }
    }
    result = _order_line_to_invoice_line(line)
    assert result["lineTotal"] == 25.5


def test_order_line_unit_price_from_price_amount():
    """_order_line uses PriceAmount when present and > 0 (line 71-72)."""
    line = {
        "cac:LineItem": {
            "cbc:ID": "1",
            "cbc:Quantity": "2",
            "cbc:LineExtensionAmount": "100",
            "cac:Price": {"cbc:PriceAmount": "75.00"},
            "cac:Item": {"cbc:Description": "Widget"},
        }
    }
    result = _order_line_to_invoice_line(line)
    assert result["unitPrice"] == 75
    assert result["lineTotal"] == 100


# ------------------- order_json_to_invoice_data -------------------


def test_order_json_root_via_fallback_when_not_order_key():
    """order_json_to_invoice_data finds root via values() when key is not 'Order' (lines 107-112)."""
    order = {
        "urn:some:Order": {
            "cbc:IssueDate": "2021-01-15",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {
                "cbc:PayableAmount": {"#text": "10", "@currencyID": "AUD"}
            },
            "cac:OrderLine": {
                "cac:LineItem": {
                    "cbc:ID": "1",
                    "cbc:Quantity": "1",
                    "cbc:LineExtensionAmount": "10",
                    "cac:Item": {"cbc:Description": "D"},
                }
            },
        }
    }
    data = order_json_to_invoice_data(order)
    assert data["issueDate"] == "2021-01-15"
    assert data["totalAmount"] == "10"
    assert len(data["lines"]) == 1


def test_order_json_raises_when_no_order_root():
    """order_json_to_invoice_data raises ValueError when no Order root (line 114)."""
    with pytest.raises(ValueError, match="Order JSON must contain an Order root"):
        order_json_to_invoice_data({})
    with pytest.raises(ValueError, match="Order JSON must contain an Order root"):
        order_json_to_invoice_data({"x": "y"})
    with pytest.raises(ValueError, match="Order JSON must contain an Order root"):
        order_json_to_invoice_data({"Order": "not a dict"})


def test_order_json_payable_amount_scalar():
    """order_json_to_invoice_data handles PayableAmount as scalar (line 131)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {"cbc:PayableAmount": "99.99"},
            "cac:OrderLine": {
                "cac:LineItem": {
                    "cbc:ID": "1",
                    "cbc:Quantity": "1",
                    "cbc:LineExtensionAmount": "99.99",
                    "cac:Item": {"cbc:Description": "D"},
                }
            },
        }
    }
    data = order_json_to_invoice_data(order)
    assert data["totalAmount"] == "99.99"


def test_order_json_total_from_line_extension_when_payable_zero():
    """order_json uses LineExtensionAmount when total_amount == 0 (lines 133-137)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {
                "cbc:PayableAmount": "0",
                "cbc:LineExtensionAmount": {"#text": "50.00"},
            },
            "cac:OrderLine": {
                "cac:LineItem": {
                    "cbc:ID": "1",
                    "cbc:Quantity": "1",
                    "cbc:LineExtensionAmount": "50.00",
                    "cac:Item": {"cbc:Description": "D"},
                }
            },
        }
    }
    data = order_json_to_invoice_data(order)
    assert float(data["totalAmount"]) == 50.0


def test_order_json_total_from_line_extension_scalar():
    """order_json LineExtensionAmount as scalar when total_amount == 0 (line 135)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {
                "cbc:PayableAmount": {"#text": "0"},
                "cbc:LineExtensionAmount": "33.33",
            },
            "cac:OrderLine": {
                "cac:LineItem": {
                    "cbc:ID": "1",
                    "cbc:Quantity": "1",
                    "cbc:LineExtensionAmount": "33.33",
                    "cac:Item": {"cbc:Description": "D"},
                }
            },
        }
    }
    data = order_json_to_invoice_data(order)
    assert float(data["totalAmount"]) == 33.33


def test_order_json_currency_empty_fallback():
    """order_json uses AUD when currency is empty (lines 139, 136)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {
                "cbc:PayableAmount": {"#text": "1", "@currencyID": ""}
            },
            "cac:OrderLine": {
                "cac:LineItem": {
                    "cbc:ID": "1",
                    "cbc:Quantity": "1",
                    "cbc:LineExtensionAmount": "1",
                    "cac:Item": {"cbc:Description": "D"},
                }
            },
        }
    }
    data = order_json_to_invoice_data(order)
    assert data["currency"] == "AUD"


def test_order_json_order_lines_none():
    """order_json treats missing OrderLine as empty list (lines 148-150)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {"cbc:PayableAmount": "10"},
        }
    }
    data = order_json_to_invoice_data(order)
    assert data["lines"] == [
        {
            "lineId": "1",
            "quantity": "1",
            "unitPrice": "10",
            "lineTotal": "10",
            "description": "Order",
        }
    ]


def test_order_json_order_lines_not_list():
    """order_json normalises single OrderLine dict to list (lines 149-150), then not list (152)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {"cbc:PayableAmount": "10"},
            "cac:OrderLine": "invalid",
        }
    }
    data = order_json_to_invoice_data(order)
    assert data["lines"] == [
        {
            "lineId": "1",
            "quantity": "1",
            "unitPrice": "10",
            "lineTotal": "10",
            "description": "Order",
        }
    ]


def test_order_json_empty_lines_fallback():
    """order_json uses single 'Order' line when no valid lines (lines 161-166)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {"cbc:PayableAmount": "5"},
            "cac:OrderLine": [None, [], "skip"],
        }
    }
    data = order_json_to_invoice_data(order)
    assert len(data["lines"]) == 1
    assert data["lines"][0]["description"] == "Order"
    assert data["lines"][0]["lineTotal"] == "5"


def test_order_json_total_from_line_sum_when_zero():
    """order_json sets total_amount from line_sum when total_amount == 0 (lines 173-174)."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {},
            "cac:OrderLine": [
                {
                    "cac:LineItem": {
                        "cbc:ID": "1",
                        "cbc:Quantity": "1",
                        "cbc:LineExtensionAmount": "20",
                        "cac:Item": {"cbc:Description": "A"},
                    }
                },
                {
                    "cac:LineItem": {
                        "cbc:ID": "2",
                        "cbc:Quantity": "1",
                        "cbc:LineExtensionAmount": "30",
                        "cac:Item": {"cbc:Description": "B"},
                    }
                },
            ],
        }
    }
    data = order_json_to_invoice_data(order)
    assert float(data["totalAmount"]) == 50


def test_order_json_due_date_parameter():
    """order_json_to_invoice_data uses due_date argument when provided."""
    order = {
        "Order": {
            "cbc:IssueDate": "2020-01-01",
            "cac:BuyerCustomerParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "B"}}
            },
            "cac:SellerSupplierParty": {
                "cac:Party": {"cac:PartyName": {"cbc:Name": "S"}}
            },
            "cac:AnticipatedMonetaryTotal": {"cbc:PayableAmount": "1"},
            "cac:OrderLine": {
                "cac:LineItem": {
                    "cbc:ID": "1",
                    "cbc:Quantity": "1",
                    "cbc:LineExtensionAmount": "1",
                    "cac:Item": {"cbc:Description": "D"},
                }
            },
        }
    }
    data = order_json_to_invoice_data(order, due_date="2020-02-01")
    assert data["dueDate"] == "2020-02-01"
