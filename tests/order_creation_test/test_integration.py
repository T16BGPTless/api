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


def get_external_token():
    res = requests.post(f"{OTHER_API}/auth/register", json={
        "email": f"test_{uuid.uuid4()}@example.com",
        "password": "StrongPassword123!",
        "nameFirst": "Integration",
        "nameLast": "Tester"
    })

    assert res.status_code == 201, res.text
    return res.json()["token"]


def create_order_external(token):
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

    res = requests.post(
        f"{OTHER_API}/orders",
        json=payload,
        headers={"token": token}
    )

    assert res.status_code == 201, res.text

    data = res.json()
    result = data.get("result", data)

    order_id = result.get("orderId")
    ubl_url = result.get("ublXmlUrl")

    assert order_id is not None, f"Missing orderId: {data}"
    assert ubl_url is not None, f"Missing ublXmlUrl: {data}"

    if ubl_url.startswith("/"):
        ubl_url = f"{OTHER_API}{ubl_url}"

    return order_id, ubl_url


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
    assert "<Invoice" in xml, "Invalid Invoice XML response"

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
    external_token = get_external_token()

    try:
        # Step 1
        order_id, ubl_url = create_order_external(external_token)

        # Step 2
        res = requests.get(
            ubl_url,
            headers={"token": external_token}
        )
        assert res.status_code == 200
        xml = res.text
        assert len(xml) > 0, "Empty XML received"

        # Step 3
        invoice_data = convert_order(xml, api_token)
        assert isinstance(invoice_data, dict)

        # Step 4
        invoice_xml = generate_invoice(invoice_data, api_token)
        assert "<Invoice" in invoice_xml

    finally:
        # Step 5
        cleanup_group(group_name)


def test_convert_invalid_xml():
    group_name, api_token = register_group()

    try:
        res = requests.post(
            f"{OUR_API}/v1/orders/convert",
            data="this is not xml",
            headers={
                "APItoken": api_token,
                "Content-Type": "application/xml"
            }
        )

        assert res.status_code == 400

    finally:
        cleanup_group(group_name)