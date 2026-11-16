"""Fetch recent NSE EOD prices and volumes into Supabase for Push discovery."""

from __future__ import annotations

import argparse
import json

from db import get_supabase_client
from ingest import fetch_daily_market_data, normalize_nse_ticker
from main import PORTFOLIO


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest EOD market data for the FINN radar")
    parser.add_argument("--period", default="3mo", help="yfinance period, for example 1mo or 3mo")
    args = parser.parse_args()

    client = get_supabase_client(admin=True)
    companies = (client.table("companies").select("id,ticker").limit(250).execute()).data or []
    known = {normalize_nse_ticker(row["ticker"]): row for row in companies}
    # Ensure the default discovery universe can be ingested even before a user adds it.
    for item in PORTFOLIO:
        if item["ticker"] not in known:
            saved = (
                client.table("companies")
                .upsert(item, on_conflict="ticker")
                .select("id,ticker")
                .single()
                .execute()
            ).data
            if saved:
                known[item["ticker"]] = saved

    results = []
    for ticker, company in known.items():
        try:
            records = fetch_daily_market_data(ticker, period=args.period)
            rows = [
                {
                    "company_id": company["id"],
                    "trading_date": record["trading_date"],
                    "close": record["close"],
                    "volume": record["volume"],
                    "source": record["source"],
                    "provenance": record["provenance"],
                }
                for record in records
            ]
            if rows:
                client.table("market_daily").upsert(rows, on_conflict="company_id,trading_date").execute()
            results.append({"ticker": ticker, "rows": len(rows), "status": "ingested"})
        except Exception as exc:
            results.append({"ticker": ticker, "rows": 0, "status": "failed", "message": str(exc)})

    print(json.dumps({"companies": len(known), "results": results}, indent=2))


if __name__ == "__main__":
    main()
