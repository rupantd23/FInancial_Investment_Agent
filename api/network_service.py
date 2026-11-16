"""User-owned network ingestion and explainable matching for FINN."""

from __future__ import annotations

import csv
import io
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from db import get_supabase_client


CSV_LIMIT = 500


class NetworkContactInput(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    email: str | None = None
    role: str | None = None
    company: str | None = None
    sector: str | None = None
    skills: list[str] = Field(default_factory=list)
    linkedin_url: str | None = None
    relationship: str | None = None
    notes: str | None = None


def _tenant_id(user_id: str | None = None) -> str | None:
    """Use the authenticated user; retain the env fallback for local demo scripts."""
    return user_id or os.getenv("FINN_TENANT_ID") or None


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _tokens(value: str | None) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (value or "").lower())
        if len(token) > 2
        and token not in {"the", "and", "for", "with", "from", "into", "this", "that"}
    }


def _skills(value: Any) -> list[str]:
    if isinstance(value, list):
        return [item for item in (_clean(entry) for entry in value) if item]
    return [item for item in (_clean(entry) for entry in re.split(r"[,;|]", str(value or ""))) if item]


def _value(row: dict[str, Any], *names: str) -> Any:
    normalized = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = normalized.get(name)
        if value is not None and str(value).strip():
            return value
    return None


def parse_csv_bytes(content: bytes) -> dict[str, Any]:
    """Validate a user CSV without writing it to disk or Supabase."""
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return {"row_count": 0, "valid_rows": [], "errors": ["CSV must be UTF-8 encoded."]}

    reader = csv.DictReader(io.StringIO(text))
    headers = {str(header).strip().lower() for header in (reader.fieldnames or []) if header}
    if not headers:
        return {"row_count": 0, "valid_rows": [], "errors": ["CSV must include a header row."]}
    if not headers.intersection({"name", "display_name", "full_name"}):
        return {"row_count": 0, "valid_rows": [], "errors": ["CSV needs a name column: name, display_name, or full_name."]}

    valid_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    row_count = 0
    for row_number, row in enumerate(reader, start=2):
        row_count += 1
        if row_count > CSV_LIMIT:
            errors.append(f"Only the first {CSV_LIMIT} rows can be imported at once.")
            break
        payload = {
            "name": _value(row, "name", "display_name", "full_name"),
            "email": _clean(_value(row, "email", "email_address")),
            "role": _clean(_value(row, "role", "title", "role_title", "job_title")),
            "company": _clean(_value(row, "company", "company_name", "employer", "organization")),
            "sector": _clean(_value(row, "sector", "industry")),
            "skills": _skills(_value(row, "skills", "skill", "expertise")),
            "linkedin_url": _clean(_value(row, "linkedin_url", "linkedin", "profile_url")),
            "relationship": _clean(_value(row, "relationship", "how_do_you_know_them")),
            "notes": _clean(_value(row, "notes", "note", "context")),
        }
        try:
            valid_rows.append(NetworkContactInput.model_validate(payload).model_dump())
        except Exception as exc:
            errors.append(f"Row {row_number}: {exc.errors()[0]['msg'] if hasattr(exc, 'errors') else str(exc)}")

    return {"row_count": row_count, "valid_rows": valid_rows, "errors": errors}


def _scope_query(client: Any, user_id: str | None = None) -> Any:
    query = client.table("network_people").select(
        "id,display_name,email,role_title,company_name,sector,skills,linkedin_url,relationship,notes,provenance,source_label,created_at"
    )
    tenant_id = _tenant_id(user_id)
    return query.eq("tenant_id", tenant_id) if tenant_id else query.is_("tenant_id", "null")


def list_contacts(user_id: str | None = None) -> list[dict[str, Any]]:
    client = get_supabase_client(admin=True)
    response = _scope_query(client, user_id).order("created_at", desc=True).execute()
    return response.data or []


def _contact_row(contact: NetworkContactInput, provenance: str, source_label: str, user_id: str | None = None) -> dict[str, Any]:
    return {
        "tenant_id": _tenant_id(user_id),
        "display_name": contact.name.strip(),
        "email": contact.email,
        "role_title": contact.role,
        "company_name": contact.company,
        "sector": contact.sector,
        "skills": contact.skills,
        "linkedin_url": contact.linkedin_url,
        "relationship": contact.relationship,
        "notes": contact.notes,
        "provenance": provenance,
        "consent_status": "user_provided",
        "source_label": source_label,
    }


