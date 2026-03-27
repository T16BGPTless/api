"""Invoice notification helpers (invoice_data -> HTML -> PDF, Resend -> email)."""

from __future__ import annotations

import base64
import io
import os

import httpx
from email_validator import EmailNotValidError, validate_email
from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa


def is_valid_email(value: object) -> bool:
    """Validate an email address for API input checks."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        validate_email(value, check_deliverability=True)
        return True
    except EmailNotValidError:
        return False


def require_env(name: str) -> str:
    """Require an environment variable to be set."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def render_invoice_html(*, invoice_id: str, invoice_data: dict) -> str:
    """Render invoice HTML from stored `invoice_data`."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    templates_dir = os.path.join(base_dir, "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("invoice_pdf.html")

    supplier = invoice_data.get("supplier") or {}
    customer = invoice_data.get("customer") or {}
    lines = invoice_data.get("lines") or []

    return template.render(
        invoice_id=invoice_id,
        issue_date=invoice_data.get("issueDate", ""),
        due_date=invoice_data.get("dueDate", ""),
        currency=invoice_data.get("currency", ""),
        total_amount=invoice_data.get("totalAmount", ""),
        supplier_name=supplier.get("name", ""),
        supplier_abn=supplier.get("ABN", ""),
        customer_name=customer.get("name", ""),
        customer_abn=customer.get("ABN", ""),
        lines=lines,
    )


def convert_html_to_pdf_bytes(html: str) -> bytes:
    """Convert HTML to PDF bytes using xhtml2pdf."""
    out = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("Failed to render PDF")
    return out.getvalue()


def invoice_data_to_pdf_bytes(*, invoice_id: str, invoice_data: dict) -> bytes:
    """High-level helper to render HTML and convert to PDF."""
    html = render_invoice_html(invoice_id=invoice_id, invoice_data=invoice_data)
    return convert_html_to_pdf_bytes(html)


def send_invoice_notification(
    *,
    recipient_email: str,
    invoice_id: str,
    pdf_bytes: bytes,
) -> None:
    """Send the invoice PDF to `recipient_email` using Resend."""
    api_key = require_env("RESEND_API_KEY")
    from_email = require_env("RESEND_FROM_EMAIL")
    override_to = os.environ.get("RESEND_TO_EMAIL", "").strip()
    to_email = override_to or recipient_email

    subject = f"Invoice {invoice_id}"
    html = (
        f"<p>Please find your invoice <strong>{invoice_id}</strong> attached.</p>"
        "<p>Thank you.</p>"
    )
    text = f"Please find your invoice {invoice_id} attached."

    filename = f"invoice-{invoice_id}.pdf"
    pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
        "attachments": [
            {
                "filename": filename,
                "content": pdf_b64,
                "content_type": "application/pdf",
            }
        ],
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(
            "https://api.resend.com/emails", headers=headers, json=payload
        )
        resp.raise_for_status()

        # Resend returns JSON; we don't need the exact content for the route contract.
        _ = resp.json()
