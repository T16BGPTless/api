"""Generate invoice tests."""

from unittest.mock import patch, MagicMock
from http import HTTPStatus
import pytest
from app.app import app


# ------------------------------ MOCK SUPABASE ------------------------------
# Creates a mock of a database
@pytest.fixture
def client():
    """Fixture to provide a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ------------------------------ MOCK SUPABASE ------------------------------
# Creates a mock of a database
class MockResponse:
    """Helper class to simulate Supabase response objects."""

    def __init__(self, data=None, error=None):
        self.data = data or []
        self.error = error


# ------------------------------- TEST CASES --------------------------------


# CASE 1: SUCCESS (201 CREATED) - Using Template ID
def test_generate_invoice_success_template(client):
    """Valid token and template ID: creates and returns XML."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": 10}])
    mock_group_lookup = MockResponse(data=[{"id": 10}])
    mock_template_data = MockResponse(
        data=[
            {
                "invoice_data": {
                    "issueDate": "2026-01-01",
                    "dueDate": "2026-01-02",
                    "currency": "AUD",
                    "totalAmount": 1,
                    "supplier": {"name": "invoice name", "ABN": "123"},
                    "customer": {"name": "customer name", "ABN": "456"},
                    "lines": [
                        {
                            "lineId": "1",
                            "description": "item",
                            "quantity": 1,
                            "unitPrice": 1,
                            "lineTotal": 1,
                        }
                    ],
                }
            }
        ]
    )
    mock_insert = MockResponse(data=[{"id": 500}])
    mock_update = MockResponse(data=[{"id": 500}])

    payload = {"templateInvoice": "123"}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.build_invoice_xml", return_value="<RichXML/>"),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[
                mock_tmpl_check,
                mock_group_lookup,
                mock_template_data,
                mock_group_lookup,
                mock_insert,
                mock_update,
            ],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate", json=payload, headers={"APItoken": "valid-token"}
        )

        assert response.status_code == HTTPStatus.CREATED
        assert b"<RichXML/>" in response.data
        assert response.mimetype == "application/xml"


# CASE 2: SUCCESS - Using Rich Invoice Data
def test_generate_invoice_success_rich_data(client):
    """If InvoiceData is provided, it calls build_invoice_xml."""
    mock_insert = MockResponse(data=[{"id": 501}])
    payload = {"InvoiceData": {"items": []}}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.build_invoice_xml", return_value="<RichXML/>"),
        patch("app.routes.invoices.sb_execute", return_value=mock_insert),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate", json=payload, headers={"APItoken": "valid-token"}
        )

        assert response.status_code == HTTPStatus.CREATED
        assert b"<RichXML/>" in response.data


# CASE 3: NOT FOUND - Template Doesn't Exist (404)
def test_generate_invoice_template_not_found(client):
    """Template doesn't exist (sb_execute returns empty list)."""
    mock_tmpl_check = MockResponse(data=[])  # No rows found
    payload = {"templateInvoice": "NONEXISTENT"}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_tmpl_check),
    ):
        response = client.post(
            "/v1/invoices/generate", json=payload, headers={"APItoken": "valid-token"}
        )
        assert response.status_code == HTTPStatus.NOT_FOUND


