import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, create_client
from supabase.lib.client_options import ClientOptions

def _load_env() -> None:
    # Load .env from repo root so it works regardless of CWD.
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)


def get_supabase() -> Client:
    _load_env()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

    options = ClientOptions(postgrest_client_timeout=10, storage_client_timeout=10)
    
    client = create_client(url, key, options=options)
    return client

