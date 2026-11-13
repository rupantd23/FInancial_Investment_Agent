"""Upload annual reports/transcripts and create page-aware Supabase chunks.

Example:
  PYTHONPATH=. python ingest_documents.py \
    --ticker TCS \
    --annual-report /path/to/tcs-annual-report.pdf \
    --annual-report-url https://example.com/annual-report.pdf \
    --transcript /path/to/tcs-transcript.pdf \
    --transcript-url https://example.com/transcript.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from db import get_supabase_client
from ingest import chunk_pages, extract_pdf_pages, normalize_nse_ticker


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest FINN primary-source PDFs")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--annual-report", type=Path)
    parser.add_argument("--annual-report-url")
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--transcript-url")
    parser.add_argument("--provenance", choices=["verified", "cached"], default="cached")
    return parser.parse_args()


def document_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def company_id_for(client: Any, ticker: str) -> tuple[str, str]:
    normalized = normalize_nse_ticker(ticker)
    response = client.table("companies").select("id,name").eq("ticker", normalized).limit(1).execute()
    rows = response.data or []
    if not rows:
        raise SystemExit(f"{normalized} is not seeded. Run seed_supabase.py first.")
    return rows[0]["id"], rows[0]["name"]


def ingest_one(
    client: Any,
    *,
    company_id: str,
    ticker: str,
    path: Path,
    source_type: str,
    source_url: str | None,
    provenance: str,
    bucket: str,
) -> dict[str, Any]:
    if not path.exists() or path.suffix.lower() != ".pdf":
        raise SystemExit(f"Expected an existing PDF: {path}")

    checksum = document_checksum(path)
    existing = (
        client.table("source_documents")
        .select("id,title")
        .eq("checksum", checksum)
        .limit(1)
        .execute()
    )
    if existing.data:
        return {"status": "skipped", "title": existing.data[0]["title"], "reason": "same checksum already ingested"}

    storage_path = f"documents/{ticker}/{source_type}/{checksum[:12]}-{path.name}"
    client.storage.from_(bucket).upload(
        storage_path,
        path.read_bytes(),
        {"content-type": "application/pdf", "upsert": "true"},
    )
    document = (
        client.table("source_documents")
        .insert(
            {
                "company_id": company_id,
                "source_type": source_type,
                "title": path.stem,
                "source_url": source_url,
                "storage_path": storage_path,
                "provenance": provenance,
                "checksum": checksum,
            }
        )
        .execute()
    )
    document_id = document.data[0]["id"]
    chunks = chunk_pages(extract_pdf_pages(path))
    rows = [
        {"document_id": document_id, "page_number": chunk["page_number"], "content": chunk["content"]}
        for chunk in chunks
    ]
    for start in range(0, len(rows), 100):
        client.table("document_chunks").insert(rows[start : start + 100]).execute()
    return {"status": "ingested", "title": path.stem, "source_type": source_type, "chunks": len(rows)}


def main() -> None:
    args = parse_args()
    if not args.annual_report and not args.transcript:
        raise SystemExit("Provide --annual-report and/or --transcript")

    client = get_supabase_client(admin=True)
    ticker = normalize_nse_ticker(args.ticker)
    company_id, company_name = company_id_for(client, ticker)
    bucket = __import__("os").environ.get("SUPABASE_STORAGE_BUCKET", "source-documents")

    results = []
    if args.annual_report:
        results.append(
            ingest_one(
                client,
                company_id=company_id,
                ticker=ticker,
                path=args.annual_report,
                source_type="annual_report",
                source_url=args.annual_report_url,
                provenance=args.provenance,
                bucket=bucket,
            )
        )
    if args.transcript:
        results.append(
            ingest_one(
                client,
                company_id=company_id,
                ticker=ticker,
                path=args.transcript,
                source_type="earnings_call_transcript",
                source_url=args.transcript_url,
                provenance=args.provenance,
                bucket=bucket,
            )
        )
    print(json.dumps({"company": company_name, "ticker": ticker, "results": results}, indent=2))


if __name__ == "__main__":
    main()
