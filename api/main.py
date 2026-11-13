from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from research_service import get_live_research


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
    live_result["network"] = NETWORK.get(normalized, [])
    return live_result


@app.get("/network/matches")
def network_matches(
    ticker: str = Query(default="TCS"),
    query: str | None = Query(default=None),
) -> dict[str, Any]:
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    matches = NETWORK.get(normalized, [])
    if query:
        terms = query.lower().split()
        matches = [m for m in matches if any(term in (m["reason"] + m["role"]).lower() for term in terms)] or matches
    return {"ticker": normalized, "query": query, "matches": matches, "provenance": "Synthetic demo fixture"}


@app.get("/companies")
def companies() -> dict[str, Any]:
    return {"companies": PORTFOLIO}
