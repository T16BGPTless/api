"""Pytest fixtures for black-box client testing."""

from __future__ import annotations

import os

import pytest

from gptless_tests.client import InvoicingApiClient


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


@pytest.fixture
def base_url() -> str:
    """Black-box integration target URL.

    We require `API_BASE_URL` to be set to avoid accidentally calling a down public
    environment (e.g. preview) from CI.
    """
    val = env("API_BASE_URL")
    if not val:
        pytest.skip("API_BASE_URL is not set; skipping black-box HTTP calls.")
    return val


@pytest.fixture
def api_token() -> str:
    """API token for integration tests requiring APItoken."""
    token = env("API_TOKEN")
    if not token:
        pytest.skip("API_TOKEN is not set; skipping APItoken integration tests.")
    return token


@pytest.fixture
def integration_client(base_url: str, api_token: str) -> InvoicingApiClient:
    """Client configured for APItoken-protected routes."""
    return InvoicingApiClient(base_url=base_url, api_token=api_token)


@pytest.fixture
def unauth_client(base_url: str) -> InvoicingApiClient:
    """Client without API token (used for 401/unauthorized checks)."""
    return InvoicingApiClient(base_url=base_url)
