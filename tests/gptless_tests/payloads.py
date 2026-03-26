"""Payloads shared by black-box API tests."""

from __future__ import annotations

from typing import Any


def valid_generate_invoice_payload() -> dict[str, Any]:
    """Return a minimal valid payload for /v1/invoices/generate."""
    return {
        "InvoiceData": {
            "supplier": {"name": "Aperture Laboratories", "ABN": "12345678987"},
            "customer": {"name": "TerraGroup", "ABN": "12345678987"},
            "issueDate": "2026-03-15",
            "dueDate": "2026-03-22",
            "totalAmount": 30.0,
            "currency": "AUD",
            "lines": [
                {
                    "lineId": "1",
                    "description": "Companion Cube",
                    "quantity": 1,
                    "unitPrice": 30.0,
                    "lineTotal": 30.0,
                }
            ],
        }
    }


def invalid_generate_invoice_payload_missing_supplier() -> dict[str, Any]:
    """Return an intentionally invalid payload for 400 tests."""
    payload = valid_generate_invoice_payload()
    del payload["InvoiceData"]["supplier"]
    return payload


def valid_order_xml_payload() -> str:
    """Return a compact but valid UBL order XML sample."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<Order xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2" xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2" xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2">
  <cbc:ID>AEG012345</cbc:ID>
  <cbc:IssueDate>2005-06-20</cbc:IssueDate>
  <cac:BuyerCustomerParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>IYT Corporation</cbc:Name></cac:PartyName>
      <cac:PartyTaxScheme><cbc:CompanyID>12356478</cbc:CompanyID></cac:PartyTaxScheme>
    </cac:Party>
  </cac:BuyerCustomerParty>
  <cac:SellerSupplierParty>
    <cac:Party>
      <cac:PartyName><cbc:Name>Consortial</cbc:Name></cac:PartyName>
      <cac:PartyTaxScheme><cbc:CompanyID>1752692355</cbc:CompanyID></cac:PartyTaxScheme>
    </cac:Party>
  </cac:SellerSupplierParty>
  <cac:AnticipatedMonetaryTotal>
    <cbc:PayableAmount currencyID="GBP">100.00</cbc:PayableAmount>
  </cac:AnticipatedMonetaryTotal>
  <cac:OrderLine>
    <cac:LineItem>
      <cbc:ID>1</cbc:ID>
      <cbc:Quantity unitCode="KGM">100</cbc:Quantity>
      <cbc:LineExtensionAmount currencyID="GBP">100.00</cbc:LineExtensionAmount>
      <cac:Price><cbc:PriceAmount currencyID="GBP">100.00</cbc:PriceAmount></cac:Price>
      <cac:Item><cbc:Description>Acme beeswax</cbc:Description></cac:Item>
    </cac:LineItem>
  </cac:OrderLine>
</Order>"""


def valid_recipient_email() -> str:
    """Return a valid recipient email address for happy-path tests."""
    return "accounts@gptless.com"


def invalid_recipient_email() -> str:
    """Return an intentionally invalid recipient email for 400 tests."""
    return "not-an-email"
