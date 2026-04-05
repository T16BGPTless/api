"""Pytest fixtures for black-box client testing."""

from __future__ import annotations

import os
import ssl
import urllib.error
import urllib.request

import pytest

from gptless_tests.client import InvoicingApiClient


def env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _tls_probe(url: str) -> None:
    """Perform a lightweight HTTPS probe to fail fast on cert trust issues."""
    if not url.lower().startswith("https://"):
        return

    request = urllib.request.Request(url=f"{url.rstrip('/')}/", method="GET")
    try:
        with urllib.request.urlopen(request, timeout=5):
            return
    except urllib.error.HTTPError:
        # Host is reachable and TLS succeeded; HTTP status can be non-2xx.
        return
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if isinstance(reason, ssl.SSLCertVerificationError):
            pytest.skip(
                "Skipping black-box tests: TLS certificate verification failed for "
                f"{url}. Configure system/Python CA trust or use API_BASE_URL over "
                "http://localhost."
            )
        raise


@pytest.fixture
def base_url() -> str:
    """Black-box integration target URL.

    We require `API_BASE_URL` to be set to avoid accidentally calling a down public
    environment (e.g. preview) from CI.
    """
    val = env("API_BASE_URL")
    if not val:
        pytest.skip("API_BASE_URL is not set; skipping black-box HTTP calls.")

    _tls_probe(val)
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
