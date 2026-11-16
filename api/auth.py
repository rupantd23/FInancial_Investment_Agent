"""FastAPI authentication helpers for Supabase Auth sessions."""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from fastapi import Header, HTTPException


load_dotenv(Path(__file__).resolve().with_name(".env"))


def _publishable_key() -> str | None:
    return os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")


def _extract_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to use this FINN workspace.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Your FINN session token is missing.")
    return token


def require_user_id(authorization: str | None = Header(default=None)) -> str:
    """Validate a Supabase access token and return the authenticated user UUID."""
    token = _extract_token(authorization)
    base_url = os.getenv("SUPABASE_URL")
    publishable_key = _publishable_key()
    if not base_url or not publishable_key:
        raise HTTPException(status_code=503, detail="Supabase Auth is not configured in the backend.")

    try:
        response = requests.get(
            f"{base_url.rstrip('/')}/auth/v1/user",
            headers={"apikey": publishable_key, "Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.RequestException as exc:
        raise HTTPException(status_code=503, detail="Supabase Auth could not be reached.") from exc

    if not response.ok:
        raise HTTPException(status_code=401, detail="Your FINN session has expired. Please sign in again.")
    try:
        user_id = response.json().get("id")
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Supabase returned an invalid session.") from exc
    if not user_id:
        raise HTTPException(status_code=401, detail="Supabase did not return a user identity.")
    return str(user_id)
