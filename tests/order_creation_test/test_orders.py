import requests
import uuid
import pytest
from datetime import datetime

BASE_URL = "https://api.orderms.tech/v1"


# -------------------------- Helper Functions --------------------------

def generate_unique_email():
    return f"test_{uuid.uuid4()}@example.com"


def register_and_get_token():
    res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": generate_unique_email(),
        "password": "StrongPassword123!",
        "nameFirst": "Order",
        "nameLast": "Tester"
    })

    assert res.status_code == 201
    return res.json()["token"]


def valid_order_payload():
    return {
        "ID": f"ORD-{uuid.uuid4()}",
        "IssueDate": "2026-03-16",
        "BuyerCustomerParty": {
            "Party": {
                "PartyName": [{"Name": "Test Buyer"}]
            }
        },
        "SellerSupplierParty": {
            "Party": {
                "PartyName": [{"Name": "Test Seller"}]
            }
        },
        "OrderLine": [
            {
                "LineItem": {
                    "ID": "LINE-001",
                    "Item": {
                        "Description": ["Test Item"],
                        "Name": "Test Product"
                    }
                }
            }
        ]
    }


# ---------------------------- Create Order ----------------------------

def test_create_order_success_and_structure():
    token = register_and_get_token()

    res = requests.post(
        f"{BASE_URL}/orders",
        json=valid_order_payload(),
        headers={"token": token}
    )

    assert res.status_code == 201

    data = res.json()

    # Structure validation
    assert isinstance(data, dict)
    assert data["status"] == "success"
    assert isinstance(data.get("orderId"), str)
    assert isinstance(data.get("ublXmlUrl"), str)

    # Basic format validation
    assert data["ublXmlUrl"].startswith("/order/")
    assert len(data["orderId"]) > 0


def test_create_order_without_authentication():
    res = requests.post(
        f"{BASE_URL}/orders",
        json=valid_order_payload()
    )

    assert res.status_code == 401


def test_create_order_with_invalid_token():
    res = requests.post(
        f"{BASE_URL}/orders",
        json=valid_order_payload(),
        headers={"token": "invalid-token"}
    )

    assert res.status_code == 401


def test_create_order_missing_required_fields():
    token = register_and_get_token()

    invalid_payloads = [
        {},
        {"ID": "ONLY-ID"},
        {"IssueDate": "2026-03-16"},
    ]

    for payload in invalid_payloads:
        res = requests.post(
            f"{BASE_URL}/orders",
            json=payload,
            headers={"token": token}
        )

        assert res.status_code == 400


def test_create_order_invalid_date_formats():
    token = register_and_get_token()

    invalid_dates = [
        "16-03-2026",
        "2026/03/16",
        "invalid-date",
        "",
        None
    ]

    for date in invalid_dates:
        payload = valid_order_payload()
        payload["IssueDate"] = date

        res = requests.post(
            f"{BASE_URL}/orders",
            json=payload,
            headers={"token": token}
        )

        assert res.status_code == 400


def test_create_order_empty_order_lines():
    token = register_and_get_token()

    payload = valid_order_payload()
    payload["OrderLine"] = []

    res = requests.post(
        f"{BASE_URL}/orders",
        json=payload,
        headers={"token": token}
    )

    assert res.status_code == 400


def test_create_order_large_payload():
    token = register_and_get_token()

    payload = valid_order_payload()

    payload["OrderLine"] = [
        {
            "LineItem": {
                "ID": f"LINE-{i}",
                "Item": {
                    "Description": ["Bulk item"],
                    "Name": f"Product-{i}"
                }
            }
        }
        for i in range(50)
    ]

    res = requests.post(
        f"{BASE_URL}/orders",
        json=payload,
        headers={"token": token}
    )

    assert res.status_code in [201, 500]

# ----------------------------  Order List ----------------------------

def test_list_orders_structure_and_types():
    token = register_and_get_token()

    requests.post(
        f"{BASE_URL}/orders",
        json=valid_order_payload(),
        headers={"token": token}
    )

    res = requests.get(
        f"{BASE_URL}/orders",
        headers={"token": token}
    )

    assert res.status_code == 200

    data = res.json()
    assert isinstance(data, list)

    for order in data:
        assert "orderId" in order
        assert "data" in order
        assert "createdAt" in order
        assert "url" in order

        try:
            datetime.fromisoformat(order["createdAt"].replace("Z", "+00:00"))
        except Exception:
            pytest.fail("Invalid datetime format")


def test_list_orders_data_consistency():
    token = register_and_get_token()

    payload = valid_order_payload()

    create_res = requests.post(
        f"{BASE_URL}/orders",
        json=payload,
        headers={"token": token}
    )

    created_order_id = create_res.json()["orderId"]

    list_res = requests.get(
        f"{BASE_URL}/orders",
        headers={"token": token}
    )

    orders = list_res.json()
    found = any(order["orderId"] == created_order_id for order in orders)

    assert found is True


def test_list_orders_empty_case():
    token = register_and_get_token()

    res = requests.get(
        f"{BASE_URL}/orders",
        headers={"token": token}
    )

    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_list_orders_unauthorized():
    res = requests.get(f"{BASE_URL}/orders")

    assert res.status_code == 401


def test_list_orders_invalid_token():
    res = requests.get(
        f"{BASE_URL}/orders",
        headers={"token": "invalid-token"}
    )

    assert res.status_code == 401

# ----------------------------  Get Order ----------------------------

def test_get_order_by_id():
    # 1. Register user and get token
    token = register_and_get_token()

    # 2. Create an order using POST /orders
    create_res = requests.post(
        f"{BASE_URL}/orders",
        json=valid_order_payload(),
        headers={"token": token}
    )
    
    # 3. Extract orderId from response IF available
    order_id = create_res.json().get("orderId")


    # 4. Send GET request to /orders/{orderId}
    res = requests.get(
        f"{BASE_URL}/orders/{order_id}",
        headers={"token": token}
    )

    # 5. Put your assert stuff here :)
    # ...

# ----------------------------  Update Order -------------------------



# ----------------------------  Delete Order --------------------------



# --------------------------  Get order as UBL ------------------------


