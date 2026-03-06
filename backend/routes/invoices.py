from flask import Blueprint, jsonify, request, Response
from http import HTTPStatus

invoices_bp = Blueprint("invoices", __name__)

# Example of storage (might be modified later when it comes to persistence)
VALID_API_TOKENS = {"abc123"}
INVOICES = {
    12345: {"owner": "abc123", "xml": "<Invoice><ID>12345</ID></Invoice>"},
    54321: {"owner": "abc123", "xml": "<Invoice><ID>54321</ID></Invoice>"}
}

# The XML layout (Needs to be changed later)
TEMPLATES = {
    "template1": {"owner": "abc123"},
    "template2": {"owner": "other_token"}
}

# ------------------- POST /v1/invoice/generate  -------------------
@invoices_bp.route("/v1/invoices/generate", methods=["POST"])
def generate_invoice():

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or api_token not in VALID_API_TOKENS:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    body = request.get_json(silent=True) or {}
    template_id = body.get("templateInvoice")
    invoice_data = body.get("InvoiceData")

    # Check template exists (404)
    if template_id not in TEMPLATES:
        return (
            jsonify({
                "error": "NOT_FOUND",
                "message": "The requested resource was not found"
            }),
            HTTPStatus.NOT_FOUND,
        )

    # Check permission (403)
    if TEMPLATES[template_id]["owner"] != api_token:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    try:
        # TODO: XML layout here (Olivianne)
        xml = f"""
            <Invoice>
                <Template>{template_id}</Template>
            </Invoice>
            """.strip()

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

    if not api_token or api_token not in VALID_API_TOKENS:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    # Get invoices owned by this API token
    invoice_ids = []

    for invoice_id in INVOICES:
        if INVOICES[invoice_id]["owner"] == api_token:
            invoice_ids.append(invoice_id)

    return (
        jsonify(invoice_ids),
        HTTPStatus.OK,
    )

# ------------------- GET /v1/invoices/<int:invoiceID> -------------------
@invoices_bp.route("/v1/invoices/<int:invoiceID>", methods=["GET"])
def get_invoice(invoiceID):

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or api_token not in VALID_API_TOKENS:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    # Check invoice exists (404)
    if invoiceID not in INVOICES:
        return (
            jsonify({
                "error": "NOT_FOUND",
                "message": "The requested resource was not found"
            }),
            HTTPStatus.NOT_FOUND,
        )

    invoice = INVOICES[invoiceID]

    # Check permission (403)
    if invoice["owner"] != api_token:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    return Response(
        invoice["xml"],
        mimetype="application/xml",
        status=HTTPStatus.OK,
    )

# ------------------- DELETE /v1/invoices/<int:invoiceID> -------------------
@invoices_bp.route("/v1/invoices/<int:invoiceID>", methods=["DELETE"])
def delete_invoice(invoiceID):

    # Validate API token (401)
    api_token = request.headers.get("APItoken")

    if not api_token or api_token not in VALID_API_TOKENS:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    # Check invoice exists (404)
    if invoiceID not in INVOICES:
        return (
            jsonify({
                "error": "NOT_FOUND",
                "message": "The requested resource was not found"
            }),
            HTTPStatus.NOT_FOUND,
        )

    invoice = INVOICES[invoiceID]

    # Check permission (403)
    if invoice["owner"] != api_token:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    deleted_xml = invoice["xml"]

    # Delete invoice
    del INVOICES[invoiceID]

    return Response(
        deleted_xml,
        mimetype="application/xml",
        status=HTTPStatus.OK,
    )