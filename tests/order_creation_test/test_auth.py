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

# ------------------------------ login ------------------------------

def test_login_success():
    email = generate_unique_email()
    password = "StrongPassword123!"

    # First register user
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "nameFirst": "Test",
        "nameLast": "User"
    })

    # Then login
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })

    assert res.status_code == 200
    data = res.json()

    assert "token" in data
    assert "userId" in data


def test_login_wrong_password():
    email = generate_unique_email()

    # Register
    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    })

    # Attempt login with wrong password
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": "WrongPassword"
    })

    assert res.status_code == 401


def test_login_user_not_found():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": generate_unique_email(),
        "password": "StrongPassword123!"
    })

    assert res.status_code == 401