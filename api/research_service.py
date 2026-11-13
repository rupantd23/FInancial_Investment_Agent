"""Supabase-backed retrieval and Gemini research orchestration."""

from __future__ import annotations

from typing import Any

from db import get_supabase_client
from llm import ALLOWED_SOURCE_TYPES, generate_research


def _unavailable(ticker: str, message: str, company: str | None = None) -> dict[str, Any]:
    return {
        "ticker": ticker,
        "company": company,
        "available": False,
        "disclosure": message,
        "headline": "Evidence unavailable",
        "sections": [],
        "network": [],
        "provenance": "No permitted primary-source documents available",
    }


def _source_for_claim(claim: dict[str, Any], source_index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    source = source_index.get(str(claim.get("source_id")))
    if not source:
        return None
    return {
        "label": source["title"],
        "type": source["source_type"],
        "page": f"p. {claim['page']}" if claim.get("page") else None,
        "url": source.get("source_url"),
        "provenance": source.get("provenance", "cached"),
    }


def _to_ui_research(
    ticker: str,
    company: dict[str, Any],
    output: dict[str, Any],
    source_index: dict[str, dict[str, Any]],
    document_count: int,
) -> dict[str, Any]:
    sections: list[dict[str, Any]] = [
        {
            "label": "Research summary",
            "text": output["summary"],
            "status": "Interpreted",
            "source": None,
        }
    ]
    for index, claim in enumerate(output["claims"], start=1):
        sections.append(
            {
                "label": f"Evidence {index}",
                "text": claim["text"],
                "status": claim["status"].capitalize(),
                "source": _source_for_claim(claim, source_index),
            }
        )

    sections.extend(
        [
            {"label": "Bull case", "text": output["bull_case"], "status": "Interpreted", "source": None},
            {"label": "Bear case", "text": output["bear_case"], "status": "Interpreted", "source": None},
        ]
    )
    if output["missing_evidence"]:
        sections.append(
            {
                "label": "Missing evidence",
                "text": "; ".join(output["missing_evidence"]),
                "status": "Unavailable",
                "source": None,
            }
        )

    return {
        "ticker": ticker,
        "company": company["name"],
        "available": True,
        "disclosure": f"Generated from {document_count} Supabase primary-source document(s) using Gemini. Financial calculations remain deterministic.",
        "headline": output["summary"],
        "sections": sections,
        "network": [],
        "model": output["model"],
        "provenance": output["provenance"],
    }


def get_live_research(ticker: str) -> dict[str, Any]:
    """Retrieve permitted source chunks and generate a validated research view."""
    normalized = ticker.upper().replace(".NS", "").replace(".BO", "")
    client = get_supabase_client(admin=True)

    company_response = (
        client.table("companies")
        .select("id,ticker,name,sector")
        .eq("ticker", normalized)
        .limit(1)
        .execute()
    )
    companies = company_response.data or []
    if not companies:
        return _unavailable(normalized, "This ticker is not present in the FINN company universe.")

    company = companies[0]
    documents_response = (
        client.table("source_documents")
        .select("id,title,source_type,source_url,provenance,published_at")
        .eq("company_id", company["id"])
        .in_("source_type", list(ALLOWED_SOURCE_TYPES))
        .order("published_at", desc=True)
        .limit(8)
        .execute()
    )
    documents = documents_response.data or []
    if not documents:
        return _unavailable(
            normalized,
            "No annual report or earnings-call transcript has been uploaded for this ticker yet.",
            company["name"],
        )

    chunks: list[dict[str, Any]] = []
    source_index: dict[str, dict[str, Any]] = {}
    for document in documents:
        chunk_response = (
            client.table("document_chunks")
            .select("id,page_number,content")
            .eq("document_id", document["id"])
            .order("page_number")
            .limit(30)
            .execute()
        )
        for chunk in chunk_response.data or []:
            chunk_id = str(chunk["id"])
            source_index[chunk_id] = document
            chunks.append(
                {
                    "source_id": chunk_id,
                    "source_type": document["source_type"],
                    "page_number": chunk.get("page_number"),
                    "content": chunk.get("content", ""),
                }
            )

    if not chunks:
        return _unavailable(
            normalized,
            "Source documents exist, but no extractable text chunks are available yet.",
            company["name"],
        )

    output = generate_research(normalized, chunks)
    return _to_ui_research(normalized, company, output, source_index, len(documents))
