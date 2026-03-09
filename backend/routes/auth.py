from flask import Blueprint, jsonify, request
from http import HTTPStatus
import uuid
from db.supabase_client import get_supabase
from postgrest.exceptions import APIError

supabase = get_supabase()

auth_bp = Blueprint("auth", __name__)

# Example of storage (might be modified later when it comes to persistence)
VALID_DEV_TOKENS = {"dev-secret"}

# Store registered groups and their tokens


def _sb_has_error(resp) -> bool:
    return getattr(resp, "error", None) is not None


def _sb_execute(builder):
    try:
        return builder.execute()
    except APIError:
        return None

# ------------------- POST /v1/auth/register -------------------
@auth_bp.route("/v1/auth/register", methods=["POST"])
def register():

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

    # Prevent duplicate registrations by group name
    existing = (
        supabase.table("api_groups")
        .select("api_token")
        .eq("group_name", group_name)
        .limit(1)
    )
    existing_resp = _sb_execute(existing)
    if existing_resp is None or _sb_has_error(existing_resp):
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
    created_resp = _sb_execute(created)
    if created_resp is None or _sb_has_error(created_resp):
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