"""Order document routes (e.g. XML to JSON conversion)."""

from http import HTTPStatus

from flask import Blueprint, jsonify, request

from app.services.order_xml import order_xml_to_json

orders_bp = Blueprint("orders", __name__)


# ------------------- POST /v1/orders/convert -------------------
@orders_bp.route("/v1/orders/convert", methods=["POST"])
def convert_order_to_json():
    """
    Convert a UBL Order XML document to JSON.

    Request body: raw XML (Content-Type: application/xml or text/xml).
    Response: JSON object suitable for storage or downstream use.
    """
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
    except ValueError as e:
        return (
            jsonify({"error": "BAD_REQUEST", "message": str(e)}),
            HTTPStatus.BAD_REQUEST,
        )
    return jsonify(data), HTTPStatus.OK
