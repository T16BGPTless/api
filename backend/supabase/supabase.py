import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Load .env from project root so it works when running from backend/
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path)

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase: Client = create_client(url, key)

def get_supabase():
  return supabase