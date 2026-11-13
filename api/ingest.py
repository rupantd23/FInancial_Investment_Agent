"""Small, testable ingestion seams for replacing FINN demo fixtures.

These functions intentionally do not run at import time. Scheduled jobs should
call them, persist the returned records, and log provenance and failures.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any


def normalize_nse_ticker(ticker: str) -> str:
    """Normalize user input to the bare NSE symbol."""
    return ticker.strip().upper().replace(".NS", "").replace(".BO", "")


def yfinance_symbol(ticker: str) -> str:
    return f"{normalize_nse_ticker(ticker)}.NS"


def checksum_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def chunk_pages(pages: list[dict[str, Any]], max_chars: int = 6000) -> list[dict[str, Any]]:
    """Split page text while retaining page-level citation metadata."""
    chunks: list[dict[str, Any]] = []
    for page in pages:
        text = " ".join(str(page.get("text", "")).split())
        if not text:
            continue
        page_number = page.get("page_number")
        for start in range(0, len(text), max_chars):
            chunks.append({"page_number": page_number, "content": text[start : start + max_chars]})
    return chunks


def extract_pdf_pages(pdf_path: str | Path) -> list[dict[str, Any]]:
    """Extract page text with PyMuPDF when installed.

    Keeping the import local lets the API demo run from fixtures even before
    optional ingestion dependencies are installed.
    """
    try:
        import fitz  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for PDF ingestion") from exc

    document = fitz.open(str(pdf_path))
    return [
        {"page_number": index + 1, "text": page.get_text("text")}
        for index, page in enumerate(document)
    ]


def fetch_daily_market_data(ticker: str, period: str = "3mo") -> list[dict[str, Any]]:
    """Fetch end-of-day market records through yfinance.

    The caller is responsible for retries, rate limits, and persistence.
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError("yfinance is required for market ingestion") from exc

    frame = yf.download(yfinance_symbol(ticker), period=period, auto_adjust=False, progress=False)
    if frame.empty:
        return []

    records: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        records.append(
            {
                "ticker": normalize_nse_ticker(ticker),
                "trading_date": index.strftime("%Y-%m-%d"),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
                "source": "yfinance",
                "provenance": "verified",
            }
        )
    return records


def compare_periods(current: float | None, previous: float | None) -> dict[str, Any]:
    """Return a safe percentage change for QoQ/YoY display."""
    if current is None or previous is None or previous == 0:
        return {"value": None, "status": "unavailable"}
    return {"value": round((current - previous) / abs(previous) * 100, 2), "status": "calculated"}
