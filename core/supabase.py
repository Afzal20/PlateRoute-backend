import os
from supabase import create_client, Client

url: str = os.environ.get("NEXT_PUBLIC_SUPABASE_URL", "")
key: str = os.environ.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")

# Note: Since the backend is running independently of the frontend, we use the
# publishable key for verification, or if we need admin rights, we'd use the service role key.
supabase: Client = create_client(url, key)
