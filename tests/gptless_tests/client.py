"""Black-box API client for pytest suites in tests/gptless_tests."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ApiResponse:
    """Normalized HTTP response object used by tests."""

    status_code: int
    headers: dict[str, str]
    body: str

    def json(self) -> dict[str, Any] | list[Any]:
        """Decode body as JSON."""
        return json.loads(self.body)


class InvoicingApiClient:
    """Small HTTP client wrapper for black-box API testing."""

    def __init__(
        self,
        base_url: str,
        api_token: str | None = None,
        timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.timeout_seconds = timeout_seconds

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        body: str | None = None,
    ) -> ApiResponse:
        request_headers = headers.copy() if headers else {}
        if body is not None and "Content-Type" not in request_headers:
            request_headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            url=f"{self.base_url}{path}",
            method=method,
            headers=request_headers,
            data=body.encode("utf-8") if body is not None else None,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                payload = resp.read().decode("utf-8")
                return ApiResponse(
                    status_code=resp.status,
                    headers=dict(resp.headers.items()),
                    body=payload,
                )
        except urllib.error.HTTPError as exc:
            payload = exc.read().decode("utf-8") if exc.fp else ""
            return ApiResponse(
                status_code=exc.code,
                headers=dict(exc.headers.items()) if exc.headers else {},
                body=payload,
            )

    def list_invoices(self, *, with_auth: bool = True) -> ApiResponse:
        headers = {}
        if with_auth and self.api_token:
            headers["APItoken"] = self.api_token
        return self._request("GET", "/v1/invoices", headers=headers)

    def get_invoice(self, invoice_id: str, *, with_auth: bool = True) -> ApiResponse:
        headers = {}
        if with_auth and self.api_token:
            headers["APItoken"] = self.api_token
        return self._request("GET", f"/v1/invoices/{invoice_id}", headers=headers)

    def delete_invoice(self, invoice_id: str, *, with_auth: bool = True) -> ApiResponse:
        headers = {}
        if with_auth and self.api_token:
            headers["APItoken"] = self.api_token
        return self._request("DELETE", f"/v1/invoices/{invoice_id}", headers=headers)

    def generate_invoice(
        self, payload: dict[str, Any], *, with_auth: bool = True
    ) -> ApiResponse:
        headers = {"Accept": "application/xml"}
        if with_auth and self.api_token:
            headers["APItoken"] = self.api_token
        return self._request(
            "POST",
            "/v1/invoices/generate",
            headers=headers,
            body=json.dumps(payload),
        )

    def convert_order(self, xml_payload: str, *, with_auth: bool = True) -> ApiResponse:
        headers = {"Content-Type": "application/xml"}
        if with_auth and self.api_token:
            headers["APItoken"] = self.api_token
        return self._request("POST", "/v1/orders/convert", headers=headers, body=xml_payload)
