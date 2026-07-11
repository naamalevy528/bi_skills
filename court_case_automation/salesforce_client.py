"""Thin client for pushing docket updates into Salesforce.

Uses the standard Salesforce REST API (Case sObject + Files/ContentVersion
for attachments) rather than any browser automation - this side of the
pipeline was never in question, it's plain API-to-API integration.

Auth: an OAuth access token + your org's instance URL (e.g. via a Connected
App / JWT bearer flow). Not implemented here - inject a valid token.
"""

import base64
import os
from typing import Optional

import requests

API_VERSION = "v60.0"


class SalesforceClient:
    def __init__(self, instance_url: Optional[str] = None, access_token: Optional[str] = None,
                 session: Optional[requests.Session] = None):
        self.instance_url = (instance_url or os.environ.get("SF_INSTANCE_URL", "")).rstrip("/")
        self.access_token = access_token or os.environ.get("SF_ACCESS_TOKEN")
        self.session = session or requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        })

    def update_case_fields(self, case_id: str, fields: dict) -> None:
        url = f"{self.instance_url}/services/data/{API_VERSION}/sobjects/Case/{case_id}"
        resp = self.session.patch(url, json=fields, timeout=30)
        resp.raise_for_status()

    def attach_file(self, case_id: str, filename: str, file_bytes: bytes) -> str:
        """Upload a file and link it to the case (Salesforce Files, not the legacy Attachment object)."""
        cv_url = f"{self.instance_url}/services/data/{API_VERSION}/sobjects/ContentVersion"
        payload = {
            "Title": filename,
            "PathOnClient": filename,
            "VersionData": base64.b64encode(file_bytes).decode("ascii"),
        }
        resp = self.session.post(cv_url, json=payload, timeout=60)
        resp.raise_for_status()
        content_version_id = resp.json()["id"]

        # ContentVersion -> ContentDocumentId lookup, then link it to the Case.
        cv_query = self.session.get(
            f"{self.instance_url}/services/data/{API_VERSION}/sobjects/ContentVersion/{content_version_id}",
            params={"fields": "ContentDocumentId"},
            timeout=30,
        )
        cv_query.raise_for_status()
        content_document_id = cv_query.json()["ContentDocumentId"]

        link_url = f"{self.instance_url}/services/data/{API_VERSION}/sobjects/ContentDocumentLink"
        link_resp = self.session.post(link_url, json={
            "ContentDocumentId": content_document_id,
            "LinkedEntityId": case_id,
            "ShareType": "V",
        }, timeout=30)
        link_resp.raise_for_status()
        return content_document_id
