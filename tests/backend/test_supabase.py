"""Supabase integration tests."""

from pathlib import Path
import sys
import uuid
from http import HTTPStatus

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def sb():
    """Get the Supabase client."""
    from app.db.supabase_client import get_supabase

    try:
        return get_supabase()
    except ValueError:
        pytest.skip(
            "Supabase not configured (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY)"
        )


@pytest.fixture()
def flask_client():
    """Get the Flask client."""
    from app.app import app

    app.config.update(TESTING=True)
    return app.test_client()


def test_auth_register_creates_group_row(flask_client, sb):
    """Test that registering a group creates a group row in the database."""
    group_name = f"pytest-{uuid.uuid4().hex}"
    try:
        resp = flask_client.post(
            "/v1/auth/register",
            headers={"APIdevToken": "dev-secret"},
            json={"groupName": group_name},
        )
        assert resp.status_code == 201
        api_token = resp.get_json().get("APItoken")
        assert isinstance(api_token, str) and api_token

        sb_resp = (
            sb.table("api_groups")
            .select("group_name, api_token")
            .eq("group_name", group_name)
            .limit(1)
            .execute()
        )
        assert sb_resp.data and sb_resp.data[0]["api_token"] == api_token
    finally:
        sb.table("api_groups").delete().eq("group_name", group_name).execute()

def test_invoices_generate_list_get_delete_roundtrip(flask_client, sb):
    """Test that generating an invoice creates a invoice row in the database."""
    # Create a group + template we own, then generate an invoice and verify it exists in DB.
    group_name = f"pytest-{uuid.uuid4().hex}"
    api_token = uuid.uuid4().hex
    template_invoice_id = None
    invoice_id = None

    try:
        group = (
            sb.table("api_groups")
            .insert({"group_name": group_name, "api_token": api_token})
            .execute()
        )
        group_id = group.data[0]["id"]

        template = (
            sb.table("api_invoices")
            .insert(
                {
                    "owner_token": group_id,
                    "template_id": "",
                    "xml": "<TemplateInvoice/>",
                    "deleted": False,
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
                    },
                }
            )
            .execute()
        )
        template_invoice_id = template.data[0]["id"]

        created = flask_client.post(
            "/v1/invoices/generate",
            headers={"APItoken": api_token},
            json={"templateInvoice": template_invoice_id, "InvoiceData": {}},
        )
        assert created.status_code == 201
        assert "<cbc:ID>" in created.get_data(as_text=True)

        # Read newest invoice row for our group/template.
        inv = (
            sb.table("api_invoices")
            .select("id, owner_token, template_id, xml")
            .eq("owner_token", group_id)
            .eq("template_id", template_invoice_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        assert inv.data
        invoice_id = inv.data[0]["id"]
        assert inv.data[0]["xml"] == created.get_data(as_text=True)

        listed = flask_client.get("/v1/invoices", headers={"APItoken": api_token})
        assert listed.status_code == 200
        assert invoice_id in listed.get_json()

        fetched = flask_client.get(
            f"/v1/invoices/{invoice_id}", headers={"APItoken": api_token}
        )
        assert fetched.status_code == 200
        assert fetched.get_data(as_text=True) == created.get_data(as_text=True)

        deleted = flask_client.delete(
            f"/v1/invoices/{invoice_id}", headers={"APItoken": api_token}
        )
        assert deleted.status_code == HTTPStatus.NO_CONTENT
        assert deleted.get_data(as_text=True) == ""

        gone = (
            sb.table("api_invoices")
            .select("id, deleted")
            .eq("id", invoice_id)
            .limit(1)
            .execute()
        )
        assert gone.data and gone.data[0]["deleted"] is True

    finally:
        if invoice_id is not None:
            sb.table("api_invoices").delete().eq("id", invoice_id).execute()
        if template_invoice_id is not None:
            sb.table("api_invoices").delete().eq("id", template_invoice_id).execute()
        sb.table("api_groups").delete().eq("group_name", group_name).execute()