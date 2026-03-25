import requests
import pytest
import uuid

BASE_URL = "https://api.orderms.tech/v1"

# -------------------------- Helper Functions --------------------------

def generate_unique_email():
    return f"test_{uuid.uuid4()}@example.com"

# ------------------------------ Register ------------------------------

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

def test_register_missing_first_name():
    payload = {
        "email": generate_unique_email(),
        "password": "StrongPassword123!",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_missing_last_name():
    payload = {
        "email": generate_unique_email(),
        "password": "StrongPassword123!",
        "nameFirst": "Test"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400

def test_register_invalid_email():
    payload = {
        "email": "invalid-email",
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)

    assert res.status_code == 400


def test_register_non_string_email():
    payload = {
        "email": 12345,
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_missing_email():
    payload = {
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400

def test_register_duplicate_email():
    email = generate_unique_email()

    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res1 = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res2.status_code == 400


def test_register_empty_email():
    payload = {
        "email": "",
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


def test_register_non_string_password():
    payload = {
        "email": generate_unique_email(),
        "password": 12345678,
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_missing_password():
    payload = {
        "email": generate_unique_email(),
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_password_less_than_8_chars():
    payload = {
        "email": generate_unique_email(),
        "password": "Ab1!",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_password_no_letters():
    payload = {
        "email": generate_unique_email(),
        "password": "12345678",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_password_no_numbers():
    payload = {
        "email": generate_unique_email(),
        "password": "PasswordOnly",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


def test_register_empty_password():
    payload = {
        "email": generate_unique_email(),
        "password": "",
        "nameFirst": "Test",
        "nameLast": "User"
    }

    res = requests.post(f"{BASE_URL}/auth/register", json=payload)
    assert res.status_code == 400


# ------------------------------ Login ------------------------------

def test_login_success():
    email = generate_unique_email()
    password = "StrongPassword123!"

    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "nameFirst": "Test",
        "nameLast": "User"
    })

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

    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    })

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


def test_login_missing_email():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "password": "StrongPassword123!"
    })

    assert res.status_code == 400


def test_login_missing_password():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": generate_unique_email()
    })

    assert res.status_code == 400


def test_login_missing_both_fields():
    res = requests.post(f"{BASE_URL}/auth/login", json={})

    assert res.status_code == 400


def test_login_empty_email():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "",
        "password": "StrongPassword123!"
    })

    assert res.status_code == 400


def test_login_empty_password():
    email = generate_unique_email()

    requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": "StrongPassword123!",
        "nameFirst": "Test",
        "nameLast": "User"
    })

    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": ""
    })

    assert res.status_code == 400


def test_login_non_string_email():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": 12345,
        "password": "StrongPassword123!"
    })

    assert res.status_code == 400


def test_login_non_string_password():
    res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": generate_unique_email(),
        "password": 12345678
    })

    assert res.status_code == 401

# ------------------------------ logout ------------------------------

def test_logout_success():
    email = generate_unique_email()
    password = "StrongPassword123!"

    register_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "nameFirst": "Test",
        "nameLast": "User"
    })

    token = register_res.json()["token"]

    res = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"token": token}
    )

    assert res.status_code == 200
    assert res.json()["status"] == "success"


def test_logout_invalid_token():
    res = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"token": "invalid-token"}
    )

    assert res.status_code == 401
    

def test_logout_missing_token():
    res = requests.post(f"{BASE_URL}/auth/logout")

    assert res.status_code == 401


def test_logout_empty_token():
    res = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"token": ""}
    )

    assert res.status_code == 401


def test_logout_malformed_token():
    res = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"token": "12345"}
    )

    assert res.status_code == 401


def test_logout_twice():
    email = generate_unique_email()
    password = "StrongPassword123!"

    register_res = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": password,
        "nameFirst": "Test",
        "nameLast": "User"
    })

    token = register_res.json()["token"]

    res1 = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"token": token}
    )
    assert res1.status_code == 200

    res2 = requests.post(
        f"{BASE_URL}/auth/logout",
        headers={"token": token}
    )
    assert res2.status_code == 401
