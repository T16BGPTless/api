"""Tests for order conversion route (XML to JSON)."""

from pathlib import Path

import pytest
from flask import Flask

from app.routes.orders import orders_bp


@pytest.fixture
def client():
    """Flask test client using only the orders blueprint (no Supabase required)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(orders_bp)
    with app.test_client() as c:
        yield c


# Minimal UBL-like Order XML (no default namespace to avoid key quirks)
MINIMAL_ORDER_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Order xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
       xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
       xmlns="urn:oasis:names:specification:ubl:schema:xsd:Order-2">
  <cbc:ID>ORD-001</cbc:ID>
  <cbc:IssueDate>2005-06-20</cbc:IssueDate>
  <cac:OrderLine>
    <cac:LineItem>
      <cbc:ID>1</cbc:ID>
      <cbc:Quantity unitCode="EA">10</cbc:Quantity>
    </cac:LineItem>
  </cac:OrderLine>
</Order>
"""


def test_convert_order_success(client):
    """Valid Order XML returns 200 and JSON structure."""
    response = client.post(
        "/v1/orders/convert",
        data=MINIMAL_ORDER_XML,
        content_type="application/xml",
    )
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    data = response.get_json()
    assert isinstance(data, dict)
    # xmltodict root key may be 'Order' or include namespace
    root = data.get("Order") or data
    assert root is not None
    # Should have nested content (ID or OrderLine)
    assert "ORD-001" in str(data) or "ORD-001" in str(root)


def test_convert_order_example_document(client):
    """Real UBL Order example from docs converts to JSON with expected content."""
    example_path = Path(__file__).resolve().parents[2] / "docs" / "orderdocexample.xml"
    if not example_path.exists():
        pytest.skip("docs/orderdocexample.xml not found")
    xml_body = example_path.read_text(encoding="utf-8")
    response = client.post(
        "/v1/orders/convert",
        data=xml_body,
        content_type="application/xml",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, dict)
    # Example contains these values
    json_str = str(data)
    assert "AEG012345" in json_str
    assert "IYT Corporation" in json_str
    assert "Consortial" in json_str
    assert "Acme beeswax" in json_str


def test_convert_order_empty_body(client):
    """Empty request body returns 400."""
    response = client.post(
        "/v1/orders/convert",
        data="",
        content_type="application/xml",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body.get("error") == "BAD_REQUEST"
    assert "XML" in body.get("message", "")


def test_convert_order_whitespace_only_body(client):
    """Whitespace-only body returns 400."""
    response = client.post(
        "/v1/orders/convert",
        data="   \n\t  ",
        content_type="text/xml",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body.get("error") == "BAD_REQUEST"


def test_convert_order_invalid_xml(client):
    """Malformed XML returns 400."""
    response = client.post(
        "/v1/orders/convert",
        data="<Order><cbc:ID>1</cbc:ID>",
        content_type="application/xml",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body.get("error") == "BAD_REQUEST"
    assert "Invalid XML" in body.get("message", "")


def test_convert_order_not_xml_returns_400(client):
    """Non-XML body that fails to parse returns 400."""
    response = client.post(
        "/v1/orders/convert",
        data="not xml at all {{{",
        content_type="application/xml",
    )
    assert response.status_code == 400
    body = response.get_json()
    assert body.get("error") == "BAD_REQUEST"


# ------------------- Service unit tests (order_xml_to_json) -------------------


def test_order_xml_to_json_success():
    """order_xml_to_json returns dict for valid XML."""
    from app.services.order_xml import order_xml_to_json

    result = order_xml_to_json(MINIMAL_ORDER_XML)
    assert isinstance(result, dict)
    assert "ORD-001" in str(result)


def test_order_xml_to_json_empty_raises():
    """order_xml_to_json raises ValueError for empty string."""
    from app.services.order_xml import order_xml_to_json

    with pytest.raises(ValueError, match="must not be empty"):
        order_xml_to_json("")


def test_order_xml_to_json_invalid_xml_raises():
    """order_xml_to_json raises ValueError for malformed XML."""
    from app.services.order_xml import order_xml_to_json

    with pytest.raises(ValueError, match="Invalid XML"):
        order_xml_to_json("<Order><cbc:ID>1</cbc:ID>")


# ------------------- Integration: order JSON -> invoice data -> invoice XML -------------------


def test_order_json_to_invoice_data_to_xml_roundtrip():
    """Order XML -> JSON -> InvoiceData -> build_invoice_xml produces valid invoice XML."""
    from app.services.invoice_xml import build_invoice_xml
    from app.services.order_xml import order_xml_to_json
    from app.services.order_to_invoice import order_json_to_invoice_data

    example_path = Path(__file__).resolve().parents[2] / "docs" / "orderdocexample.xml"
    if not example_path.exists():
        pytest.skip("docs/orderdocexample.xml not found")

    order_xml = example_path.read_text(encoding="utf-8")
    order_json = order_xml_to_json(order_xml)
    invoice_data = order_json_to_invoice_data(order_json)
    invoice_data["invoiceID"] = "test-inv-1"
    invoice_xml = build_invoice_xml(invoice_data)

    assert "<?xml" in invoice_xml
    assert "Invoice" in invoice_xml
    assert "IYT Corporation" in invoice_xml or "Consortial" in invoice_xml
    assert "Acme beeswax" in invoice_xml or "100" in invoice_xml
