"""Seed the portfolio companies into Supabase using the server-only key."""

from __future__ import annotations

import json

from db import get_supabase_client
from main import PORTFOLIO


client = get_supabase_client(admin=True)
rows = [
    {
        "ticker": company["ticker"],
        "name": company["name"],
        "sector": company["sector"],
    }
    for company in PORTFOLIO
]
result = client.table("companies").upsert(rows, on_conflict="ticker").execute()
print(json.dumps({"seeded_companies": len(result.data or rows)}, indent=2))
