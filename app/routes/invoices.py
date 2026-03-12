from flask import Blueprint, jsonify, request, Response
from http import HTTPStatus
from db.supabase_client import get_supabase
from postgrest.exceptions import APIError
from services.invoice_xml import build_invoice_xml

supabase = get_supabase()

invoices_bp = Blueprint("invoices", __name__)

UNAUTHORIZED_MESSAGE = (
    "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
)


def _sb_has_error(resp) -> bool:
    return getattr(resp, "error", None) is not None


def _sb_execute(builder):
    try:
        return builder.execute()
    except APIError:
        return None


def _is_valid_api_token(api_token: str) -> bool:
    builder = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("api_token", api_token)
        .limit(1)
    )
    resp = _sb_execute(builder)
    if resp is None or _sb_has_error(resp):
        return False
    return bool(resp.data)

# ------------------- POST /v1/invoice/generate  -------------------
@invoices_bp.route("/v1/invoices/generate", methods=["POST"])
def generate_invoice():

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or not _is_valid_api_token(api_token):
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": UNAUTHORIZED_MESSAGE
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    body = request.get_json(silent=True) or {}
    template_id = body.get("templateInvoice")
    invoice_data = body.get("InvoiceData")

    if invoice_data is None:
        return (
            jsonify({"error": "BAD_REQUEST", "message": "InvoiceData is required"}),
            HTTPStatus.BAD_REQUEST,
        )

    # Check template exists (404) and permission (403)
    if template_id:
        tmpl_rows = (
            supabase.table("api_templates")
            .select("owner_token")
            .eq("template_id", template_id)
        )
        tmpl_rows_resp = _sb_execute(tmpl_rows)
        if tmpl_rows_resp is None or _sb_has_error(tmpl_rows_resp):
            return (
                jsonify(
                    {
                        "error": "INTERNAL_SERVER_ERROR",
                        "message": "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
                    }
                ),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        if not tmpl_rows_resp.data:
            return (
                jsonify({
                    "error": "NOT_FOUND",
                    "message": "The requested resource was not found"
                }),
                HTTPStatus.NOT_FOUND,
            )

        if not any(row.get("owner_token") == api_token for row in tmpl_rows_resp.data):
            return (
                jsonify({
                    "error": "FORBIDDEN",
                    "message": "You do not have access to this content"
                }),
                HTTPStatus.FORBIDDEN,
            )

    try:
        # TODO: XML layout here (Olivianne)
        xml = build_invoice_xml(invoice_data)

        created = (
            supabase.table("api_invoices")
            .insert(
                {
                    "owner_token": api_token,
                    "template_id": template_id,
                    "xml": xml,
                }
            )
        )
        created_resp = _sb_execute(created)
        if created_resp is None or _sb_has_error(created_resp):
            return (
                jsonify(
                    {
                        "error": "INTERNAL_SERVER_ERROR",
                        "message": "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
                    }
                ),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    except ValueError as e:
        return (
            jsonify({
                "error": "BAD_REQUEST",
                "message": str(e)
            }),
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

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or not _is_valid_api_token(api_token):
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": UNAUTHORIZED_MESSAGE
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    # Get invoices owned by this API token
    resp = (
        supabase.table("api_invoices")
        .select("id")
        .eq("owner_token", api_token)
        .order("id", desc=False)
    )
    resp_exec = _sb_execute(resp)
    if resp_exec is None or _sb_has_error(resp_exec):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    invoice_ids = [row.get("id") for row in (resp_exec.data or [])]

    return (
        jsonify(invoice_ids),
        HTTPStatus.OK,
    )

# ------------------- GET /v1/invoices/<int:invoiceID> -------------------
@invoices_bp.route("/v1/invoices/<int:invoiceID>", methods=["GET"])
def get_invoice(invoiceID):

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or not _is_valid_api_token(api_token):
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": UNAUTHORIZED_MESSAGE
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    resp = (
        supabase.table("api_invoices")
        .select("owner_token, xml")
        .eq("id", invoiceID)
        .limit(1)
    )
    resp_exec = _sb_execute(resp)
    if resp_exec is None or _sb_has_error(resp_exec):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    if not resp_exec.data:
        return (
            jsonify({
                "error": "NOT_FOUND",
                "message": "The requested resource was not found"
            }),
            HTTPStatus.NOT_FOUND,
        )

    invoice = resp_exec.data[0]

    # Check permission (403)
    if invoice.get("owner_token") != api_token:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    return Response(
        invoice.get("xml") or "",
        mimetype="application/xml",
        status=HTTPStatus.OK,
    )

# ------------------- DELETE /v1/invoices/<int:invoiceID> -------------------
@invoices_bp.route("/v1/invoices/<int:invoiceID>", methods=["DELETE"])
def delete_invoice(invoiceID):

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or not _is_valid_api_token(api_token):
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": UNAUTHORIZED_MESSAGE
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    existing = (
        supabase.table("api_invoices")
        .select("owner_token, xml")
        .eq("id", invoiceID)
        .limit(1)
    )
    existing_exec = _sb_execute(existing)
    if existing_exec is None or _sb_has_error(existing_exec):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    if not existing_exec.data:
        return (
            jsonify({
                "error": "NOT_FOUND",
                "message": "The requested resource was not found"
            }),
            HTTPStatus.NOT_FOUND,
        )

    invoice = existing_exec.data[0]

    # Check permission (403)
    if invoice.get("owner_token") != api_token:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    deleted_xml = invoice.get("xml") or ""

    deleted = (
        supabase.table("api_invoices").delete().eq("id", invoiceID)
    )
    deleted_exec = _sb_execute(deleted)
    if deleted_exec is None or _sb_has_error(deleted_exec):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return Response(
        deleted_xml,
        mimetype="application/xml",
        status=HTTPStatus.OK,
    )