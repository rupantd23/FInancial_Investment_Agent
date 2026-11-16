from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import os
from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import Depends, File, FastAPI, HTTPException, Header, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from db import get_supabase_client
from document_fetcher import fetch_and_ingest_annual_report
from ingest import fetch_daily_market_data, normalize_nse_ticker
from llm import ALLOWED_SOURCE_TYPES, GeminiTemporarilyUnavailable, generate_chat
from research_service import get_live_research
from news import GNewsNotConfigured, GNewsRequestFailed, search_news
from network_service import NetworkContactInput, insert_contacts, list_contacts, match_contacts, parse_csv_bytes
from auth import require_user_id
from linkedin_service import LinkedInNotConfigured, LinkedInRequestFailed, authorization_url, consume_oauth_context, create_oauth_state, import_connections


app = FastAPI(title="FINN API", version="0.1.0")
_configured_cors_origins = [
    origin.strip()
    for origin in os.getenv("FINN_CORS_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins or ["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PortfolioCompanyInput(BaseModel):
    query: str = Field(min_length=2, max_length=120)


DEFAULT_ALERT_PREFERENCES = {
    "enabled": True,
    "price_rise_threshold": 5.0,
    "price_fall_threshold": 5.0,
    "volume_multiplier": 2.0,
    "material_filings": ["results", "m&a", "fund_raise", "management", "legal_regulatory", "earnings_call"],
    "watched_scope": "portfolio",
}


class AlertPreferencesInput(BaseModel):
    enabled: bool = True
    price_rise_threshold: float = Field(default=5.0, ge=0.5, le=50)
    price_fall_threshold: float = Field(default=5.0, ge=0.5, le=50)
    volume_multiplier: float = Field(default=2.0, ge=1.0, le=20)
    material_filings: list[str] = Field(default_factory=lambda: list(DEFAULT_ALERT_PREFERENCES["material_filings"]))
    watched_scope: Literal["portfolio", "selected"] = "portfolio"


class ChatInput(BaseModel):
    question: str = Field(min_length=3, max_length=600)
    ticker: str | None = Field(default=None, max_length=20)


PORTFOLIO = [
    {"ticker": "RELIANCE", "name": "Reliance Industries", "sector": "Energy & Digital"},
    {"ticker": "TCS", "name": "Tata Consultancy Services", "sector": "Technology"},
    {"ticker": "INFY", "name": "Infosys", "sector": "Technology"},
    {"ticker": "HDFCBANK", "name": "HDFC Bank", "sector": "Financials"},
    {"ticker": "ICICIBANK", "name": "ICICI Bank", "sector": "Financials"},
    {"ticker": "SBIN", "name": "State Bank of India", "sector": "Financials"},
    {"ticker": "ITC", "name": "ITC", "sector": "Consumer"},
    {"ticker": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "Consumer"},
    {"ticker": "LT", "name": "Larsen & Toubro", "sector": "Industrials"},
    {"ticker": "MARUTI", "name": "Maruti Suzuki India", "sector": "Auto"},
    {"ticker": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Healthcare"},
    {"ticker": "ASIANPAINT", "name": "Asian Paints", "sector": "Consumer"},
    {"ticker": "WIPRO", "name": "Wipro", "sector": "Technology"},
    {"ticker": "AXISBANK", "name": "Axis Bank", "sector": "Financials"},
    {"ticker": "BHARTIARTL", "name": "Bharti Airtel", "sector": "Telecom"},
]

# Companies that can be added on demand. These do not become part of the
# default portfolio until the signed-in user explicitly adds them.
SUPPORTED_COMPANIES = [
    *PORTFOLIO,
    {"ticker": "ADANIENT", "name": "Adani Enterprises", "sector": "Industrials & Infrastructure"},
]


def source(label: str, source_type: str, page: str | None = None) -> dict[str, Any]:
    return {
        "label": label,
        "type": source_type,
        "page": page,
        "url": None,
        "provenance": "Synthetic demo fixture",
    }


NETWORK = {
    "RELIANCE": [
        {
            "name": "Asha Mehta",
            "role": "Former digital infrastructure operator",
            "score": 92,
            "reason": "Worked at a synthetic Reliance Digital Infrastructure fixture from 2021–2023.",
            "evidence": "Employer overlap",
            "caveat": "Employer overlap indicates relevance, not proof of a personal relationship.",
        },
        {
            "name": "Rohan Kapoor",
            "role": "Enterprise technology advisor",
            "score": 68,
            "reason": "Sector overlap with telecom and cloud infrastructure; recorded as an investor contact.",
            "evidence": "Sector expertise",
            "caveat": "Synthetic profile for demonstration only.",
        },
    ],
    "TCS": [
        {
            "name": "Neha Rao",
            "role": "Former enterprise software executive",
            "score": 88,
            "reason": "Worked at a synthetic TCS fixture and later at a large enterprise buyer.",
            "evidence": "Employer and customer overlap",
            "caveat": "This is a relevance signal, not a claim of personal contact.",
        },
        {
            "name": "Vikram Singh",
            "role": "Technology services operator",
            "score": 64,
            "reason": "Recorded expertise in Indian IT services and delivery economics.",
            "evidence": "Sector expertise",
            "caveat": "Synthetic profile for demonstration only.",
        },
    ],
    "INFY": [
        {
            "name": "Vikram Singh",
            "role": "Technology services operator",
            "score": 84,
            "reason": "Former employer and sector overlap with IT services delivery.",
            "evidence": "Employer overlap",
            "caveat": "Employer overlap indicates relevance, not proof of a personal relationship.",
        }
    ],
}


ANNOUNCEMENTS = [
    {
        "id": "ann-001",
        "ticker": "TCS",
        "company": "Tata Consultancy Services",
        "kind": "Quarterly results",
        "priority": "High",
        "title": "Results filing: headline metrics need a closer look",
        "summary": "A results filing was added to the digest. FINN extracted the four headline metrics for comparison.",
        "impact": "Compare delivery against management commentary before changing the investment view.",
        "metric": {"label": "PAT YoY", "value": "+8.4%", "tone": "positive"},
        "source": source("Synthetic results filing", "annual_report", "p. 3"),
        "network": NETWORK["TCS"],
    },
    {
        "id": "ann-002",
        "ticker": "RELIANCE",
        "company": "Reliance Industries",
        "kind": "Unusual volume",
        "priority": "High",
        "title": "Volume crossed your unusual-move threshold",
        "summary": "End-of-day volume is 2.4× its 20-day average in this synthetic fixture.",
        "impact": "Check the latest company filing and avoid treating volume alone as an explanation.",
        "metric": {"label": "Volume vs avg", "value": "2.4×", "tone": "warning"},
        "source": source("Synthetic market data", "market_data", None),
        "network": NETWORK["RELIANCE"],
    },
    {
        "id": "ann-003",
        "ticker": "INFY",
        "company": "Infosys",
        "kind": "Management change",
        "priority": "Medium",
        "title": "Incoming finance leader added to the watchlist",
        "summary": "A management-change announcement is available for review.",
        "impact": "Use the background card to identify relevant operating context before a conversation.",
        "metric": {"label": "Network relevance", "value": "1 strong match", "tone": "neutral"},
        "source": source("Synthetic exchange announcement", "announcement", "p. 1"),
        "network": NETWORK["INFY"],
    },
]


RESEARCH = {
    "TCS": {
        "ticker": "TCS",
        "company": "Tata Consultancy Services",
        "available": True,
        "disclosure": "Synthetic demo analysis. Replace with extracted annual-report and transcript evidence before submission.",
        "headline": "A resilient services profile with a question around delivery against guidance.",
        "sections": [
            {"label": "Business snapshot", "text": "Synthetic evidence describes a diversified enterprise technology-services business across multiple client sectors.", "status": "Interpreted", "source": source("Synthetic annual report excerpt", "annual_report", "p. 12")},
            {"label": "Financial trajectory", "text": "Revenue and PAT are shown as stable-to-growing in the demo fixture; replace these values with extracted company figures.", "status": "Synthetic demo", "source": source("Synthetic results excerpt", "annual_report", "p. 34")},
            {"label": "Narrative vs numbers", "text": "Management commentary emphasizes resilience. The next implementation step is to compare the last four quarters with explicit guidance from transcripts.", "status": "Interpreted", "source": source("Synthetic earnings-call excerpt", "earnings_call_transcript", "p. 5")},
            {"label": "Bull / bear", "text": "Bull: diversified demand and execution. Bear: slower discretionary technology spending could pressure growth.", "status": "Interpreted", "source": source("Synthetic transcript excerpt", "earnings_call_transcript", "p. 8")},
        ],
        "network": NETWORK["TCS"],
    },
    "RELIANCE": {
        "ticker": "RELIANCE",
        "company": "Reliance Industries",
        "available": True,
        "disclosure": "Synthetic demo analysis. Replace with extracted annual-report and transcript evidence before submission.",
        "headline": "A diversified company where the key research task is separating segment narratives.",
        "sections": [
            {"label": "Business snapshot", "text": "Synthetic evidence describes a diversified group with energy, consumer, and digital infrastructure activities.", "status": "Interpreted", "source": source("Synthetic annual report excerpt", "annual_report", "p. 9")},
            {"label": "Narrative vs numbers", "text": "The demo flags a need to compare segment commentary with reported operating performance rather than relying on a single consolidated headline.", "status": "Interpreted", "source": source("Synthetic earnings-call excerpt", "earnings_call_transcript", "p. 4")},
            {"label": "Bull / bear", "text": "Bull: multiple growth engines. Bear: complexity makes evidence quality and segment attribution more important.", "status": "Interpreted", "source": source("Synthetic transcript excerpt", "earnings_call_transcript", "p. 7")},
        ],
        "network": NETWORK["RELIANCE"],
    },
    "INFY": {
        "ticker": "INFY",
        "company": "Infosys",
        "available": True,
        "disclosure": "Synthetic demo analysis. Replace with extracted annual-report and transcript evidence before submission.",
        "headline": "A technology-services research view focused on demand, margins, and delivery commentary.",
        "sections": [
            {"label": "Business snapshot", "text": "Synthetic evidence describes an international technology-services business with enterprise clients.", "status": "Interpreted", "source": source("Synthetic annual report excerpt", "annual_report", "p. 11")},
            {"label": "Guidance", "text": "No verified guidance is available in this fixture; FINN should show the missing-evidence state until a transcript is loaded.", "status": "Unavailable", "source": None},
            {"label": "Bull / bear", "text": "Bull: resilient client relationships. Bear: discretionary-spend weakness may delay large programs.", "status": "Interpreted", "source": source("Synthetic transcript excerpt", "earnings_call_transcript", "p. 6")},
        ],
        "network": NETWORK["INFY"],
    },
}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "finn-api", "timestamp": datetime.now(timezone.utc).isoformat()}


def _load_alert_preferences(client: Any, user_id: str) -> dict[str, Any]:
    """Load user settings while keeping the feed usable before the migration is run."""
    try:
        rows = (
            client.table("alert_preferences")
            .select("enabled,price_rise_threshold,price_fall_threshold,volume_multiplier,material_filings,watched_scope")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        ).data or []
        if rows:
            return {**DEFAULT_ALERT_PREFERENCES, **rows[0], "storage_ready": True}
    except Exception:
        pass
    return {**DEFAULT_ALERT_PREFERENCES, "storage_ready": False}


def _market_digest_items(
    client: Any,
    companies: dict[str, dict[str, Any]],
    user_id: str,
    preferences: dict[str, Any],
) -> list[dict[str, Any]]:
    if not companies:
        return []
    rows = (
        client.table("market_daily")
        .select("company_id,trading_date,close,volume,source,provenance")
        .in_("company_id", list(companies))
        .order("trading_date", desc=True)
        .limit(min(len(companies) * 21, 2000))
        .execute()
    ).data or []
    by_company: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_company.setdefault(str(row["company_id"]), []).append(row)

    items: list[dict[str, Any]] = []
    for company_id, company_rows in by_company.items():
        if len(company_rows) < 2:
            continue
        latest, previous = company_rows[0], company_rows[1]
        latest_close = float(latest["close"] or 0)
        previous_close = float(previous["close"] or 0)
        if not previous_close:
            continue
        change = (latest_close - previous_close) / abs(previous_close) * 100
        rise_threshold = float(preferences.get("price_rise_threshold", 5))
        fall_threshold = float(preferences.get("price_fall_threshold", 5))
        price_triggered = change >= rise_threshold or change <= -fall_threshold
        prior_volumes = [float(row.get("volume") or 0) for row in company_rows[1:21] if row.get("volume")]
        latest_volume = float(latest.get("volume") or 0)
        average_volume = sum(prior_volumes) / len(prior_volumes) if prior_volumes else 0
        volume_ratio = latest_volume / average_volume if average_volume else 0
        volume_triggered = volume_ratio >= float(preferences.get("volume_multiplier", 2))
        if not price_triggered and not volume_triggered:
            continue
        company = companies.get(company_id)
        if not company:
            continue
        direction = "rose" if change > 0 else "fell"
        items.append(
            {
                "id": f"market-{company['ticker']}-{latest['trading_date']}",
                "ticker": company["ticker"],
                "company": company["name"],
                "kind": "Market signal",
                "priority": "High" if abs(change) >= 5 else "Medium",
                "title": f"{company['ticker']} {direction} {abs(change):.1f}% in the latest session" if price_triggered else f"{company['ticker']} volume reached {volume_ratio:.1f}× its recent average",
                "summary": f"EOD close moved from {previous_close:.2f} to {latest_close:.2f}." + (f" Volume was {volume_ratio:.1f}× the prior average." if volume_triggered else ""),
                "impact": "Price movement is a prompt to investigate; it is not an explanation by itself. Check the latest filing and Pull research.",
                "metric": {"label": "EOD return", "value": f"{change:+.1f}%", "tone": "positive" if change > 0 else "warning"},
                "source": {
                    "label": latest.get("source") or "Market data",
                    "type": "market_data",
                    "page": None,
                    "url": None,
                    "provenance": latest.get("provenance") or "verified",
                },
                "network": _network_for_ticker(company["ticker"], user_id=user_id),
            }
        )
    return items


def _news_digest_items(companies: list[dict[str, Any]], user_id: str) -> list[dict[str, Any]]:
    """Add a small contextual news sample without making news Pull evidence."""
    def fetch_for_company(company: dict[str, Any]) -> list[dict[str, Any]]:
        try:
            result = search_news(company["name"], max_results=2)
        except (GNewsNotConfigured, GNewsRequestFailed):
            return []
        items: list[dict[str, Any]] = []
        for article in result.get("articles", [])[:2]:
            publisher = (article.get("source") or {}).get("name") or "News publisher"
            items.append(
                {
                    "id": f"news-{company['ticker']}-{article.get('id') or article.get('url') or article.get('title')}",
                    "ticker": company["ticker"],
                    "company": company["name"],
                    "kind": "News context",
                    "priority": "Low",
                    "title": article.get("title") or f"Recent coverage for {company['ticker']}",
                    "summary": article.get("description") or "Recent coverage is available for context.",
                    "impact": "Context only: verify this coverage against an official filing or primary-source research before acting.",
                    "metric": {"label": "Context", "value": "News", "tone": "neutral"},
                    "source": {
                        "label": publisher,
                        "type": "news",
                        "page": None,
                        "url": article.get("url"),
                        "provenance": "GNews API",
                    },
                    "network": _network_for_ticker(company["ticker"], user_id=user_id),
                }
            )
        return items

    items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(3, max(len(companies), 1))) as executor:
        futures = [executor.submit(fetch_for_company, company) for company in companies[:3]]
        for future in as_completed(futures):
            items.extend(future.result())
    return items


@app.get("/digest")
def digest(window: str = Query(default="24h"), user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Build Today from primary sources, market data, and contextual news.

    News is deliberately not passed into Pull research. Pull research is
    generated on demand from annual reports and earnings-call transcripts.
    """
    try:
        client = get_supabase_client(admin=True)
        alert_preferences = _load_alert_preferences(client, user_id)
        tickers = [item["ticker"] for item in PORTFOLIO]
        company_rows = (
            client.table("companies")
            .select("id,ticker,name,sector")
            .in_("ticker", tickers)
            .execute()
        ).data or []
        company_by_id = {str(row["id"]): row for row in company_rows}

        memberships = (
            client.table("portfolio_companies")
            .select("company_id")
            .eq("tenant_id", user_id)
            .execute()
        ).data or []
        added_ids = [str(row["company_id"]) for row in memberships if row.get("company_id")]
        if added_ids:
            added_rows = (
                client.table("companies")
                .select("id,ticker,name,sector")
                .in_("id", added_ids)
                .execute()
            ).data or []
            company_by_id.update({str(row["id"]): row for row in added_rows})

        company_ids = list(company_by_id)
        documents = []
        if company_ids:
            documents = (
                client.table("source_documents")
                .select("id,company_id,title,source_type,source_url,provenance,published_at,created_at")
                .in_("company_id", company_ids)
                .in_("source_type", ["annual_report", "earnings_call_transcript", "announcement"])
                .order("created_at", desc=True)
                .limit(30)
                .execute()
            ).data or []

        latest_by_company: dict[str, dict[str, Any]] = {}
        for document in documents:
            company_id = str(document["company_id"])
            latest_by_company.setdefault(company_id, document)

        items: list[dict[str, Any]] = []
        for index, document in enumerate(latest_by_company.values(), start=1):
            company = company_by_id.get(str(document["company_id"]))
            if not company:
                continue
            is_transcript = document["source_type"] == "earnings_call_transcript"
            is_announcement = document["source_type"] == "announcement"
            source_label = "Earnings-call transcript" if is_transcript else "Material filing" if is_announcement else "Annual report"
            items.append(
                {
                    "id": f"source-{document['id']}",
                    "ticker": company["ticker"],
                    "company": company["name"],
                    "kind": "Material filing" if is_announcement else "Primary-source update",
                    "priority": "Medium",
                    "title": f"{source_label} is ready for review",
                    "summary": f"{document['title']} was loaded into FINN and can now support source-grounded research.",
                    "impact": "Open Pull research to compare the company’s reported figures, trajectory, and management narrative against this source.",
                    "metric": {"label": "Source status", "value": "Verified", "tone": "positive"},
                    "source": {
                        "label": document["title"],
                        "type": document["source_type"],
                        "page": None,
                        "url": document.get("source_url"),
                        "provenance": document.get("provenance", "cached"),
                    },
                    "network": _network_for_ticker(company["ticker"], user_id=user_id),
                }
            )

        ordered_companies = [
            company
            for portfolio_company in PORTFOLIO
            for company in company_by_id.values()
            if company["ticker"] == portfolio_company["ticker"]
        ]
        if alert_preferences.get("enabled", True):
            items.extend(_market_digest_items(client, company_by_id, user_id, alert_preferences))
        items.extend(_news_digest_items(ordered_companies, user_id))
        items.sort(key=lambda item: {"High": 0, "Medium": 1, "Low": 2}.get(item["priority"], 3))

        return {
            "window": window,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "provenance": "Supabase + market data + contextual GNews",
            "portfolioCount": len(company_by_id),
            "portfolio": list(company_by_id.values()),
            "items": items,
            "alertPreferences": alert_preferences,
            "notice": "Today combines primary-source updates, market signals, and contextual news. News is never used as Pull evidence.",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Primary-source feed is unavailable: {exc}") from exc


@app.get("/alerts/preferences")
def get_alert_preferences(user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    client = get_supabase_client(admin=True)
    return _load_alert_preferences(client, user_id)


@app.put("/alerts/preferences")
def save_alert_preferences(payload: AlertPreferencesInput, user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    try:
        client = get_supabase_client(admin=True)
        row = {
            "user_id": user_id,
            **payload.model_dump(),
        }
        saved = (
            client.table("alert_preferences")
            .upsert(row, on_conflict="user_id")
            .select("enabled,price_rise_threshold,price_fall_threshold,volume_multiplier,material_filings,watched_scope")
            .single()
            .execute()
        ).data
        return {**(saved or row), "storage_ready": True}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Alert preferences are not available yet. Run supabase/alert_preferences_migration.sql in Supabase SQL Editor, then retry.") from exc


@app.get("/opportunities")
def opportunities(limit: int = Query(default=8, ge=1, le=20), user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Rank tracked NSE/BSE companies by recent EOD price and volume movement."""
    try:
        client = get_supabase_client(admin=True)
        companies = (client.table("companies").select("id,ticker,name,sector").limit(250).execute()).data or []
        if not companies:
            return {"items": [], "provenance": "Supabase market_daily", "notice": "No companies are available for opportunity discovery yet."}
        company_by_id = {str(row["id"]): row for row in companies}
        rows = (
            client.table("market_daily")
            .select("company_id,trading_date,close,volume,source,provenance")
            .in_("company_id", list(company_by_id))
            .order("trading_date", desc=True)
            .limit(min(len(companies) * 21, 5000))
            .execute()
        ).data or []
        by_company: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_company.setdefault(str(row["company_id"]), []).append(row)

        ranked: list[tuple[float, dict[str, Any]]] = []
        for company_id, company_rows in by_company.items():
            if len(company_rows) < 2:
                continue
            latest, previous = company_rows[0], company_rows[1]
            latest_close, previous_close = float(latest.get("close") or 0), float(previous.get("close") or 0)
            if not previous_close:
                continue
            change = (latest_close - previous_close) / abs(previous_close) * 100
            prior_volumes = [float(row.get("volume") or 0) for row in company_rows[1:21] if row.get("volume")]
            average_volume = sum(prior_volumes) / len(prior_volumes) if prior_volumes else 0
            volume_ratio = float(latest.get("volume") or 0) / average_volume if average_volume else 0
            if abs(change) < 2 and volume_ratio < 1.5:
                continue
            company = company_by_id[company_id]
            gainer = change >= 0
            ranked.append(
                (
                    abs(change) * 0.7 + min(volume_ratio, 5) * 3,
                    {
                        "id": f"opportunity-{company['ticker']}-{latest['trading_date']}",
                        "ticker": company["ticker"],
                        "company": company["name"],
                        "kind": "Top gainer" if gainer else "Top mover",
                        "priority": "High" if abs(change) >= 5 or volume_ratio >= 3 else "Medium",
                        "title": f"{company['ticker']} {('rose' if gainer else 'fell')} {abs(change):.1f}% in the latest session",
                        "summary": f"EOD close moved from {previous_close:.2f} to {latest_close:.2f}." + (f" Volume was {volume_ratio:.1f}× its recent average." if volume_ratio else ""),
                        "impact": "A discovery signal, not an investment conclusion. Open Research to verify the move against primary-source company evidence.",
                        "metric": {"label": "EOD return", "value": f"{change:+.1f}%", "tone": "positive" if gainer else "warning"},
                        "source": {"label": latest.get("source") or "Market data", "type": "market_data", "page": None, "url": None, "provenance": latest.get("provenance") or "verified"},
                        "network": _network_for_ticker(company["ticker"], user_id=user_id),
                    },
                )
            )
        ranked.sort(key=lambda item: item[0], reverse=True)
        return {
            "items": [item for _, item in ranked[:limit]],
            "provenance": "Supabase market_daily",
            "notice": "Companies are ranked from stored NSE EOD price and volume data. A move is a prompt for research, not a recommendation.",
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Opportunity feed is unavailable: {exc}") from exc


@app.get("/market")
def market(limit: int = Query(default=20, ge=1, le=50), user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Return latest stored EOD quotes and compact sparkline series."""
    try:
        client = get_supabase_client(admin=True)
        companies = (client.table("companies").select("id,ticker,name,sector").limit(250).execute()).data or []
        company_by_id = {str(row["id"]): row for row in companies}
        if not company_by_id:
            return {"companies": [], "provenance": "Supabase market_daily", "notice": "Seed companies before loading the market dashboard."}
        rows = (
            client.table("market_daily")
            .select("company_id,trading_date,close,volume,source,provenance")
            .in_("company_id", list(company_by_id))
            .order("trading_date", desc=True)
            .limit(min(len(company_by_id) * 21, 5000))
            .execute()
        ).data or []
        by_company: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            by_company.setdefault(str(row["company_id"]), []).append(row)
        quotes: list[dict[str, Any]] = []
        for company_id, company_rows in by_company.items():
            if not company_rows:
                continue
            latest = company_rows[0]
            latest_close = float(latest.get("close") or 0)
            previous_close = float(company_rows[1].get("close") or 0) if len(company_rows) > 1 else latest_close
            change = (latest_close - previous_close) / abs(previous_close) * 100 if previous_close else 0
            quotes.append(
                {
                    "ticker": company_by_id[company_id]["ticker"],
                    "name": company_by_id[company_id]["name"],
                    "sector": company_by_id[company_id].get("sector"),
                    "price": latest_close,
                    "change_percent": round(change, 2),
                    "trading_date": latest.get("trading_date"),
                    "series": [float(row.get("close") or 0) for row in reversed(company_rows[:20])],
                    "source": latest.get("source") or "Market data",
                    "provenance": latest.get("provenance") or "verified",
                }
            )
        quotes.sort(key=lambda item: abs(item["change_percent"]), reverse=True)
        return {"companies": quotes[:limit], "provenance": "Supabase market_daily", "notice": "Prices and sparklines use stored end-of-day market data."}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Market dashboard is unavailable: {exc}") from exc


@app.post("/market/refresh")
def refresh_market(user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Fetch and persist the latest EOD data for the stored company universe."""
    try:
        client = get_supabase_client(admin=True)
        companies = (client.table("companies").select("id,ticker").limit(250).execute()).data or []
        results: list[dict[str, Any]] = []
        for company in companies:
            ticker = normalize_nse_ticker(company["ticker"])
            try:
                records = fetch_daily_market_data(ticker, period="3mo")
                rows = [
                    {
                        "company_id": company["id"], "trading_date": record["trading_date"],
                        "close": record["close"], "volume": record["volume"],
                        "source": record["source"], "provenance": record["provenance"],
                    }
                    for record in records
                ]
                if rows:
                    client.table("market_daily").upsert(rows, on_conflict="company_id,trading_date").execute()
                results.append({"ticker": ticker, "rows": len(rows), "status": "ingested"})
            except Exception as exc:
                results.append({"ticker": ticker, "rows": 0, "status": "failed", "message": str(exc)})
        total_rows = sum(item["rows"] for item in results)
        if total_rows == 0:
            raise HTTPException(status_code=503, detail="Yahoo Finance did not return usable EOD data. It may be temporarily rate-limiting requests; wait 30–60 seconds and retry, or run the market ingestion script later.")
        return {"companies": len(results), "rows": total_rows, "results": results, "notice": "Latest EOD prices loaded. Refresh the dashboard to see charts."}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Market data could not be refreshed: {exc}") from exc


@app.post("/chat")
def chat(payload: ChatInput, user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Answer from annual-report and earnings-call chunks only."""
    normalized = payload.ticker.upper().replace(".NS", "").replace(".BO", "") if payload.ticker else None
    try:
        client = get_supabase_client(admin=True)
        company_query = client.table("companies").select("id,ticker,name").limit(250)
        if normalized:
            company_query = company_query.eq("ticker", normalized)
        companies = company_query.execute().data or []
        if normalized and not companies:
            return {"available": False, "answer": f"{normalized} is not in FINN's company universe. Add it first or ask about a supported company.", "sources": [], "caveat": "No company record was found."}
        company_ids = [str(item["id"]) for item in companies]
        if not company_ids:
            return {"available": False, "answer": "No company evidence is available yet. Add a company or ingest its annual report first.", "sources": [], "caveat": "No company records were found."}
        documents = (
            client.table("source_documents")
            .select("id,title,source_type,source_url,provenance")
            .in_("company_id", company_ids)
            .in_("source_type", list(ALLOWED_SOURCE_TYPES))
            .order("created_at", desc=True)
            .limit(8)
            .execute()
        ).data or []
        if not documents:
            return {"available": False, "answer": "I do not have an annual report or earnings-call transcript for that question yet.", "sources": [], "caveat": "Ask again after primary-source documents are ingested."}
        chunks: list[dict[str, Any]] = []
        source_index: dict[str, dict[str, Any]] = {}
        for document in documents:
            chunk_rows = (
                client.table("document_chunks")
                .select("id,page_number,content")
                .eq("document_id", document["id"])
                .order("page_number")
                .limit(12)
                .execute()
            ).data or []
            for chunk in chunk_rows:
                source_index[str(chunk["id"])] = document
                chunks.append({"source_id": str(chunk["id"]), "source_type": document["source_type"], "page_number": chunk.get("page_number"), "content": chunk.get("content", "")})
        if not chunks:
            return {"available": False, "answer": "The document exists, but no extractable text is available yet.", "sources": [], "caveat": "Re-ingest the PDF and try again."}
        output = generate_chat(payload.question, chunks, normalized)
        sources = []
        for ref in output.get("sources", []):
            document = source_index.get(str(ref.get("source_id")))
            if document:
                source = {"label": document["title"], "page": f"p. {ref['page']}" if ref.get("page") else None, "url": document.get("source_url"), "provenance": document.get("provenance", "verified")}
                if source not in sources:
                    sources.append(source)
        return {"available": True, "answer": output["answer"], "sources": sources, "caveat": output.get("caveat", ""), "model": output.get("model"), "provenance": output.get("provenance")}
    except GeminiTemporarilyUnavailable as exc:
        raise HTTPException(status_code=503, detail={"code": "gemini_temporarily_unavailable", "message": str(exc), "retry_after_seconds": 15}) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Ask FINN is unavailable: {exc}") from exc


@app.get("/research/{ticker}")
def research(ticker: str, demo: bool = Query(default=False), user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    if demo and normalized in RESEARCH:
        return RESEARCH[normalized]
    try:
        live_result = get_live_research(normalized)
    except GeminiTemporarilyUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "gemini_temporarily_unavailable",
                "message": str(exc),
                "retry_after_seconds": 15,
            },
        ) from exc
    live_result["network"] = _network_for_ticker(normalized, user_id=user_id, limit=500)
    return live_result


def _network_for_ticker(
    normalized: str,
    query: str | None = None,
    user_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    company = next((item for item in PORTFOLIO if item["ticker"] == normalized), None)
    try:
        matches = match_contacts(normalized, query, company, user_id, limit=limit)
        if matches:
            return matches
    except Exception:
        # A missing network table must not break the Push or Pull workflows.
        pass
    return NETWORK.get(normalized, [])


@app.get("/network/matches")
def network_matches(
    ticker: str = Query(default="TCS"),
    query: str | None = Query(default=None),
    limit: int = Query(default=500, ge=1, le=500),
    user_id: str = Depends(require_user_id),
) -> dict[str, Any]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    matches = _network_for_ticker(normalized, query, user_id, limit=limit)
    provenance = "Supabase user network" if matches and any(item.get("source") for item in matches) else "Synthetic demo fixture"
    return {"ticker": normalized, "query": query, "matches": matches, "provenance": provenance}


def _linkedin_frontend_redirect(status: str, message: str) -> RedirectResponse:
    frontend = os.getenv("LINKEDIN_FRONTEND_URL", "http://localhost:3000").rstrip("/")
    query = urlencode({"linkedin": status, "message": message[:240]})
    return RedirectResponse(f"{frontend}/?{query}")


@app.get("/auth/linkedin/start")
def linkedin_start(user_id: str = Depends(require_user_id)) -> dict[str, str]:
    try:
        state = create_oauth_state(user_id)
        return {"authorization_url": authorization_url(state)}
    except LinkedInNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/auth/linkedin/callback")
def linkedin_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
) -> RedirectResponse:
    user_id = consume_oauth_context(state) if state else None
    if not user_id:
        return _linkedin_frontend_redirect("error", "LinkedIn authorization state expired. Please try again.")
    if error:
        return _linkedin_frontend_redirect("error", error_description or error)
    if not code:
        return _linkedin_frontend_redirect("error", "LinkedIn did not return an authorization code.")
    try:
        from linkedin_service import exchange_code

        access_token = exchange_code(code)
        result = import_connections(access_token, user_id)
        return _linkedin_frontend_redirect("connected", f"Imported {result['inserted']} LinkedIn contacts; {len(result['duplicates'])} duplicates skipped.")
    except (LinkedInNotConfigured, LinkedInRequestFailed) as exc:
        return _linkedin_frontend_redirect("error", str(exc))
    except Exception:
        return _linkedin_frontend_redirect("error", "LinkedIn import failed. Check the backend logs and LinkedIn app permissions.")


@app.get("/network/people")
def network_people(user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    try:
        return {"contacts": list_contacts(user_id), "provenance": "Supabase user network"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Network storage is unavailable: {exc}") from exc


@app.post("/network/people")
def create_network_person(contact: NetworkContactInput, user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    try:
        result = insert_contacts([contact], "manual", "Manual contact", user_id)
        return {**result, "provenance": "Supabase user network"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Network storage is unavailable: {exc}") from exc


@app.post("/network/import/csv/preview")
async def preview_network_csv(file: UploadFile = File(...), user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    content = await file.read()
    return {"filename": file.filename, **parse_csv_bytes(content)}


@app.post("/network/import/csv")
async def import_network_csv(file: UploadFile = File(...), user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    content = await file.read()
    parsed = parse_csv_bytes(content)
    if not parsed["valid_rows"]:
        raise HTTPException(status_code=422, detail={"message": "No valid contact rows found.", **parsed})
    contacts = [NetworkContactInput.model_validate(row) for row in parsed["valid_rows"]]
    try:
        result = insert_contacts(contacts, "csv_import", "CSV import", user_id)
        return {"filename": file.filename, "errors": parsed["errors"], **result, "provenance": "Supabase user network"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Network storage is unavailable: {exc}") from exc


def _portfolio_match(query: str) -> dict[str, Any] | None:
    normalized = query.strip().upper().replace(".NS", "").replace(".BO", "")
    folded = query.strip().casefold()
    return next(
        (
            item
            for item in SUPPORTED_COMPANIES
            if item["ticker"] == normalized or item["name"].casefold() == folded
        ),
        None,
    )


def _primary_source_readiness(client: Any, company_id: str) -> tuple[int, bool]:
    documents_response = (
        client.table("source_documents")
        .select("id")
        .eq("company_id", company_id)
        .in_("source_type", ["annual_report", "earnings_call_transcript"])
        .execute()
    )
    documents = documents_response.data or []
    if not documents:
        return 0, False
    chunks_response = (
        client.table("document_chunks")
        .select("id")
        .in_("document_id", [document["id"] for document in documents])
        .limit(1)
        .execute()
    )
    return len(documents), bool(chunks_response.data)


@app.get("/companies")
def companies() -> dict[str, Any]:
    return {"companies": PORTFOLIO}


@app.get("/portfolio/companies")
def portfolio_companies(user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Return the default universe plus companies explicitly added by this user."""
    try:
        client = get_supabase_client(admin=True)
        memberships = (
            client.table("portfolio_companies")
            .select("company_id")
            .eq("tenant_id", user_id)
            .execute()
        ).data or []
        company_ids = [row["company_id"] for row in memberships if row.get("company_id")]
        added: list[dict[str, Any]] = []
        if company_ids:
            added = (
                client.table("companies")
                .select("ticker,name,sector")
                .in_("id", company_ids)
                .execute()
            ).data or []
        by_ticker = {item["ticker"]: item for item in PORTFOLIO}
        for item in added:
            by_ticker[item["ticker"]] = item
        return {"companies": list(by_ticker.values())}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Portfolio storage is unavailable: {exc}") from exc


@app.post("/portfolio/companies")
def add_portfolio_company(payload: PortfolioCompanyInput, user_id: str = Depends(require_user_id)) -> dict[str, Any]:
    """Add a supported company and report whether primary-source research is ready."""
    match = _portfolio_match(payload.query)
    if not match:
        raise HTTPException(
            status_code=404,
            detail="Company not found in the supported universe. Use a tracked NSE/BSE ticker or company name.",
        )

    try:
        client = get_supabase_client(admin=True)
        company_response = (
            client.table("companies")
            .upsert(
                {
                    "ticker": match["ticker"],
                    "name": match["name"],
                    "sector": match["sector"],
                },
                on_conflict="ticker",
            )
            .select("id,ticker,name,sector")
            .single()
            .execute()
        )
        company = company_response.data
        if not company:
            raise RuntimeError("Company could not be created")

        client.table("portfolio_companies").upsert(
            {"tenant_id": user_id, "company_id": company["id"]},
            on_conflict="tenant_id,company_id",
        ).execute()
        document_fetch = fetch_and_ingest_annual_report(
            client,
            ticker=company["ticker"],
            company_id=company["id"],
        )
        document_count, research_ready = _primary_source_readiness(client, company["id"])
        if research_ready:
            message = f"{company['name']} added. Primary-source research is ready."
        elif document_count:
            message = f"{company['name']} added. Documents exist, but extractable text is not ready yet."
        elif document_fetch["status"] == "failed":
            message = f"{company['name']} added, but its annual report could not be ingested. {document_fetch['message']}"
        else:
            message = f"{company['name']} added. Upload and ingest an annual report or earnings-call transcript to enable research."
        return {
            "company": {key: company[key] for key in ("ticker", "name", "sector")},
            "research_ready": research_ready,
            "documents": document_count,
            "document_fetch": document_fetch,
            "message": message,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Portfolio storage is unavailable: {exc}") from exc


@app.get("/news")
def news(
    ticker: str | None = Query(default=None),
    query: str | None = Query(default=None),
    max_results: int = Query(default=10, ge=1, le=10),
) -> dict[str, Any]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "") if ticker else None
    company = next((item for item in PORTFOLIO if item["ticker"] == normalized), None)
    search_query = query or (company["name"] if company else None)
    if not search_query:
        return {"query": None, "totalArticles": 0, "articles": [], "provenance": "GNews API", "useInPull": False, "notice": "Provide ticker or query."}
    try:
        result = search_news(search_query, max_results=max_results)
        result["ticker"] = normalized
        return result
    except GNewsNotConfigured:
        return {"query": search_query, "totalArticles": 0, "articles": [], "provenance": "GNews API", "useInPull": False, "notice": "GNEWS_API_KEY is not configured in the backend."}
    except GNewsRequestFailed as exc:
        return {"query": search_query, "totalArticles": 0, "articles": [], "provenance": "GNews API", "useInPull": False, "notice": str(exc)}
