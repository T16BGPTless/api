"""
Supabase client configuration
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

_CLIENT: Client | None = None


def _load_env() -> None:
    #Load the .env file from the repository root.
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)


def get_supabase() -> Client:
    """Return a singleton Supabase client."""
    global _CLIENT

    if _CLIENT is not None:
        return _CLIENT

    _load_env()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    _CLIENT = create_client(url, key)
    return _CLIENT