"""Fetch and ingest official annual reports for the supported company universe."""

from __future__ import annotations

import hashlib
import os
from typing import Any

import requests

from ingest import chunk_pages


ANNUAL_REPORT_SOURCES: dict[str, dict[str, str]] = {
    "RELIANCE": {"title": "RELIANCE-FY2025-annual-report", "url": "https://www.ril.com/ar2024-25/pdf/RIL-IAR-2025.pdf"},
    "TCS": {"title": "TCS-FY2026-annual-report", "url": "https://www.tcs.com/content/dam/tcs/investor-relations/financial-statements/2025-26/ar/annual-report-2025-2026.pdf"},
    "INFY": {"title": "INFY-FY2026-annual-report", "url": "https://www.infosys.com/investors/reports-filings/annual-report/annual/documents/infosys-ar-26.pdf"},
    "HDFCBANK": {"title": "HDFCBANK-FY2025-annual-report", "url": "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/annual-reports/2024-25/HDFC_Bank_Annual_Report_2024_25-310202.pdf"},
    "ICICIBANK": {"title": "ICICIBANK-FY2025-annual-report", "url": "https://www.icici.bank.in/content/dam/icicibank/managed-assets/docs/investor/annual-reports/2025/icici-bank-integrated-report-2024-25.pdf"},
    "SBIN": {"title": "SBIN-FY2025-annual-report", "url": "https://sbi.co.in/documents/17826/35696/Annual%2BReport%2BFY2025.pdf/1b6a1b79-a16d-b9d1-d28f-be8d7edf60d5?t=1745556744202"},
    "ITC": {"title": "ITC-FY2025-annual-report", "url": "https://itcportal.com/content/dam/itc-corporate/open-pdfs/report-and-accounts/ITC-Report-and-Accounts-2025.pdf"},
    "HINDUNILVR": {"title": "HINDUNILVR-FY2025-annual-report", "url": "https://www.hul.co.in/files/annual-report-2024-25.pdf"},
    "LT": {"title": "LT-FY2025-annual-report", "url": "https://investors.larsentoubro.com/pdf/2025/Integrated%20Report%202024-25.pdf"},
    "MARUTI": {"title": "MARUTI-FY2025-annual-report", "url": "https://www.marutisuzuki.com/content/dam/arena-eds/corporate/pdf/company-reports/2024-2025/MSIL_IR_2024_25_HR.pdf"},
    "SUNPHARMA": {"title": "SUNPHARMA-FY2025-annual-report", "url": "https://sunpharma.com/wp-content/uploads/2025/07/Sunpharmaannualreport202425.pdf"},
    "ASIANPAINT": {"title": "ASIANPAINT-FY2025-annual-report", "url": "https://static.asianpaints.com/content/dam/annual-folder-2425/pdf/Asian%20Paints%20IR%202024-25.pdf"},
    "WIPRO": {"title": "WIPRO-FY2025-annual-report", "url": "https://www.wipro.com/content/dam/nexus/en/investor/annual-reports/2024-2025/Integrated-Annual-report-2024-2025.pdf"},
    "AXISBANK": {"title": "AXISBANK-FY2025-annual-report", "url": "https://www.axisbank.com/docs/default-source/annual-reports/for-axis-bank/annual-report-for-the-year-2024-2025.pdf"},
    "BHARTIARTL": {"title": "BHARTIARTL-FY2025-annual-report", "url": "https://www.airtel.in/airtel-annual-report-2024-25/pdf/Bharti%20Airtel%20IAR%202024-25.pdf"},
    "ADANIENT": {"title": "ADANIENT-FY2025-annual-report", "url": "https://www.adanienterprises.com/-/media/Project/Enterprises/Investors/Investor-Downloads/Annual-Report/AEL-FY25.pdf"},
}


def _extract_pdf_pages(content: bytes) -> list[dict[str, Any]]:
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for automatic document ingestion") from exc

    document = fitz.open(stream=content, filetype="pdf")
    try:
        return [
            {"page_number": index + 1, "text": page.get_text("text")}
            for index, page in enumerate(document)
        ]
    finally:
        document.close()


def fetch_and_ingest_annual_report(client: Any, *, ticker: str, company_id: str) -> dict[str, Any]:
    """Download one official annual report and persist storage, metadata, and chunks."""
    source = ANNUAL_REPORT_SOURCES.get(ticker)
    if not source:
        return {"status": "unavailable", "message": "No official annual-report URL is configured for this ticker."}

    existing = (
        client.table("source_documents")
        .select("id,title")
        .eq("company_id", company_id)
        .eq("source_type", "annual_report")
        .limit(1)
        .execute()
    ).data or []
    if existing:
        return {"status": "existing", "title": existing[0]["title"], "message": "Annual report already exists in Supabase."}

    try:
        response = requests.get(
            source["url"],
            headers={"User-Agent": "FINN research prototype/1.0"},
            timeout=(10, 45),
        )
        response.raise_for_status()
        content = response.content
    except requests.RequestException as exc:
        return {"status": "failed", "message": f"Annual-report download failed: {exc}"}

    if not content.startswith(b"%PDF"):
        return {"status": "failed", "message": "The configured annual-report URL did not return a valid PDF."}
    if len(content) > 60 * 1024 * 1024:
        return {"status": "failed", "message": "The annual report is larger than the 60 MB ingestion limit."}

    checksum = hashlib.sha256(content).hexdigest()
    duplicate = (
        client.table("source_documents")
        .select("id,title")
        .eq("checksum", checksum)
        .limit(1)
        .execute()
    ).data or []
    if duplicate:
        return {"status": "existing", "title": duplicate[0]["title"], "message": "The same annual report is already in Supabase."}

    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "source-documents")
    storage_path = f"documents/{ticker}/annual_report/{checksum[:12]}-{source['title']}.pdf"
    try:
        client.storage.from_(bucket).upload(
            storage_path,
            content,
            {"content-type": "application/pdf", "upsert": "true"},
        )
        document_response = (
            client.table("source_documents")
            .insert(
                {
                    "company_id": company_id,
                    "source_type": "annual_report",
                    "title": source["title"],
                    "source_url": source["url"],
                    "storage_path": storage_path,
                    "provenance": "verified",
                    "checksum": checksum,
                }
            )
            .execute()
        )
        document_id = document_response.data[0]["id"]
        chunks = chunk_pages(_extract_pdf_pages(content))
        rows = [
            {"document_id": document_id, "page_number": chunk["page_number"], "content": chunk["content"]}
            for chunk in chunks
        ]
        for start in range(0, len(rows), 100):
            client.table("document_chunks").insert(rows[start : start + 100]).execute()
    except Exception as exc:
        return {"status": "failed", "message": f"Annual report downloaded but could not be saved to Supabase: {exc}"}

    return {
        "status": "ingested",
        "title": source["title"],
        "chunks": len(rows),
        "message": "Annual report downloaded and ingested into Supabase.",
    }