# CASE 4: FORBIDDEN - Template Owned by Someone Else (403)
def test_generate_invoice_template_wrong_owner(client):
    """Template owned by someone else (sb_execute returns owner_token != token)."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": "someone-else"}])
    payload = {"templateInvoice": "T123"}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_tmpl_check),
    ):
        response = client.post(
            "/v1/invoices/generate", json=payload, headers={"APItoken": "valid-token"}
        )
        assert response.status_code == HTTPStatus.FORBIDDEN


# CASE 5: BAD REQUEST - XML Build Failure (400)
def test_generate_invoice_xml_error(client):
    """Tests the try/except block for build_invoice_xml raising ValueError."""
    mock_group_lookup = MockResponse(data=[{"id": 10}])
    mock_insert = MockResponse(data=[{"id": 500}])

    payload = {"InvoiceData": {"bad": "data"}}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.build_invoice_xml",
            side_effect=ValueError("Invalid data format"),
        ),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[mock_group_lookup, mock_insert],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json=payload,
            headers={"APItoken": "valid-token"},
        )

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.get_json()["error"] == "BAD_REQUEST"


# CASE 6: UNAUTHORIZED (401)
def test_generate_invoice_unauthorized(client):
    """Invalid token (sb_execute returns None)."""
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=False),
    ):
        response = client.post("/v1/invoices/generate", headers={"APItoken": "bad"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 7: INTERNAL SERVER ERROR - Insert Fails (500)
def test_generate_invoice_insert_fail(client):
    """Template check passes, but the insert fails."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": 10}])
    mock_group_lookup = MockResponse(data=[{"id": 10}])
    mock_template_data = MockResponse(
        data=[
            {
                "invoice_data": {
                    "issueDate": "2026-01-01",
                    "dueDate": "2026-01-02",
                    "currency": "AUD",
                    "totalAmount": 1,
                    "supplier": {"name": "invoice name", "ABN": "123"},
                    "customer": {"name": "customer name", "ABN": "456"},
                    "lines": [
                        {
                            "lineId": "1",
                            "description": "item",
                            "quantity": 1,
                            "unitPrice": 1,
                            "lineTotal": 1,
                        }
                    ],
                }
            }
        ]
    )

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[
                mock_tmpl_check,
                mock_group_lookup,
                mock_template_data,
                mock_group_lookup,
                None,
            ],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={"templateInvoice": "T1"},
            headers={"APItoken": "token"},
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 8: DATABASE INITIALIZATION FAILURE (500)
def test_generate_invoice_db_connection_fail(client):
    """Scenario where get_db() returns None at the start of generation."""
    with patch("app.routes.invoices.get_db", return_value=None):
        response = client.post(
            "/v1/invoices/generate",
            json={"templateInvoice": "T1"},
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 9: TEMPLATE LOOKUP EXECUTION FAILURE (500)
def test_generate_invoice_template_lookup_error(client):
    """The query to check if the template exists fails (sb_execute returns None)."""
    payload = {"templateInvoice": "T123"}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=None),
    ):
        response = client.post(
            "/v1/invoices/generate", json=payload, headers={"APItoken": "valid-token"}
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 10: TEMPLATE LOOKUP SUPABASE ERROR (500)
def test_generate_invoice_template_supabase_error(client):
    """The template lookup runs but Supabase returns an error flag."""
    mock_err = MockResponse(error="Database Error")
    payload = {"templateInvoice": "T123"}

    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=mock_err),
        patch("app.routes.invoices.sb_has_error", return_value=True),
    ):
        response = client.post(
            "/v1/invoices/generate", json=payload, headers={"APItoken": "valid-token"}
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 11: UNAUTHORIZED - get_group_id_from_token fails with template (line 70)
def test_generate_invoice_group_lookup_fails_with_template(client):
    """With template_id set, first get_group_id_from_token fails
    (e.g. api_groups select returns None)."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": 10}])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[mock_tmpl_check, None],  # template ok, group lookup fails
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={"templateInvoice": "123"},
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 12: UNAUTHORIZED - get_group_id_from_token fails without template (line 104)
def test_generate_invoice_group_lookup_fails_no_template(client):
    """Without template, get_group_id_from_token fails before insert."""
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.sb_execute", return_value=None),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={},
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.UNAUTHORIZED


# CASE 13: Template invoice_data not a dict → merged_data = {} (line 95)
def test_generate_invoice_template_invoice_data_not_dict(client):
    """When template invoice_data is not a dict, merge uses empty dict."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": 10}])
    mock_group = MockResponse(data=[{"id": 10}])
    # Truthy non-dict so template_data is not a dict ([] or {} → {} in Python)
    mock_template_data = MockResponse(data=[{"invoice_data": "not-a-dict"}])
    mock_insert = MockResponse(data=[{"id": 600}])
    mock_update = MockResponse(data=[{"id": 600}])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.build_invoice_xml",
            return_value="<Invoice/>",
        ),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[
                mock_tmpl_check,
                mock_group,
                mock_template_data,
                mock_group,
                mock_insert,
                mock_update,
            ],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={"templateInvoice": "123", "InvoiceData": {"invoiceID": "600"}},
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.CREATED


# CASE 14: Template merge with request InvoiceData (line 98)
def test_generate_invoice_template_merge_with_request_data(client):
    """Template invoice_data is merged with request InvoiceData (request on top)."""
    mock_tmpl_check = MockResponse(data=[{"owner_token": 10}])
    mock_group = MockResponse(data=[{"id": 10}])
    mock_template_data = MockResponse(
        data=[{"invoice_data": {"issueDate": "2026-01-01", "currency": "AUD"}}]
    )
    mock_insert = MockResponse(data=[{"id": 601}])
    mock_update = MockResponse(data=[{"id": 601}])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.build_invoice_xml",
            return_value="<Invoice/>",
        ),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[
                mock_tmpl_check,
                mock_group,
                mock_template_data,
                mock_group,
                mock_insert,
                mock_update,
            ],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={
                "templateInvoice": "123",
                "InvoiceData": {"dueDate": "2026-01-02", "currency": "USD"},
            },
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.CREATED


# CASE 15: Insert returns data but id is None (line 121)
def test_generate_invoice_insert_returns_no_id(client):
    """Insert succeeds but response data has no id → 500."""
    mock_group = MockResponse(data=[{"id": 10}])
    mock_insert_no_id = MockResponse(data=[{}])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[mock_group, mock_insert_no_id],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={},
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR


# CASE 16: Update after insert fails (line 132)
def test_generate_invoice_update_fails(client):
    """Insert succeeds but update (xml, deleted) fails → 500."""
    mock_group = MockResponse(data=[{"id": 10}])
    mock_insert = MockResponse(data=[{"id": 602}])
    with (
        patch("app.routes.invoices.get_db", return_value=MagicMock()),
        patch("app.routes.invoices.is_valid_api_token", return_value=True),
        patch("app.routes.invoices.build_invoice_xml", return_value="<Invoice/>"),
        patch(
            "app.routes.invoices.sb_execute",
            side_effect=[mock_group, mock_insert, None],
        ),
        patch("app.routes.invoices.sb_has_error", return_value=False),
    ):
        response = client.post(
            "/v1/invoices/generate",
            json={},
            headers={"APItoken": "valid-token"},
        )
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
