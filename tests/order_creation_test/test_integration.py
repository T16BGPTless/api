import requests
import uuid
import pytest

OUR_API = "https://api.gptless.au"
OTHER_API = "https://api.orderms.tech/v1"
DEV_TOKEN = ":3"

# -------------------------- Helper Functions --------------------------

def register_group():
    group_name = f"test-{uuid.uuid4()}"

    res = requests.post(
        f"{OUR_API}/v1/auth/register",
        json={"groupName": group_name},
        headers={"APIdevToken": DEV_TOKEN}
    )

    assert res.status_code == 201, res.text
    api_token = res.json()["APItoken"]

    return group_name, api_token


def cleanup_group(group_name):
    requests.delete(
        f"{OUR_API}/v1/auth/revoke",
        json={"groupName": group_name},
        headers={"APIdevToken": DEV_TOKEN}
    )


def create_order_external():
    payload = {
        "ID": f"ORD-{uuid.uuid4()}",
        "IssueDate": "2026-03-16",
        "BuyerCustomerParty": {
            "Party": {
                "PartyName": [{"Name": "Integration Buyer"}]
            }
        },
        "SellerSupplierParty": {
            "Party": {
                "PartyName": [{"Name": "Integration Seller"}]
            }
        },
        "OrderLine": [
            {
                "LineItem": {
                    "ID": "1",
                    "Item": {
                        "Name": "Integration Item",
                        "Description": ["Test Description"]
                    }
                }
            }
        ]
    }

    res = requests.post(f"{OTHER_API}/orders", json=payload)
    assert res.status_code == 201, res.text

    data = res.json()
    result = data.get("result", {})

    order_id = (
        data.get("orderId") or
        data.get("_id") or
        result.get("orderId")
    )

    assert order_id is not None, f"Missing orderId in response: {data}"
    assert order_id is not None, f"Missing orderId in response: {data}"

    return order_id


def get_order_xml(order_id):
    possible_urls = [
        f"{OTHER_API}/orders/{order_id}/xml",
        f"{OTHER_API}/order/orders/{order_id}/xml",
    ]

    for url in possible_urls:
        res = requests.get(url)
        if res.status_code == 200:
            return res.text

    pytest.fail("Could not retrieve XML from external API")


def convert_order(xml, api_token):
    res = requests.post(
        f"{OUR_API}/v1/orders/convert",
        data=xml,
        headers={
            "APItoken": api_token,
            "Content-Type": "application/xml"
        }
    )

    assert res.status_code == 200, res.text

    data = res.json()
    assert "InvoiceData" in data, "Missing InvoiceData from conversion"

    return data["InvoiceData"]


def generate_invoice(invoice_data, api_token):
    res = requests.post(
        f"{OUR_API}/v1/invoices/generate",
        json={"InvoiceData": invoice_data},
        headers={"APItoken": api_token}
    )

    assert res.status_code == 201, res.text

    xml = res.text
    assert xml.strip().startswith("<"), "Invalid XML response"

    return xml

# -------------------------- Integration Test --------------------------

# ALL THE STEPS DONE:
# Step 1: Create order in external API
# Step 2: Get XML from external API
# Step 3: Convert XML -> JSON using OUR API
# Step 4: Generate invoice from JSON
# Step 5: Cleanup (VERY IMPORTANT)

def test_order_to_invoice_integration():
    group_name, api_token = register_group()

    try:
        order_id = create_order_external()
        
        xml = get_order_xml(order_id)
        assert len(xml) > 0, "Empty XML received"

        invoice_data = convert_order(xml, api_token)
        assert isinstance(invoice_data, dict), "InvoiceData not a dict"

        invoice_xml = generate_invoice(invoice_data, api_token)
        assert "<Invoice" in invoice_xml or "<" in invoice_xml
    finally:
        cleanup_group(group_name)