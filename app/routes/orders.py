"""Order document routes (e.g. XML to JSON conversion)."""

from http import HTTPStatus

from flask import Blueprint, jsonify, request

from app.routes.invoices import require_api_token
from app.services.order_xml import order_xml_to_json
from app.services.order_to_invoice import order_json_to_invoice_data

orders_bp = Blueprint("orders", __name__)


# ------------------- POST /v1/orders/convert -------------------
@orders_bp.route("/v1/orders/convert", methods=["POST"])
def convert_order_to_json():
    """
    Convert a UBL Order XML document to JSON.

    Request body: raw XML (Content-Type: application/xml or text/xml).
    Response: JSON object suitable for storage or downstream use.
    """

    supabase, api_token, error = require_api_token()
    if error is not None:
        return error

    xml_body = request.get_data(as_text=True)
    if not xml_body or not xml_body.strip():
        return (
            jsonify(
                {"error": "BAD_REQUEST", "message": "Request body must contain XML"}
            ),
            HTTPStatus.BAD_REQUEST,
        )
    try:
        data = order_xml_to_json(xml_body)
        data = order_json_to_invoice_data(data)
        data = {"InvoiceData": data}
    except ValueError as e:
        return (
            jsonify({"error": "BAD_REQUEST", "message": str(e)}),
            HTTPStatus.BAD_REQUEST,
        )
    return jsonify(data), HTTPStatus.OK
