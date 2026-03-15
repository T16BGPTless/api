"""Tests for the main app (home route, etc.)."""

from http import HTTPStatus

import pytest

from app.app import app


@pytest.fixture
def client():
    """Flask test client."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_home_redirects_to_swagger(client):
    """GET / redirects to the docs URL."""
    resp = client.get("/")
    assert resp.status_code == HTTPStatus.FOUND  # 302
    assert resp.location == "https://docs.gptless.au"
