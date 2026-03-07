from flask import Blueprint, jsonify, request
from http import HTTPStatus
import uuid
from supabase.supabase import get_supabase

supabase = get_supabase()

auth_bp = Blueprint("auth", __name__)

# Example of storage (might be modified later when it comes to persistence)
VALID_DEV_TOKENS = {"dev-secret"}

# Store registered groups and their tokens
GROUPS = {}

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

    # Generate API token
    api_token = uuid.uuid4().hex

    # Store the group
    GROUPS[group_name] = {
        "token": api_token
    }

    return (
        jsonify({
            "APItoken": api_token
        }),
        HTTPStatus.CREATED,
    )