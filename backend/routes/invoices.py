from flask import Blueprint, jsonify, request, Response
from http import HTTPStatus

invoices_bp = Blueprint("invoices", __name__)

# Temporary token store for prototype
VALID_API_TOKENS = {"demo-token-123"}

@invoices_bp.route("/v1/invoices/generate", methods=["POST"])
def generate_invoice():

    # Validate API token
    api_token = request.headers.get("APItoken")

    if not api_token or api_token not in VALID_API_TOKENS:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    body = request.get_json(force=True, silent=True) or {}
    template_id = body.get("templateInvoice")
    invoice_data = body.get("invoiceData")

    # Validate required fields
    if not template_id or not invoice_data:
        return (
            jsonify({
                "error": "BAD_REQUEST",
                "message": "templateInvoice and invoiceData are required"
            }),
            HTTPStatus.BAD_REQUEST,
        )

    try:
        #TODO: Add xml bit here
        xml = "<Invoice></Invoice>"
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