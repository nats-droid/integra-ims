import os
from supabase import create_client, Client
from app.core.config import settings

_supabase: Client = None

def get_db() -> Client:
    """Get Supabase client with service role (bypasses RLS for internal operations)."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    return _supabase
