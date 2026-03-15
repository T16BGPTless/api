"""Shared pytest fixtures for backend tests."""

import os

import pytest


@pytest.fixture
def valid_dev_token():
    """Token from VALID_DEV_TOKENS env (required for tests that call protected routes)."""
    raw = os.environ.get("VALID_DEV_TOKENS", "").strip()
    token = raw.split(",")[0].strip() if raw else ""
    if not token:
        pytest.skip(
            "VALID_DEV_TOKENS not set (set in CI via secrets or in .env locally)"
        )
    return token
