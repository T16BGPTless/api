import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import Client, createclient

client: Client | None = None

def load_env() -> None:
    # Load .env from repo root so it works regardless of CWD.
    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)


def get_supabase() -> Client:
    global client
    if client is not None:
        return client

    load_env()

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    
    client = createclient(url, key)
    return client
