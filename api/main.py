from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import File, FastAPI, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from research_service import get_live_research
from news import GNewsNotConfigured, search_news
from network_service import NetworkContactInput, insert_contacts, list_contacts, match_contacts, parse_csv_bytes


app = FastAPI(title="FINN API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/digest")
def digest(window: str = Query(default="24h")) -> dict[str, Any]:
    return {
        "window": window,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "provenance": "Synthetic demo fixture",
        "portfolioCount": len(PORTFOLIO),
        "portfolio": PORTFOLIO,
        "items": ANNOUNCEMENTS,
    }


@app.get("/research/{ticker}")
def research(ticker: str, demo: bool = Query(default=False)) -> dict[str, Any]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    if demo and normalized in RESEARCH:
        return RESEARCH[normalized]
    live_result = get_live_research(normalized)
    live_result["network"] = _network_for_ticker(normalized)
    return live_result


def _network_for_ticker(normalized: str, query: str | None = None) -> list[dict[str, Any]]:
    company = next((item for item in PORTFOLIO if item["ticker"] == normalized), None)
    try:
        matches = match_contacts(normalized, query, company)
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
) -> dict[str, Any]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    matches = _network_for_ticker(normalized, query)
    provenance = "Supabase user network" if matches and any(item.get("source") for item in matches) else "Synthetic demo fixture"
    return {"ticker": normalized, "query": query, "matches": matches, "provenance": provenance}


@app.get("/network/people")
def network_people() -> dict[str, Any]:
    try:
        return {"contacts": list_contacts(), "provenance": "Supabase user network"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Network storage is unavailable: {exc}") from exc


@app.post("/network/people")
def create_network_person(contact: NetworkContactInput) -> dict[str, Any]:
    try:
        result = insert_contacts([contact], "manual", "Manual contact")
        return {**result, "provenance": "Supabase user network"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Network storage is unavailable: {exc}") from exc


@app.post("/network/import/csv/preview")
async def preview_network_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    return {"filename": file.filename, **parse_csv_bytes(content)}


@app.post("/network/import/csv")
async def import_network_csv(file: UploadFile = File(...)) -> dict[str, Any]:
    content = await file.read()
    parsed = parse_csv_bytes(content)
    if not parsed["valid_rows"]:
        raise HTTPException(status_code=422, detail={"message": "No valid contact rows found.", **parsed})
    contacts = [NetworkContactInput.model_validate(row) for row in parsed["valid_rows"]]
    try:
        result = insert_contacts(contacts, "csv_import", "CSV import")
        return {"filename": file.filename, "errors": parsed["errors"], **result, "provenance": "Supabase user network"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Network storage is unavailable: {exc}") from exc


@app.get("/companies")
def companies() -> dict[str, Any]:
    return {"companies": PORTFOLIO}


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
