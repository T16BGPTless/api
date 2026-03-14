"""
Authorisation methods
"""

from http import HTTPStatus
import uuid
from flask import Blueprint, jsonify, request
from app.routes.helpers import sb_has_error, sb_execute, get_db, return_error

auth_bp = Blueprint("auth", __name__)

VALID_DEV_TOKENS = {"dev-secret"}


# ------------------- POST /v1/auth/register -------------------
@auth_bp.route("/v1/auth/register", methods=["POST"])
def register():  # pylint: disable=too-many-return-statements
    """Register a new group."""

    supabase = get_db()
    if supabase is None:
        return return_error("INTERNAL_SERVER_ERROR")

    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return return_error("UNAUTHORIZED")

    if dev_token not in VALID_DEV_TOKENS:
        return return_error("FORBIDDEN")

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return return_error("GROUP_NAME_REQUIRED")

    # Prevent duplicate registrations by group name
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = sb_execute(existing)
    if existing_resp is None or sb_has_error(existing_resp):
        return return_error("INTERNAL_SERVER_ERROR")
    if existing_resp.data:
        return return_error("GROUP_ALREADY_REGISTERED")

    # Generate API token
    api_token = uuid.uuid4().hex

    created = supabase.table("api_groups").insert(
        {"group_name": group_name, "api_token": api_token}
    )
    created_resp = sb_execute(created)
    if created_resp is None or sb_has_error(created_resp):
        return return_error("INTERNAL_SERVER_ERROR")

    return jsonify({"APItoken": api_token}), HTTPStatus.CREATED


# ------------------- PUT /v1/auth/reset -------------------
@auth_bp.route("/v1/auth/reset", methods=["PUT"])
def reset():  # pylint: disable=too-many-return-statements
    """Reset the API token for a group."""

    supabase = get_db()
    if supabase is None:
        return return_error("INTERNAL_SERVER_ERROR")

    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return return_error("UNAUTHORIZED")

    if dev_token not in VALID_DEV_TOKENS:
        return return_error("FORBIDDEN")

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return return_error("GROUP_NAME_REQUIRED")

    # make sure that the group does exist
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = sb_execute(existing)
    if existing_resp is None or sb_has_error(existing_resp):
        return return_error("INTERNAL_SERVER_ERROR")

    if not existing_resp.data:
        return return_error("GROUP_NOT_FOUND")

    # Generate API token
    api_token = uuid.uuid4().hex

    update = (
        supabase.table("api_groups")
        .update({"api_token": api_token})
        .eq("group_name", group_name)
    )
    created_resp = sb_execute(update)
    if created_resp is None or sb_has_error(created_resp):
        return return_error("INTERNAL_SERVER_ERROR")

    return jsonify({"APItoken": api_token}), HTTPStatus.OK


# ------------------- delete /v1/auth/revoke -------------------
@auth_bp.route("/v1/auth/revoke", methods=["DELETE"])
def revoke():  # pylint: disable=too-many-return-statements
    """Revoke the API token for a group."""

    supabase = get_db()
    if supabase is None:
        return return_error("INTERNAL_SERVER_ERROR")
    # Validate developer token (401)
    dev_token = request.headers.get("APIdevToken")

    if not dev_token:
        return return_error("UNAUTHORIZED")

    if dev_token not in VALID_DEV_TOKENS:
        return return_error("FORBIDDEN")

    body = request.get_json(silent=True) or {}
    group_name = body.get("groupName")

    if not group_name:
        return return_error("GROUP_NAME_REQUIRED")

    # check if the group exists
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = sb_execute(existing)
    if existing_resp is None or sb_has_error(existing_resp):
        return return_error("INTERNAL_SERVER_ERROR")
    if not existing_resp.data:
        return return_error("GROUP_NOT_FOUND")

    api_token = existing_resp.data[0].get("api_token")

    delete = (
        supabase.table("api_groups")
        .update({"api_token": None})
        .eq("group_name", group_name)
    )
    created_resp = sb_execute(delete)
    if created_resp is None or sb_has_error(created_resp):
        return return_error("INTERNAL_SERVER_ERROR")

    return jsonify({"APItoken": api_token}), HTTPStatus.OK
