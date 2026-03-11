from http import HTTPStatus
from unittest.mock import MagicMock


def test_list_invoices_success(client, mock_supabase_client):
    """
    Test that the API returns a list of invoice IDs.
    """

    # Create fake database response
    mock_response = MagicMock()
    mock_response.data = [
        {"id": 1},
        {"id": 2},
        {"id": 3}
    ]

    # Simulate Supabase query chain
    mock_supabase_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = mock_response

    # Send request to API
    response = client.get(
        "/v1/invoices",
        headers={"APItoken": "fake-token"}
    )

    # Check response
    assert response.status_code == HTTPStatus.OK
    assert response.get_json() == [1, 2, 3]


def test_list_invoices_missing_token(client):
    """
    If the APItoken header is missing,
    the API should return 401 Unauthorized.
    """

    response = client.get("/v1/invoices")

    assert response.status_code == HTTPStatus.UNAUTHORIZED