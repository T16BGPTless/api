"""Invoices routes."""

from http import HTTPStatus
from flask import Blueprint, jsonify, request, Response
from app.services.invoice_xml import build_invoice_xml
from app.routes.helpers import (
    sb_has_error,
    sb_execute,
    get_db,
    return_error,
    is_valid_api_token,
)

invoices_bp = Blueprint("invoices", __name__)


def require_api_token():
    """Get Supabase client and validate APItoken header."""
    supabase = get_db()
    if supabase is None:
        return None, None, return_error("INTERNAL_SERVER_ERROR")

    api_token = request.headers.get("APItoken")
    if not api_token or not is_valid_api_token(supabase, api_token):
        return supabase, None, return_error("UNAUTHORIZED")

    return supabase, api_token, None

def get_group_id_from_token(supabase, api_token):
    """Helper to get group name from API token."""
    resp = (
        supabase.table("api_groups")
        .select("id")
        .eq("api_token", api_token)
        .limit(1)
    )
    resp_exec = sb_execute(resp)
    if resp_exec is None or sb_has_error(resp_exec) or not resp_exec.data:
        return return_error("UNAUTHORIZED")
    return resp_exec.data[0].get("id")


# ------------------- POST /v1/invoice/generate  -------------------
@invoices_bp.route("/v1/invoices/generate", methods=["POST"])
def generate_invoice():  # pylint: disable=too-many-return-statements
    """Generate an invoice."""
    supabase, api_token, error = require_api_token()
    if error is not None:
        return error

    body = request.get_json(silent=True) or {}
    template_id = body.get("templateInvoice")
    if template_id is None:
        template_id = ""
    invoice_data = body.get("InvoiceData")

    # Check template exists (404) and permission (403)
    if template_id:
        tmpl_rows = (
            supabase.table("api_invoices")
            .select("owner_token")
            .eq("id", template_id)
        )
        tmpl_rows_resp = sb_execute(tmpl_rows)
        if tmpl_rows_resp is None or sb_has_error(tmpl_rows_resp):
            return return_error("INTERNAL_SERVER_ERROR")

        if not tmpl_rows_resp.data:
            return return_error("NOT_FOUND")

        group_id = get_group_id_from_token(supabase, api_token)

        if not any(row.get("owner_token") == group_id for row in tmpl_rows_resp.data):
            return return_error("FORBIDDEN")

    try:
        # If template exists, merge its invoice_data with the request's InvoiceData (request takes precedence)
        if template_id:
            template_resp = sb_execute(
                supabase.table("api_invoices")
                .select("invoice_data")
                .eq("id", template_id)
                .limit(1)
            )
            
            # Extract the inner JSON data (default to empty dict if missing)
            template_data = {}
            if template_resp and template_resp.data:
                template_data = template_resp.data[0].get("invoice_data") or {}

            # Merge request data ON TOP of template data
            if isinstance(template_data, dict):
                merged_data = template_data.copy()
            else:
                merged_data = {}

            if invoice_data:
                merged_data.update(invoice_data)
            
            invoice_data = merged_data

        group_id = get_group_id_from_token(supabase, api_token)

        created = supabase.table("api_invoices").insert(
            {
                "owner_token": group_id,
                "template_id": template_id,
                "xml": "None",
                "deleted": True,
                "invoice_data": invoice_data,
            }
        )
        created_resp = sb_execute(created)
        if created_resp is None or sb_has_error(created_resp):
            return return_error("INTERNAL_SERVER_ERROR")
        
        invoice_id = created_resp.data[0].get("id")
        if invoice_id is None:
            return return_error("INTERNAL_SERVER_ERROR")
        invoice_data["invoiceID"] = str(invoice_id)
        xml = build_invoice_xml(invoice_data)
        # Update the row with the generated XML and mark it as not deleted
        updated = (
            supabase.table("api_invoices")
            .update({"xml": xml, "deleted": False})
            .eq("id", invoice_id)
        )
        updated_resp = sb_execute(updated)
        if updated_resp is None or sb_has_error(updated_resp):
            return return_error("INTERNAL_SERVER_ERROR")

    except ValueError as e:
        return (
            jsonify({"error": "BAD_REQUEST", "message": str(e)}),
            HTTPStatus.BAD_REQUEST,
        )

    return Response(
        xml,
        mimetype="application/xml",
        status=HTTPStatus.CREATED,
    )


