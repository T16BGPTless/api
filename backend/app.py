from flask import Flask, jsonify, request
from http import HTTPStatus
import uuid
from datetime import date, datetime


def create_app() -> Flask:
    app = Flask(__name__)

    # In-memory stores for this prototype.
    invoices = {}
    credits = {}

    def _now_date() -> str:
        return date.today().isoformat()

    @app.route("/v1/invoices/generate", methods=["POST"])
    def generate_invoice():
        data = request.get_json(force=True, silent=True) or {}
        order_document = data.get("orderDocument")
        user_data = data.get("userData")
        contract_reference = data.get("contractReference")

        if not order_document or not user_data or not contract_reference:
            return (
                jsonify(
                    {
                        "code": "BAD_REQUEST",
                        "message": "orderDocument, userData and contractReference are required",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )

        # In a real implementation, contract lookup, pricing, and validation would occur here.
        invoice_id = str(uuid.uuid4())
        invoice = {
            "invoiceId": invoice_id,
            "status": "DRAFT",
            "customerId": user_data.get("customerId"),
            "issueDate": _now_date(),
            "dueDate": user_data.get("dueDate"),
            "totalAmount": user_data.get("totalAmount", 0),
            "currency": user_data.get("currency", "AUD"),
            "lines": user_data.get("lines", []),
            "creditsApplied": [],
        }
        invoices[invoice_id] = invoice
        return jsonify(invoice), HTTPStatus.CREATED

    @app.route("/v1/invoices", methods=["GET"])
    def list_invoices():
        limit = request.args.get("limit", type=int)
        # Filtering parameters are accepted but not fully implemented in this prototype.
        all_invoices = list(invoices.values())
        if limit is not None:
            all_invoices = all_invoices[:limit]
        summaries = [
            {
                "invoiceId": inv["invoiceId"],
                "status": inv["status"],
                "customerId": inv.get("customerId"),
                "issueDate": inv.get("issueDate"),
                "totalAmount": inv.get("totalAmount"),
            }
            for inv in all_invoices
        ]
        return jsonify(summaries), HTTPStatus.OK

    @app.route("/v1/invoices/<invoice_id>", methods=["GET"])
    def get_invoice(invoice_id: str):
        invoice = invoices.get(invoice_id)
        if not invoice:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        return jsonify(invoice), HTTPStatus.OK

    @app.route("/v1/invoices/<invoice_id>", methods=["PUT"])
    def update_invoice(invoice_id: str):
        invoice = invoices.get(invoice_id)
        if not invoice:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        if invoice.get("status") in {"FINAL", "EXPORTED"}:
            return (
                jsonify(
                    {
                        "code": "CONFLICT",
                        "message": "Cannot modify a finalised/exported invoice",
                    }
                ),
                HTTPStatus.CONFLICT,
            )
        body = request.get_json(force=True, silent=True) or {}
        # Apply shallow updates to the invoice.
        invoice.update(body)
        invoices[invoice_id] = invoice
        return jsonify(invoice), HTTPStatus.OK

    @app.route("/v1/invoices/<invoice_id>", methods=["DELETE"])
    def delete_invoice(invoice_id: str):
        invoice = invoices.get(invoice_id)
        if not invoice:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        if invoice.get("status") in {"FINAL", "EXPORTED"}:
            return (
                jsonify(
                    {
                        "code": "CONFLICT",
                        "message": "Cannot delete a finalised/exported invoice",
                    }
                ),
                HTTPStatus.CONFLICT,
            )
        invoices.pop(invoice_id, None)
        return ("", HTTPStatus.NO_CONTENT)

    @app.route("/v1/invoices/<invoice_id>/export", methods=["GET"])
    def export_invoice(invoice_id: str):
        invoice = invoices.get(invoice_id)
        if not invoice:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        # Placeholder UBL XML representation for this prototype.
        xml = f"<Invoice><ID>{invoice_id}</ID><Total>{invoice.get('totalAmount')}</Total></Invoice>"
        return app.response_class(xml, mimetype="application/xml", status=HTTPStatus.OK)

    @app.route("/v1/credits", methods=["POST"])
    def create_credit():
        body = request.get_json(force=True, silent=True) or {}
        invoice_id = body.get("invoiceId")
        amount = body.get("amount")
        if not invoice_id or amount is None:
            return (
                jsonify(
                    {
                        "code": "BAD_REQUEST",
                        "message": "invoiceId and amount are required",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )
        if amount <= 0:
            return (
                jsonify(
                    {
                        "code": "BAD_REQUEST",
                        "message": "amount must be positive",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )
        if invoice_id not in invoices:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        credit_id = str(uuid.uuid4())
        credit = {
            "creditId": credit_id,
            "invoiceId": invoice_id,
            "status": "CREATED",
            "amount": amount,
            "createdAt": datetime.utcnow().isoformat() + "Z",
        }
        credits[credit_id] = credit
        return jsonify(credit), HTTPStatus.CREATED

    @app.route("/v1/credits/<credit_id>", methods=["GET"])
    def get_credit(credit_id: str):
        credit = credits.get(credit_id)
        if not credit:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Credit not found"}),
                HTTPStatus.NOT_FOUND,
            )
        return jsonify(credit), HTTPStatus.OK

    @app.route("/v1/invoices/<invoice_id>/apply-credit", methods=["POST"])
    def apply_credit(invoice_id: str):
        invoice = invoices.get(invoice_id)
        if not invoice:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        body = request.get_json(force=True, silent=True) or {}
        credit_id = body.get("creditId")
        amount = body.get("amount")
        if not credit_id or amount is None:
            return (
                jsonify(
                    {
                        "code": "BAD_REQUEST",
                        "message": "creditId and amount are required",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )
        credit = credits.get(credit_id)
        if not credit:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Credit not found"}),
                HTTPStatus.NOT_FOUND,
            )
        if any(c["creditId"] == credit_id for c in invoice.get("creditsApplied", [])):
            return (
                jsonify(
                    {"code": "CONFLICT", "message": "Credit has already been applied"}
                ),
                HTTPStatus.CONFLICT,
            )
        if amount <= 0 or amount > credit.get("amount", 0):
            return (
                jsonify(
                    {
                        "code": "BAD_REQUEST",
                        "message": "Invalid credit amount for application",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )
        if amount > invoice.get("totalAmount", 0):
            return (
                jsonify(
                    {
                        "code": "BAD_REQUEST",
                        "message": "Amount exceeds invoice total",
                    }
                ),
                HTTPStatus.BAD_REQUEST,
            )
        applied_credit = {
            "creditId": credit_id,
            "amount": amount,
        }
        invoice.setdefault("creditsApplied", []).append(applied_credit)
        invoice["totalAmount"] = invoice.get("totalAmount", 0) - amount
        invoices[invoice_id] = invoice
        return jsonify(invoice), HTTPStatus.OK

    @app.route("/v1/invoices/<invoice_id>/status", methods=["POST"])
    def update_invoice_status(invoice_id: str):
        invoice = invoices.get(invoice_id)
        if not invoice:
            return (
                jsonify({"code": "NOT_FOUND", "message": "Invoice not found"}),
                HTTPStatus.NOT_FOUND,
            )
        body = request.get_json(force=True, silent=True) or {}
        current_status = body.get("currentStatus")
        if not current_status:
            return (
                jsonify(
                    {
                        "code": "UNPROCESSABLE_ENTITY",
                        "message": "currentStatus is required",
                    }
                ),
                HTTPStatus.UNPROCESSABLE_ENTITY,
            )
        invoice["status"] = current_status
        invoices[invoice_id] = invoice
        ack = {
            "invoiceId": invoice_id,
            "currentStatus": current_status,
            "message": "Status update recorded",
        }
        return jsonify(ack), HTTPStatus.OK

    return app


app = create_app()

