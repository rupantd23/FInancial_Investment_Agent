"""Small, testable ingestion seams for replacing FINN demo fixtures.

These functions intentionally do not run at import time. Scheduled jobs should
call them, persist the returned records, and log provenance and failures.
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


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
    """Fetch verified end-of-day market records from Yahoo Finance.

    The chart endpoint is attempted first because it avoids yfinance's
    cookie/crumb parsing path. yfinance remains as a compatibility fallback.
    """
    try:
        import yfinance as yf  # type: ignore
    except ImportError as exc:
        raise RuntimeError("yfinance is required for market ingestion") from exc

    symbol = yfinance_symbol(ticker)
    chart_error: Exception | None = None
    try:
        chart_records = _fetch_yahoo_chart_records(ticker, period)
        if chart_records:
            return chart_records
    except Exception as exc:
        chart_error = exc

    session = requests.Session()
    session.headers.update({"User-Agent": "FINN market ingestion/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            frame = yf.download(
                symbol,
                period=period,
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=20,
                session=session,
            )
            records = _records_from_frame(normalize_nse_ticker(ticker), frame)
            if records:
                return records
        except Exception as exc:
            last_error = exc
        if attempt < 2:
            time.sleep(2 ** attempt)

    try:
        return _fetch_yahoo_chart_records(ticker, period)
    except Exception as exc:
        if last_error:
            detail = f"Yahoo market data failed for {symbol}: {exc}; yfinance: {last_error}"
            if chart_error:
                detail += f"; initial chart request: {chart_error}"
            raise RuntimeError(detail) from exc
        raise RuntimeError(f"Yahoo market data failed for {symbol}: {exc}") from exc


def _records_from_frame(ticker: str, frame: Any) -> list[dict[str, Any]]:
    if frame is None or frame.empty:
        return []
    records: list[dict[str, Any]] = []
    for index, row in frame.iterrows():
        close_value = row["Close"]
        volume_value = row["Volume"]
        if hasattr(close_value, "iloc"):
            close_value = close_value.iloc[0]
        if hasattr(volume_value, "iloc"):
            volume_value = volume_value.iloc[0]
        if close_value is None or volume_value is None:
            continue
        records.append({
            "ticker": ticker,
            "trading_date": index.strftime("%Y-%m-%d"),
            "close": float(close_value),
            "volume": float(volume_value),
            "source": "yfinance",
            "provenance": "verified",
        })
    return records


def _fetch_yahoo_chart_records(ticker: str, period: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    payload: dict[str, Any] | None = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            response = requests.get(
                f"https://{host}/v8/finance/chart/{yfinance_symbol(ticker)}",
                params={"range": period, "interval": "1d", "events": "history"},
                headers={"User-Agent": "Mozilla/5.0 FINN market ingestion/1.0", "Accept": "application/json"},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            break
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
    if payload is None:
        raise RuntimeError(f"Yahoo chart endpoints were unavailable: {last_error}")
    result = (payload.get("chart") or {}).get("result")
    if not result:
        raise RuntimeError((payload.get("chart") or {}).get("error") or "Yahoo returned no chart data")
    result = result[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    records = []
    for timestamp, close_value, volume_value in zip(timestamps, quote.get("close") or [], quote.get("volume") or []):
        if close_value is None:
            continue
        records.append({
            "ticker": normalize_nse_ticker(ticker),
            "trading_date": datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d"),
            "close": float(close_value),
            "volume": float(volume_value or 0),
            "source": "Yahoo Finance chart API",
            "provenance": "verified",
        })
    return records


def compare_periods(current: float | None, previous: float | None) -> dict[str, Any]:
    """Return a safe percentage change for QoQ/YoY display."""
    if current is None or previous is None or previous == 0:
        return {"value": None, "status": "unavailable"}
    return {"value": round((current - previous) / abs(previous) * 100, 2), "status": "calculated"}
