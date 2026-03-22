import requests
import pytest
import uuid

BASE_URL = "https://api.orderms.tech/v1"

# ------------------------------ helper functions ------------------------------

def generate_unique_email():
    return f"test_{uuid.uuid4()}@example.com"

# ------------------------------ register ------------------------------

def test_register_success():
    payload = {
        "email": generate_unique_email(),
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)

    assert res.status_code == 201
    data = res.json()

    assert "userId" in data
    assert "token" in data


def test_register_invalid_email():
    payload = {
        "email": "invalid-email",
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)

    assert res.status_code == 400


def test_register_weak_password():
    payload = {
        "email": generate_unique_email(),
        "password": "123",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)

    assert res.status_code == 400