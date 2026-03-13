"""
Authorisation methods
"""

from flask import Blueprint, jsonify, request
from http import HTTPStatus
import uuid
from app.db.supabase_client import get_supabase
from postgrest.exceptions import APIError

supabase = get_supabase()

auth_bp = Blueprint("auth", __name__)

# Example of storage (might be modified later when it comes to persistence)
VALID_DEV_TOKENS = {"dev-secret"}

# Store registered groups and their tokens


def sb_has_error(resp) -> bool:
    """Check if the response has an error."""
    return getattr(resp, "error", None) is not None


def sb_execute(builder):
    """Execute the builder."""
    try:
        return builder.execute()
    except APIError:
        return None

# ------------------- POST /v1/auth/register -------------------
@auth_bp.route("/v1/auth/register", methods=["POST"])
def register():
    """Register a new group"""

    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": (
                    "The API token is missing or invalid. "
                    "If you do not have an API token register for one "
                    "through the forum on our website"
                )            }),
            HTTPStatus.UNAUTHORIZED,
        )

    if dev_token not in VALID_DEV_TOKENS:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return (
            jsonify({"error": "BAD_REQUEST", "message": "groupName is required"}),
            HTTPStatus.BAD_REQUEST,
        )

    # Prevent duplicate registrations by group name
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = sb_execute(existing)
    if existing_resp is None or sb_has_error(existing_resp):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    if existing_resp.data:
        return (
            jsonify(
                {
                    "error": "CONFLICT",
                    "message": "groupName already registered",
                }
            ),
            HTTPStatus.CONFLICT,
        )

    # Generate API token
    api_token = uuid.uuid4().hex

    created = (
        supabase.table("api_groups")
        .insert({"group_name": group_name, "api_token": api_token})
    )
    created_resp = sb_execute(created)
    if created_resp is None or sb_has_error(created_resp):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return (
        jsonify({
            "APItoken": api_token
        }),
        HTTPStatus.CREATED,
    )

# ------------------- PUT /v1/auth/reset -------------------
@auth_bp.route("/v1/auth/reset", methods=["PUT"])
def reset():
    """Reset the API token for a group"""
    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    if dev_token not in VALID_DEV_TOKENS:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return (
            jsonify({"error": "BAD_REQUEST", "message": "groupName is required"}),
            HTTPStatus.BAD_REQUEST,
        )

    # make sure that the group does exist 
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = sb_execute(existing)
    if existing_resp is None or sb_has_error(existing_resp):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
    if not existing_resp.data:
        return (
            jsonify(
                {
                    "error": "GROUP_NOT_FOUND",
                    "message": "groupName not found registered",
                }
            ),
            HTTPStatus.NOT_FOUND,
        )

    # Generate API token
    api_token = uuid.uuid4().hex

    update = (
        supabase.table("api_groups")
        .update({"api_token": api_token})
        .eq("group_name", group_name)
    )
    created_resp = sb_execute(update)
    if created_resp is None or sb_has_error(created_resp):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return (
        jsonify({
            "APItoken": api_token
        }),
        HTTPStatus.OK,
    )

# ------------------- delete /v1/auth/revoke -------------------
@auth_bp.route("/v1/auth/revoke", methods=["DELETE"])
def revoke():
    """Revoke the API token for a group"""  
    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return (
            jsonify({
                "error": "UNAUTHORIZED",
                "message": "The API token is missing or invalid. If you do not have an API token register for one through the forum on our website"
            }),
            HTTPStatus.UNAUTHORIZED,
        )

    if dev_token not in VALID_DEV_TOKENS:
        return (
            jsonify({
                "error": "FORBIDDEN",
                "message": "You do not have access to this content"
            }),
            HTTPStatus.FORBIDDEN,
        )

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return (
            jsonify({
                "error": "BAD_REQUEST", 
                "message": "groupName is required"
            }),
            HTTPStatus.BAD_REQUEST,
        )

    # check if the group exists 
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = sb_execute(existing)
    if existing_resp is None or sb_has_error(existing_resp):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )
        
    if not existing_resp.data:
        return (
            jsonify(
                {
                    "error": "GROUP_NOT_FOUND",
                    "message": "groupName not found registered",
                }
            ),
            HTTPStatus.NOT_FOUND,
        )

    api_token = existing_resp.data.api_token

    delete = (
        supabase.table("api_groups")
        .update({"api_token": None})
        .eq("group_name", group_name)
    )
    created_resp = sb_execute(delete)
    if created_resp is None or sb_has_error(created_resp):
        return (
            jsonify(
                {
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "Database error (check SUPABASE_URL/SUPABASE_KEY)",
                }
            ),
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    return (
        jsonify({
            "APItoken": api_token
        }),
        HTTPStatus.OK,
    )
