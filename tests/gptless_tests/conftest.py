"""Pytest fixtures for black-box client testing."""

from __future__ import annotations

import os

import pytest

from gptless_tests.client import InvoicingApiClient


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


@pytest.fixture
def base_url() -> str:
    """Integration target URL; defaults to preview from swagger."""
    return _env("API_BASE_URL") or "https://preview.gptless.au"


@pytest.fixture
def api_token() -> str:
    """API token for integration tests requiring APItoken."""
    token = _env("API_TOKEN")
    if not token:
        pytest.skip("API_TOKEN is not set; skipping APItoken integration tests.")
    return token


@pytest.fixture
def integration_client(base_url: str, api_token: str) -> InvoicingApiClient:
    """Client configured for APItoken-protected routes."""
    return InvoicingApiClient(base_url=base_url, api_token=api_token)


@pytest.fixture
def unit_client() -> InvoicingApiClient:
    """Client for unit tests with placeholder credentials."""
    return InvoicingApiClient(
        base_url="https://example.test",
        api_token="api-token",
    )
