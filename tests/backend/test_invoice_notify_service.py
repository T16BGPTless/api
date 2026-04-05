"""Unit tests for invoice notification helper functions."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from email_validator import EmailNotValidError

from app.services.invoice_notify import (
    convert_html_to_pdf_bytes,
    invoice_data_to_pdf_bytes,
    is_blocked_educational_domain,
    is_valid_email,
    require_env,
    render_invoice_html,
    send_invoice_notification,
)


def test_is_blocked_educational_domain_matches_explicit_domain():
    assert is_blocked_educational_domain("ad.unsw.edu.au") is True


@pytest.mark.parametrize("domain", ["student.edu.au", "student.ac.uk", "student.edu"])
def test_is_blocked_educational_domain_matches_suffix(domain):
    assert is_blocked_educational_domain(domain) is True


def test_is_valid_email_accepts_non_blocked_domain():
    fake_info = SimpleNamespace(domain="example.com")
    with patch("app.services.invoice_notify.validate_email", return_value=fake_info):
        assert is_valid_email("accounts@example.com") is True


def test_is_valid_email_rejects_blocked_domain():
    fake_info = SimpleNamespace(domain="student.unsw.edu.au")
    with patch("app.services.invoice_notify.validate_email", return_value=fake_info):
        assert is_valid_email("student@unsw.edu.au") is False


def test_is_valid_email_rejects_invalid_email():
    with patch(
        "app.services.invoice_notify.validate_email",
        side_effect=EmailNotValidError("bad"),
    ):
        assert is_valid_email("not-an-email") is False


@pytest.mark.parametrize("value", [None, "", "   ", 123])
def test_is_valid_email_rejects_non_string_or_blank(value):
    assert is_valid_email(value) is False


def test_require_env_returns_stripped_value():
    with patch.dict("os.environ", {"RESEND_API_KEY": "  secret-key  "}, clear=True):
        assert require_env("RESEND_API_KEY") == "secret-key"


def test_require_env_missing_raises():
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(RuntimeError, match="Missing required environment variable"):
            require_env("RESEND_API_KEY")


def test_render_invoice_html_includes_invoice_fields():
    html = render_invoice_html(
        invoice_id="123",
        invoice_data={
            "issueDate": "2026-03-25",
            "dueDate": "2026-04-01",
            "currency": "AUD",
            "totalAmount": "110.00",
            "supplier": {"name": "ACME Pty Ltd", "ABN": "12345678901"},
            "customer": {"name": "Example Co", "ABN": "10987654321"},
            "lines": [
                {
                    "description": "Widget",
                    "quantity": 1,
                    "unitPrice": "100.00",
                    "lineTotal": "100.00",
                }
            ],
        },
    )

    assert "123" in html
    assert "ACME Pty Ltd" in html
    assert "Example Co" in html


def test_convert_html_to_pdf_bytes_success():
    def fake_create_pdf(*, src, dest, encoding):
        dest.write(b"%PDF-FAKE%")
        return SimpleNamespace(err=False)

    with patch("app.services.invoice_notify.pisa.CreatePDF", side_effect=fake_create_pdf):
        result = convert_html_to_pdf_bytes("<html><body>Invoice</body></html>")

    assert result == b"%PDF-FAKE%"


def test_convert_html_to_pdf_bytes_failure():
    with patch(
        "app.services.invoice_notify.pisa.CreatePDF",
        return_value=SimpleNamespace(err=True),
    ):
        with pytest.raises(RuntimeError, match="Failed to render PDF"):
            convert_html_to_pdf_bytes("<html><body>Invoice</body></html>")


def test_invoice_data_to_pdf_bytes_delegates_to_render_and_convert():
    with (
        patch("app.services.invoice_notify.render_invoice_html", return_value="<html/>") as mock_render,
        patch("app.services.invoice_notify.convert_html_to_pdf_bytes", return_value=b"%PDF-FAKE%") as mock_convert,
    ):
        result = invoice_data_to_pdf_bytes(
            invoice_id="123",
            invoice_data={"issueDate": "2026-03-25"},
        )

    assert result == b"%PDF-FAKE%"
    mock_render.assert_called_once_with(
        invoice_id="123", invoice_data={"issueDate": "2026-03-25"}
    )
    mock_convert.assert_called_once_with("<html/>")


def test_send_invoice_notification_success():
    mock_response = MagicMock()
    mock_response.content = b'{"id": "email-1"}'
    mock_response.json.return_value = {"id": "email-1"}
    mock_response.raise_for_status.return_value = None

    mock_http_client = MagicMock()
    mock_http_client.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_http_client
    mock_context_manager.__exit__.return_value = False

    with (
        patch.dict(
            "os.environ",
            {
                "RESEND_API_KEY": "api-key",
                "RESEND_FROM_EMAIL": "sender@example.com",
                "RESEND_TO_EMAIL": "ops@example.com",
            },
            clear=True,
        ),
        patch("app.services.invoice_notify.httpx.Client", return_value=mock_context_manager),
    ):
        send_invoice_notification(
            recipient_email="recipient@example.com",
            invoice_id="123",
            pdf_bytes=b"%PDF-FAKE%",
        )

    mock_http_client.post.assert_called_once()
    call_kwargs = mock_http_client.post.call_args.kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer api-key"
    assert call_kwargs["headers"]["User-Agent"] == "gptless-api/1.0"
    assert call_kwargs["json"]["to"] == ["ops@example.com"]
    assert call_kwargs["json"]["attachments"][0]["filename"] == "invoice-123.pdf"
    assert call_kwargs["json"]["attachments"][0]["content_type"] == "application/pdf"


def test_send_invoice_notification_http_error_raises():
    mock_response = MagicMock()
    mock_response.content = b"error"
    mock_response.text = "bad request"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "boom",
        request=MagicMock(),
        response=mock_response,
    )

    mock_http_client = MagicMock()
    mock_http_client.post.return_value = mock_response
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = mock_http_client
    mock_context_manager.__exit__.return_value = False

    with (
        patch.dict(
            "os.environ",
            {
                "RESEND_API_KEY": "api-key",
                "RESEND_FROM_EMAIL": "sender@example.com",
                "RESEND_TO_EMAIL": "ops@example.com",
            },
            clear=True,
        ),
        patch("app.services.invoice_notify.httpx.Client", return_value=mock_context_manager),
    ):
        with pytest.raises(httpx.HTTPStatusError):
            send_invoice_notification(
                recipient_email="recipient@example.com",
                invoice_id="123",
                pdf_bytes=b"%PDF-FAKE%",
            )