def _duplicate_key(contact: dict[str, Any]) -> tuple[str, str, str]:
    linkedin = re.sub(r"\W", "", str(contact.get("linkedin_url") or "").lower())
    name = " ".join(str(contact.get("display_name") or contact.get("name") or "").lower().split())
    company = " ".join(str(contact.get("company_name") or contact.get("company") or "").lower().split())
    return linkedin, name, company


def _insert_evidence(client: Any, person_id: str, contact: NetworkContactInput, source: str) -> None:
    evidence: list[dict[str, Any]] = []
    if contact.company:
        evidence.append({"person_id": person_id, "evidence_type": "employer_overlap", "detail": f"Contact lists {contact.company} as an employer or company context.", "source": source, "confidence": 0.65})
    if contact.sector:
        evidence.append({"person_id": person_id, "evidence_type": "sector_expertise", "detail": f"Contact is associated with the {contact.sector} sector.", "source": source, "confidence": 0.55})
    if contact.relationship:
        evidence.append({"person_id": person_id, "evidence_type": "user_relationship", "detail": contact.relationship, "source": source, "confidence": 0.7})
    if evidence:
        client.table("network_evidence").insert(evidence).execute()


def insert_contacts(contacts: list[NetworkContactInput], provenance: str, source_label: str, user_id: str | None = None) -> dict[str, Any]:
    client = get_supabase_client(admin=True)
    existing = list_contacts(user_id)
    existing_keys = {_duplicate_key(row) for row in existing}
    inserted: list[dict[str, Any]] = []
    duplicates: list[str] = []

    for contact in contacts:
        key = _duplicate_key(contact.model_dump())
        if key in existing_keys:
            duplicates.append(contact.name)
            continue
        response = client.table("network_people").insert(_contact_row(contact, provenance, source_label, user_id)).execute()
        row = (response.data or [None])[0]
        if row:
            inserted.append(row)
            _insert_evidence(client, str(row["id"]), contact, provenance)
            existing_keys.add(key)

    return {"inserted": len(inserted), "duplicates": duplicates, "contacts": inserted}


def _company_context(ticker: str, company: dict[str, Any] | None) -> tuple[str, str]:
    if company:
        return str(company.get("name") or ticker), str(company.get("sector") or "")
    return ticker, ""


def match_contacts(
    ticker: str,
    query: str | None,
    company: dict[str, Any] | None,
    user_id: str | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    people = list_contacts(user_id)
    company_name, sector = _company_context(ticker, company)
    company_tokens = _tokens(f"{ticker} {company_name}")
    sector_tokens = _tokens(sector)
    query_tokens = _tokens(query)
    matches: list[dict[str, Any]] = []

    for person in people:
        profile_text = " ".join([
            str(person.get("display_name") or ""),
            str(person.get("role_title") or ""),
            str(person.get("company_name") or ""),
            str(person.get("sector") or ""),
            " ".join(person.get("skills") or []),
            str(person.get("relationship") or ""),
            str(person.get("notes") or ""),
        ])
        profile_tokens = _tokens(profile_text)
        company_overlap = company_tokens.intersection(_tokens(str(person.get("company_name") or "")))
        sector_overlap = sector_tokens.intersection(_tokens(str(person.get("sector") or "")))
        query_overlap = query_tokens.intersection(profile_tokens)
        relationship = bool(person.get("relationship"))
        score = (45 if company_overlap else 0) + (25 if sector_overlap else 0) + (25 if query_overlap else 0) + (5 if relationship else 0)
        if score < 50:
            continue

        reasons: list[str] = []
        evidence = "Skill or role overlap"
        if company_overlap:
            reasons.append(f"company context overlaps with {company_name}")
            evidence = "Employer overlap"
        if sector_overlap:
            reasons.append(f"sector expertise overlaps with {sector}")
            if not company_overlap:
                evidence = "Sector expertise"
        if query_overlap:
            reasons.append(f"profile matches {', '.join(sorted(query_overlap))}")
        if relationship:
            reasons.append("user-provided relationship context is available")
            if not company_overlap and not sector_overlap:
                evidence = "User-provided context"

        source_label = person.get("source_label") or str(person.get("provenance") or "User-provided")
        caveat = "User-provided profile; relevance does not prove a personal relationship."
        if person.get("provenance") == "synthetic_demo":
            caveat = "Synthetic profile for demonstration only."
        matches.append({
            "personId": str(person["id"]),
            "name": person.get("display_name"),
            "role": person.get("role_title") or "Role not provided",
            "score": min(score, 99),
            "reason": "; ".join(reasons).capitalize() + ".",
            "evidence": evidence,
            "source": source_label,
            "caveat": caveat,
        })

    return sorted(matches, key=lambda match: match["score"], reverse=True)[:limit]