# ------------------- GET /v1/invoices  -------------------
@invoices_bp.route("/v1/invoices", methods=["GET"])
def list_invoices():
    """List invoices."""
    supabase, api_token, error = require_api_token()
    if error is not None:
        return error

    group_id = get_group_id_from_token(supabase, api_token)

    # Get invoices owned by this API token, not deleted
    resp = (
        supabase.table("api_invoices")
        .select("id")
        .eq("owner_token", group_id)
        .eq("deleted", False)
        .order("id", desc=False)
    )
    resp_exec = sb_execute(resp)
    if resp_exec is None or sb_has_error(resp_exec):
        return return_error("INTERNAL_SERVER_ERROR")

    invoice_ids = [row.get("id") for row in (resp_exec.data or [])]

    return (
        jsonify(invoice_ids),
        HTTPStatus.OK,
    )


# ------------------- GET /v1/invoices/<int:invoice_id> -------------------
@invoices_bp.route("/v1/invoices/<int:invoice_id>", methods=["GET"])
def get_invoice(invoice_id):  # pylint: disable=too-many-return-statements
    """Get an invoice."""
    supabase, api_token, error = require_api_token()
    if error is not None:
        return error

    resp = (
        supabase.table("api_invoices")
        .select("owner_token, xml, deleted")
        .eq("id", invoice_id)
        .limit(1)
    )
    resp_exec = sb_execute(resp)
    if resp_exec is None or sb_has_error(resp_exec):
        return return_error("INTERNAL_SERVER_ERROR")

    if not resp_exec.data:
        return return_error("NOT_FOUND")

    invoice = resp_exec.data[0]

    # Treat soft-deleted invoices as not found
    if invoice.get("deleted"):
        return return_error("NOT_FOUND")

    group_id = get_group_id_from_token(supabase, api_token)

    # Check permission (403)
    if invoice.get("owner_token") != group_id:
        return return_error("FORBIDDEN")

    return Response(
        invoice.get("xml") or "",
        mimetype="application/xml",
        status=HTTPStatus.OK,
    )


# ------------------- DELETE /v1/invoices/<int:invoice_id> -------------------
@invoices_bp.route("/v1/invoices/<int:invoice_id>", methods=["DELETE"])
def delete_invoice(invoice_id):  # pylint: disable=too-many-return-statements
    """Soft-delete an invoice (flag as deleted)."""
    supabase, api_token, error = require_api_token()
    if error is not None:
        return error

    existing = (
        supabase.table("api_invoices")
        .select("owner_token, xml, deleted")
        .eq("id", invoice_id)
        .limit(1)
    )
    existing_exec = sb_execute(existing)
    if existing_exec is None or sb_has_error(existing_exec):
        return return_error("INTERNAL_SERVER_ERROR")

    if not existing_exec.data:
        return return_error("NOT_FOUND")

    invoice = existing_exec.data[0]

    # Treat already-deleted invoices as not found
    if invoice.get("deleted"):
        return return_error("NOT_FOUND")

    group_id = get_group_id_from_token(supabase, api_token)

    # Check permission (403)
    if invoice.get("owner_token") != group_id:
        return return_error("FORBIDDEN")

    # Soft-delete: mark the row as deleted instead of removing it
    deleted = (
        supabase.table("api_invoices").update({"deleted": True}).eq("id", invoice_id)
    )
    deleted_exec = sb_execute(deleted)
    if deleted_exec is None or sb_has_error(deleted_exec):
        return return_error("INTERNAL_SERVER_ERROR")

    return "", HTTPStatus.NO_CONTENT
