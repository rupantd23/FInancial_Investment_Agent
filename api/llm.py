"""Gemini adapter for source-grounded FINN research.

The adapter accepts retrieved primary-source chunks and returns validated JSON.
It deliberately does not fetch web content or calculate financial metrics.
"""

from __future__ import annotations

import os
from typing import Any

from pydantic import BaseModel, Field


ALLOWED_SOURCE_TYPES = {"annual_report", "earnings_call_transcript"}


class GeminiNotConfigured(RuntimeError):
    pass


class ResearchClaim(BaseModel):
    text: str
    status: str = Field(description="verified, calculated, interpreted, or unavailable")
    source_id: str | None = None
    page: int | None = None


class ResearchMetric(BaseModel):
    label: str
    value: str
    trend: str = Field(default="neutral", description="up, down, flat, or neutral")


class ResearchSourceRef(BaseModel):
    source_id: str
    page: int | None = None


class ResearchInsight(BaseModel):
    text: str
    status: str = Field(description="verified, calculated, interpreted, or unavailable")
    source_id: str | None = None
    page: int | None = None
    metrics: list[ResearchMetric] = Field(default_factory=list)


class ResearchCase(BaseModel):
    text: str
    sources: list[ResearchSourceRef] = Field(default_factory=list)


class ResearchOutput(BaseModel):
    summary: str
    summary_sources: list[ResearchSourceRef] = Field(default_factory=list)
    business_snapshot: ResearchInsight
    financial_snapshot: ResearchInsight
    trajectory: ResearchInsight
    balance_sheet: ResearchInsight
    cash_quality: ResearchInsight
    narrative_vs_numbers: ResearchInsight
    guidance: ResearchInsight
    claims: list[ResearchClaim]
    missing_evidence: list[str]
    bull_case: ResearchCase
    bear_case: ResearchCase


SYSTEM_INSTRUCTION = """You are FINN's evidence-grounded public-markets research assistant.

Use only the supplied annual-report and earnings-call transcript excerpts.
Do not use general knowledge, news, broker notes, or unstated assumptions.
If the supplied excerpts do not support a requested fact, use status=unavailable,
leave its source fields empty, and add the topic to missing_evidence. Never invent
financial figures, guidance, biographies, or relationships. Financial arithmetic
is performed by the application, not by you. Every supported insight, claim, and
case must include source_id and page references when evidence exists. Use metrics
only for figures explicitly present in the supplied excerpts; preserve the source
wording and units. Interpretations must be labeled interpreted. Return only valid
JSON matching the supplied schema. Keep the response compact: use at most 4
claims, keep each claim under 35 words, keep each insight under 45 words, keep
the summary under 60 words, and keep each bull/bear case under 45 words.
"""


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def build_research_prompt(ticker: str, chunks: list[dict[str, Any]]) -> str:
    """Build a bounded prompt from permitted primary-source chunks only."""
    permitted = [
        chunk
        for chunk in chunks
        if chunk.get("source_type") in ALLOWED_SOURCE_TYPES and chunk.get("content")
    ]

    evidence = []
    for index, chunk in enumerate(permitted, start=1):
        source_id = str(chunk.get("source_id", f"chunk-{index}"))
        page = chunk.get("page_number", "unknown")
        source_type = chunk["source_type"]
        evidence.append(
            f"[source_id={source_id} type={source_type} page={page}]\n{chunk['content']}"
        )

    evidence_text = "\n\n".join(evidence) or "NO PERMITTED EVIDENCE WAS RETRIEVED."
    return f"""Research ticker: {ticker.upper()}

Produce a compact research brief with a summary, exactly seven typed insights,
evidence-backed claims, missing evidence, and a bull and bear case. The seven
insights must cover these keys: business_snapshot, financial_snapshot, trajectory,
balance_sheet, cash_quality, narrative_vs_numbers, and guidance. Use a maximum
of four metrics in financial_snapshot and trajectory, and only include metrics
that are explicit in the retrieved evidence. For narrative_vs_numbers, compare
management commentary with reported numbers only when both are present. For
guidance, report only explicit management guidance. Return at most 4 claims.
Keep every field concise so the complete JSON response fits within the output
limit. Do not include markdown or commentary outside the JSON.

Retrieved primary-source evidence:
{evidence_text}
"""


def generate_research(ticker: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    """Call Gemini and validate the structured response."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise GeminiNotConfigured("GEMINI_API_KEY is not set")

    try:
        from google import genai  # type: ignore
        from google.genai import types  # type: ignore
    except ImportError as exc:
        raise GeminiNotConfigured("Install google-genai in the backend environment") from exc

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=_model_name(),
        contents=build_research_prompt(ticker, chunks),
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=ResearchOutput,
            temperature=0.2,
            max_output_tokens=2600,
        ),
    )

    result = ResearchOutput.model_validate_json(response.text)
    return {
        **result.model_dump(),
        "ticker": ticker.upper(),
        "model": _model_name(),
        "provenance": "Gemini interpretation of supplied primary-source chunks",
    }
