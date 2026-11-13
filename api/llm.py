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


class ResearchOutput(BaseModel):
    summary: str
    claims: list[ResearchClaim]
    missing_evidence: list[str]
    bull_case: str
    bear_case: str


SYSTEM_INSTRUCTION = """You are FINN's evidence-grounded public-markets research assistant.

Use only the supplied annual-report and earnings-call transcript excerpts.
Do not use general knowledge, news, broker notes, or unstated assumptions.
If the supplied excerpts do not support a requested fact, put it in
missing_evidence and use status=unavailable. Never invent financial figures,
guidance, biographies, or relationships. Financial arithmetic is performed by
the application, not by you. Every claim must include the source_id and page
when evidence exists. Interpretations must be labeled interpreted.
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

Produce a compact research brief with a summary, evidence-backed claims,
missing evidence, and a bull and bear case.

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
    except ImportError as exc:
        raise GeminiNotConfigured("Install google-genai in the backend environment") from exc

    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=_model_name(),
        input=build_research_prompt(ticker, chunks),
        system_instruction=SYSTEM_INSTRUCTION,
        response_format=[
            {
                "type": "text",
                "mime_type": "application/json",
                "schema": ResearchOutput.model_json_schema(),
            }
        ],
        generation_config={"temperature": 0.2, "max_output_tokens": 1400},
    )

    result = ResearchOutput.model_validate_json(interaction.output_text)
    return {
        **result.model_dump(),
        "ticker": ticker.upper(),
        "model": _model_name(),
        "provenance": "Gemini interpretation of supplied primary-source chunks",
    }
