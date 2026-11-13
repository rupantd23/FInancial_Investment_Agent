"""Supabase client helpers for server-side FINN jobs."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class SupabaseNotConfigured(RuntimeError):
    pass


def get_supabase_client(*, admin: bool = False) -> Any:
    """Create a Supabase client without ever logging credentials."""
    try:
        from supabase import create_client  # type: ignore
    except ImportError as exc:
        raise SupabaseNotConfigured("Install the supabase Python client") from exc

    url = os.getenv("SUPABASE_URL")
    key_name = "SUPABASE_SERVICE_ROLE_KEY" if admin else "SUPABASE_ANON_KEY"
    key = os.getenv(key_name)
    if not url or not key:
        raise SupabaseNotConfigured(f"{key_name} and SUPABASE_URL must be set")
    return create_client(url, key)


def check_supabase_connection() -> dict[str, Any]:
    """Check that the schema is reachable without returning any secret data."""
    client = get_supabase_client(admin=True)
    response = client.table("companies").select("ticker").limit(1).execute()
    rows = response.data or []
    return {"connected": True, "schema_ready": True, "company_rows_visible": len(rows)}
