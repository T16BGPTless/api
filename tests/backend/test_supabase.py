"""Supabase integration tests."""

import sys
import uuid
from pathlib import Path
from http import HTTPStatus

import pytest
from postgrest.exceptions import APIError

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


def test_auth_register_creates_group_row(flask_client, sb, valid_dev_token):
    """Test that registering a group creates a group row in the database."""
    group_name = f"pytest-{uuid.uuid4().hex}"
    try:
        resp = flask_client.post(
            "/v1/auth/register",
            headers={"APIdevToken": valid_dev_token},
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

        template_payload_full = {
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
        template_payload_minimal = {
            "owner_token": group_id,
            "template_id": "",
            "xml": "<TemplateInvoice/>",
            "deleted": False,
        }
        used_minimal_insert = False
        try:
            template = sb.table("api_invoices").insert(template_payload_full).execute()
        except APIError as e:
            if "invoice_data" in str(e) and "PGRST204" in str(e):
                # Schema cache may not list invoice_data; try without it (DB default used)
                try:
                    template = (
                        sb.table("api_invoices")
                        .insert(template_payload_minimal)
                        .execute()
                    )
                    used_minimal_insert = True
                except APIError:
                    pytest.skip(
                        "api_invoices.invoice_data missing (run: supabase db reset)"
                    )
            else:
                raise
        template_invoice_id = template.data[0]["id"]

        # If we had to omit invoice_data, the generate endpoint will 500 (same schema cache)
        if used_minimal_insert:
            pytest.skip("Schema cache missing invoice_data (run: supabase db reset)")

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


def test_order_xml_to_json_stored_then_to_invoice_xml(flask_client, sb):
    """Integration: user provides order XML -> convert to JSON -> use as InvoiceData -> generate invoice XML."""
    from app.services.order_to_invoice import order_json_to_invoice_data

    example_path = Path(__file__).resolve().parents[2] / "docs" / "orderdocexample.xml"
    if not example_path.exists():
        pytest.skip("docs/orderdocexample.xml not found")

    order_xml = example_path.read_text(encoding="utf-8")
    group_name = f"pytest-order-{uuid.uuid4().hex}"
    api_token = uuid.uuid4().hex
    invoice_id = None

    try:
        group = (
            sb.table("api_groups")
            .insert({"group_name": group_name, "api_token": api_token})
            .execute()
        )
        group_id = group.data[0]["id"]

        # 1. User provides order XML -> convert to JSON (stored in variable, then used as payload)
        convert_resp = flask_client.post(
            "/v1/orders/convert",
            data=order_xml,
            content_type="application/xml",
            headers={"APItoken": api_token},
        )
        assert convert_resp.status_code == 200, convert_resp.get_data(as_text=True)
        order_json = convert_resp.get_json()

        # 2. Map order JSON to InvoiceData shape and send to generate
        invoice_data = order_json
        assert "supplier" in invoice_data["InvoiceData"] and "customer" in invoice_data["InvoiceData"]
        assert invoice_data["InvoiceData"]["supplier"].get("name") and invoice_data["InvoiceData"]["customer"].get(
            "name"
        )
        assert invoice_data["InvoiceData"]["lines"]

        generate_resp = flask_client.post(
            "/v1/invoices/generate",
            headers={"APItoken": api_token},
            json=invoice_data,
        )
        if generate_resp.status_code == 500:
            body = generate_resp.get_json() or {}
            msg = body.get("message", "")
            if "Database error" in msg or "SUPABASE" in msg:
                pytest.skip(
                    "App could not reach database during request (ensure SUPABASE_URL and "
                    "SUPABASE_SERVICE_ROLE_KEY are set for the process running the app)"
                )
        assert generate_resp.status_code == 201, generate_resp.get_data(as_text=True)
        invoice_xml_body = generate_resp.get_data(as_text=True)
        assert "<?xml" in invoice_xml_body
        assert "Invoice" in invoice_xml_body
        # Order example has IYT Corporation (buyer) and Consortial (seller)
        assert (
            "IYT" in invoice_xml_body
            or "Consortial" in invoice_xml_body
            or "Corporation" in invoice_xml_body
        )

        # 3. Verify invoice was stored: list and get
        list_resp = flask_client.get("/v1/invoices", headers={"APItoken": api_token})
        assert list_resp.status_code == 200
        ids = list_resp.get_json()
        assert isinstance(ids, list)
        invoice_id = next((i for i in ids if i), None)
        if invoice_id is not None:
            get_resp = flask_client.get(
                f"/v1/invoices/{invoice_id}",
                headers={"APItoken": api_token},
            )
            assert get_resp.status_code == 200
            assert get_resp.get_data(as_text=True) == invoice_xml_body
    finally:
        if invoice_id is not None:
            sb.table("api_invoices").delete().eq("id", invoice_id).execute()
        sb.table("api_groups").delete().eq("group_name", group_name).execute()
