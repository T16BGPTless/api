"""Helper functions for the routes."""

from http import HTTPStatus
from postgrest.exceptions import APIError
from flask import jsonify, request, Response
from supabase import Client
from app.db.supabase_client import get_supabase

VALID_DEV_TOKENS = {"dev-secret"}


def sb_has_error(resp: dict) -> bool:
    """Check if the response has an error."""
    return getattr(resp, "error", None) is not None


def sb_execute(builder: Client) -> dict | None:
    """Execute the builder."""
    try:
        return builder.execute()
    except APIError:
        return None


def get_db() -> Client | None:
    """Get a Supabase client, or None if misconfigured."""
    try:
        return get_supabase()
    except ValueError:
        return None


def return_error(error: str) -> tuple[Response, int]:
    """Return an error response."""
    # Use dict lookup table
    error_map = {
        "INTERNAL_SERVER_ERROR": (
            HTTPStatus.INTERNAL_SERVER_ERROR,
            "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)",
        ),
        "UNAUTHORIZED": (
            HTTPStatus.UNAUTHORIZED,
            "The API token is missing or invalid. "
            "If you do not have an API token register for one through the forum on our website",
        ),
        "FORBIDDEN": (HTTPStatus.FORBIDDEN, "You do not have access to this content"),
        "NOT_FOUND": (HTTPStatus.NOT_FOUND, "The requested resource was not found"),
        "GROUP_NOT_FOUND": (HTTPStatus.NOT_FOUND, "groupName not found registered"),
        "GROUP_ALREADY_REGISTERED": (
            HTTPStatus.CONFLICT,
            "groupName already registered",
        ),
        "GROUP_NAME_REQUIRED": (HTTPStatus.BAD_REQUEST, "groupName is required"),
        "UNKNOWN": (HTTPStatus.INTERNAL_SERVER_ERROR, "An unknown error occurred"),
    }
    status, message = error_map.get(error, error_map["UNKNOWN"])
    return jsonify(
        {
            "error": error,
            "message": message,
        }
    ), status


def require_dev_token_and_group() -> tuple[Client, str, Response | None]:
    """Validate developer token and group name."""
    supabase = get_db()
    if supabase is None:
        return None, None, return_error("INTERNAL_SERVER_ERROR")

    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return supabase, None, return_error("UNAUTHORIZED")

    if dev_token not in VALID_DEV_TOKENS:
        return supabase, None, return_error("FORBIDDEN")

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return supabase, None, return_error("GROUP_NAME_REQUIRED")

    return supabase, group_name, None


def is_valid_api_token(supabase: Client, api_token: str) -> bool:
    """Check if the API token is valid (exists in api_groups)."""
    if not api_token:
        return False
    builder = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("api_token", api_token)
        .limit(1)
    )
    resp = sb_execute(builder)
    if resp is None or sb_has_error(resp):
        return False
    return bool(resp.data)
