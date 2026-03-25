"""Invoice notification helpers (CloudConvert -> PDF, Resend -> email)."""

from __future__ import annotations

import base64
import os
import time
from typing import Any

import httpx
from email_validator import EmailNotValidError, validate_email


def is_valid_email(value: object) -> bool:
    """Validate an email address for API input checks."""
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        validate_email(value, check_deliverability=True)
        return True
    except EmailNotValidError:
        return False


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def convert_invoice_xml_to_pdf(xml_str: str) -> bytes:
    """
    Convert UBL invoice XML to a PDF using CloudConvert.

    CloudConvert flow:
    - import/base64 -> convert (output_format=pdf) -> export/url
    - download the exported PDF from the signed URL
    """
    api_key = _require_env("CLOUDCONVERT_API_KEY")

    # CloudConvert supports importing base64 for reasonably sized files.
    b64 = base64.b64encode(xml_str.encode("utf-8")).decode("ascii")

    tasks: dict[str, Any] = {
        "import-invoice": {
            "operation": "import/base64",
            "file": b64,
            "filename": "invoice.xml",
        },
        "convert-invoice": {
            "operation": "convert",
            "input": "import-invoice",
            "output_format": "pdf",
        },
        "export-invoice": {
            "operation": "export/url",
            "input": "convert-invoice",
        },
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=20) as client:
        create = client.post(
            "https://api.cloudconvert.com/v2/jobs",
            headers=headers,
            json={"tasks": tasks},
        )
        create.raise_for_status()
        create_data = create.json().get("data") or {}
        job_id = create_data.get("id")
        if not job_id:
            raise RuntimeError("CloudConvert did not return a job id")

        deadline_s = time.time() + 30  # keep polling bounded in serverless
        pdf_url: str | None = None

        while time.time() < deadline_s:
            status_resp = client.get(
                f"https://sync.api.cloudconvert.com/v2/jobs/{job_id}",
                headers=headers,
            )
            status_resp.raise_for_status()
            status_data = status_resp.json().get("data") or {}
            status = status_data.get("status")

            if status == "finished":
                for task in status_data.get("tasks") or []:
                    # export/url task holds the signed download URL in result.files[0].url
                    result = task.get("result") or {}
                    files = result.get("files") or []
                    if files:
                        candidate = files[0].get("url")
                        if candidate:
                            pdf_url = candidate
                            break
                break

            if status in ("error", "failed"):
                raise RuntimeError(f"CloudConvert job failed: {status_data}")

            time.sleep(1.0)

        if not pdf_url:
            raise RuntimeError("CloudConvert did not produce a PDF download URL in time")

        pdf_resp = client.get(pdf_url, timeout=30)
        pdf_resp.raise_for_status()
        return pdf_resp.content


def send_invoice_notification(
    *,
    recipient_email: str,
    invoice_id: str,
    pdf_bytes: bytes,
) -> None:
    """Send the invoice PDF to `recipient_email` using Resend."""
    api_key = _require_env("RESEND_API_KEY")
    from_email = _require_env("RESEND_FROM_EMAIL")

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
        "to": [recipient_email],
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
        resp = client.post("https://api.resend.com/emails", headers=headers, json=payload)
        resp.raise_for_status()

        # Resend returns JSON; we don't need the exact content for the route contract.
        _ = resp.json()
