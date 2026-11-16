"""Optional LinkedIn OAuth and first-degree connection import."""

from __future__ import annotations

import os
import secrets
import time
from typing import Any
from urllib.parse import urlencode

import requests

from network_service import NetworkContactInput, insert_contacts


AUTHORIZATION_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
CONNECTIONS_URL = "https://api.linkedin.com/v2/connections"
_pending_states: dict[str, tuple[float, str | None]] = {}


class LinkedInNotConfigured(RuntimeError):
    pass


class LinkedInRequestFailed(RuntimeError):
    pass


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise LinkedInNotConfigured(f"{name} is not configured")
    return value


def connections_enabled() -> bool:
    return os.getenv("LINKEDIN_CONNECTIONS_ENABLED", "false").lower() in {"1", "true", "yes"}


def _scopes() -> str:
    scopes = ["openid", "profile", "email"]
    if connections_enabled():
        scopes.append("r_1st_connections")
    return " ".join(scopes)


def create_oauth_state(user_id: str | None = None) -> str:
    now = time.time()
    _pending_states.update({key: value for key, value in list(_pending_states.items()) if now - value[0] < 600})
    state = secrets.token_urlsafe(32)
    _pending_states[state] = (now, user_id)
    return state


def consume_oauth_state(state: str) -> bool:
    value = _pending_states.pop(state, None)
    return bool(value and time.time() - value[0] < 600)


def consume_oauth_context(state: str) -> str | None:
    value = _pending_states.pop(state, None)
    if not value or time.time() - value[0] >= 600:
        return None
    return value[1]


def authorization_url(state: str) -> str:
    client_id = _required_env("LINKEDIN_CLIENT_ID")
    redirect_uri = _required_env("LINKEDIN_REDIRECT_URI")
    if not connections_enabled():
        raise LinkedInNotConfigured("Set LINKEDIN_CONNECTIONS_ENABLED=true after LinkedIn approves r_1st_connections")
    return f"{AUTHORIZATION_URL}?{urlencode({'response_type': 'code', 'client_id': client_id, 'redirect_uri': redirect_uri, 'state': state, 'scope': _scopes()})}"


def _request_json(response: requests.Response, operation: str) -> dict[str, Any]:
    if not response.ok:
        detail = response.text[:500]
        raise LinkedInRequestFailed(f"LinkedIn {operation} failed ({response.status_code}): {detail}")
    return response.json()


def exchange_code(code: str) -> str:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "client_id": _required_env("LINKEDIN_CLIENT_ID"),
            "client_secret": _required_env("LINKEDIN_CLIENT_SECRET"),
            "redirect_uri": _required_env("LINKEDIN_REDIRECT_URI"),
        },
        timeout=15,
    )
    payload = _request_json(response, "token exchange")
    token = payload.get("access_token")
    if not token:
        raise LinkedInRequestFailed("LinkedIn token response did not include an access token")
    return str(token)


def fetch_userinfo(access_token: str) -> dict[str, Any]:
    response = requests.get(USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}, timeout=15)
    return _request_json(response, "profile request")


def _localized(profile: dict[str, Any], key: str) -> str | None:
    value = profile.get(key)
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        localized = value.get("localized") or {}
        if localized:
            return next(iter(localized.values()))
    return None


def fetch_connections(access_token: str) -> list[NetworkContactInput]:
    response = requests.get(
        CONNECTIONS_URL,
        params={
            "q": "viewer",
            "start": 0,
            "count": 50,
            "projection": "(elements(*(to~)),paging)",
        },
        headers={
            "Authorization": f"Bearer {access_token}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        timeout=20,
    )
    payload = _request_json(response, "connections request")
    contacts: list[NetworkContactInput] = []
    for element in payload.get("elements", []):
        profile = element.get("to~") or {}
        first = _localized(profile, "firstName") or ""
        last = _localized(profile, "lastName") or ""
        name = " ".join(part for part in [first, last] if part).strip()
        if not name:
            continue
        contacts.append(
            NetworkContactInput(
                name=name,
                role=_localized(profile, "headline"),
                linkedin_url=None,
            )
        )
    return contacts


def import_connections(access_token: str, user_id: str | None = None) -> dict[str, Any]:
    # Fetching userinfo validates the member token before importing connections.
    fetch_userinfo(access_token)
    contacts = fetch_connections(access_token)
    result = insert_contacts(contacts, "linkedin", "LinkedIn first-degree connection", user_id) if contacts else {"inserted": 0, "duplicates": [], "contacts": []}
    return {"fetched": len(contacts), **result}
