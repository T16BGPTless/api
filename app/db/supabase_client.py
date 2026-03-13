"""
Supabase client configuration
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client

supabase_client: Client | None = None


def get_supabase() -> Client:
    """Get the Supabase client."""
    global supabase_client  # pylint: disable=global-statement
    if supabase_client is not None:
        return supabase_client

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

    supabase_client = create_client(url, key)
    return supabase_client
