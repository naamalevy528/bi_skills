"""Thin client for CourtListener / RECAP (Free Law Project).

Why this instead of automating CourtLink: CourtListener is a free, API-first
docket database built specifically for programmatic access - no login
session to script, no ToS conflict, no CAPTCHA/MFA to fight. Coverage is
federal PACER dockets (via RECAP). State-court cases need a different
source (see README) unless/until they're removed to federal court.

Docs: https://www.courtlistener.com/help/api/rest/
Auth: a free account + API token is enough for read access and for
creating docket alerts. No PACER credentials required to *read* what's
already in RECAP.
"""

import os
import time
from typing import Iterable, Optional

import requests

BASE_URL = "https://www.courtlistener.com/api/rest/v4"


class CourtListenerClient:
    def __init__(self, api_token: Optional[str] = None, session: Optional[requests.Session] = None):
        self.api_token = api_token or os.environ.get("COURTLISTENER_API_TOKEN")
        self.session = session or requests.Session()
        headers = {"User-Agent": "darrow-docket-monitor/1.0"}
        if self.api_token:
            headers["Authorization"] = f"Token {self.api_token}"
        self.session.headers.update(headers)

    def _get(self, path: str, params: dict) -> dict:
        resp = self.session.get(f"{BASE_URL}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def search_docket(self, docket_number: str, court: str) -> Optional[dict]:
        """Find a docket by its case number + court short code (e.g. 'cand' for N.D. Cal.)."""
        data = self._get("/search/", {"type": "r", "docket_number": docket_number, "court": court})
        results = data.get("results", [])
        return results[0] if results else None

    def list_docket_entries(self, docket_id: int, since_id: Optional[int] = None) -> list:
        """All entries for a docket, optionally only those newer than a previously-seen entry id."""
        entries = []
        params = {"docket": docket_id, "order_by": "-entry_number"}
        next_url = None
        data = self._get("/docket-entries/", params)
        entries.extend(data.get("results", []))
        while data.get("next") and not next_url:
            # CourtListener paginates; stop early once we cross into already-seen entries.
            if since_id and any(e["id"] <= since_id for e in data["results"]):
                break
            resp = self.session.get(data["next"], timeout=30)
            resp.raise_for_status()
            data = resp.json()
            entries.extend(data.get("results", []))
        if since_id:
            entries = [e for e in entries if e["id"] > since_id]
        return entries

    def create_docket_alert(self, docket_id: int) -> dict:
        """Subscribe to CourtListener's own alerting: emails/webhooks us when this docket updates.

        This is the "set a trigger" step from the user's flow, done through a
        first-party API instead of screen-scraping a login-walled tool.
        """
        resp = self.session.post(f"{BASE_URL}/docket-alerts/", data={"docket": docket_id}, timeout=30)
        resp.raise_for_status()
        return resp.json()
