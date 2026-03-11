import os

# Fake environment variables so Supabase client does not crash
os.environ["SUPABASE_URL"] = "http://test"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-key"