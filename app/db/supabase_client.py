"""
Supabase client configuration
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

CLIENT: Client | None = None


def get_supabase() -> Client:
    """Get the Supabase client."""
    global CLIENT  # pylint: disable=global-statement
    if CLIENT is not None:
        return CLIENT

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    CLIENT = create_client(url, key)
    return CLIENT
