from flask import Blueprint, jsonify, request
from http import HTTPStatus

auth_bp = Blueprint("auth", __name__)


# POST /v1/auth/register
@auth_bp.route("/v1/auth/register", methods=["POST"])
def register():
    return jsonify({
        "message": "Register API user (stub)"
    }), HTTPStatus.NOT_IMPLEMENTED