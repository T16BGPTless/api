"""Helper functions for the routes."""

from http import HTTPStatus
from postgrest.exceptions import APIError
from flask import jsonify
from app.db.supabase_client import get_supabase


def sb_has_error(resp) -> bool:
    """Check if the response has an error."""
    return getattr(resp, "error", None) is not None


def sb_execute(builder):
    """Execute the builder."""
    try:
        return builder.execute()
    except APIError:
        return None


def get_db():
    """Get a Supabase client, or None if misconfigured."""
    try:
        return get_supabase()
    except ValueError:
        return None


def return_error(error: str):
    """Return an error response."""
    if error == "INTERNAL_SERVER_ERROR":
        message = "Database error (check SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY)"
        status = HTTPStatus.INTERNAL_SERVER_ERROR
    elif error == "UNAUTHORIZED":
        message = (
            "The API token is missing or invalid. "
            "If you do not have an API token register for one "
            "through the forum on our website"
        )
        status = HTTPStatus.UNAUTHORIZED
    elif error == "FORBIDDEN":
        message = "You do not have access to this content"
        status = HTTPStatus.FORBIDDEN
    elif error == "NOT_FOUND":
        message = "The requested resource was not found"
        status = HTTPStatus.NOT_FOUND
    elif error == "GROUP_NOT_FOUND":
        message = "groupName not found registered"
        status = HTTPStatus.NOT_FOUND
    elif error == "GROUP_ALREADY_REGISTERED":
        message = "groupName already registered"
        status = HTTPStatus.CONFLICT
    elif error == "GROUP_NAME_REQUIRED":
        message = "groupName is required"
        status = HTTPStatus.BAD_REQUEST
    else:
        message = "An unknown error occurred"
        status = HTTPStatus.INTERNAL_SERVER_ERROR
    return jsonify(
        {
            "error": error,
            "message": message,
        }
    ), status
