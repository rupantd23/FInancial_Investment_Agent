"""Local Supabase connectivity and schema check."""

from __future__ import annotations

import json

from db import check_supabase_connection


try:
    print(json.dumps(check_supabase_connection(), indent=2))
except Exception as exc:  # noqa: BLE001 - provide a useful local diagnostic
    print(json.dumps({"connected": False, "error": str(exc)}, indent=2))
    raise SystemExit(1) from exc
