"""The ONLY place that talks to the Gmail API.

It can list, read, label and create drafts. It cannot send, and it never hands the raw
API service to anyone else. Gmail's own permission can't enforce that (there's no
draft-only scope), so this file does.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
LABEL_PREFIX = "Triage/"


@dataclass(frozen=True)
class Email:
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    message_id: str  # the RFC 822 Message-ID header, used to thread the reply


class GmailClient:
    def __init__(self, service):
        self._service = service  # private: nothing outside this class gets it
        self._labels: dict[str, str] = {}

    @classmethod
    def from_token(cls, secrets_dir: Path) -> "GmailClient":
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        token = secrets_dir / "token.json"
        creds = Credentials.from_authorized_user_file(str(token), SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token.write_text(creds.to_json())
        return cls(build("gmail", "v1", credentials=creds, cache_discovery=False))

    def list_unread(self, max_results: int = 25) -> list[str]:
        resp = self._service.users().messages().list(
            userId="me", q="is:unread in:inbox", maxResults=max_results
        ).execute()
        return [m["id"] for m in resp.get("messages", [])]

    def get_message(self, message_id: str) -> Email:
        msg = self._service.users().messages().get(userId="me", id=message_id, format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}
        return Email(
            id=msg["id"],
            thread_id=msg["threadId"],
            sender=headers.get("from", ""),
            subject=headers.get("subject", "(no subject)"),
            body=_plain_text(msg["payload"])[:4000],
            message_id=headers.get("message-id", ""),
        )

    def add_label(self, message_id: str, name: str) -> None:
        label_id = self._label_id(LABEL_PREFIX + name)
        self._service.users().messages().modify(
            userId="me", id=message_id, body={"addLabelIds": [label_id]}
        ).execute()

    def create_draft(self, email: Email, body: str) -> str:
        """A threaded reply to the sender, saved as a draft. Returns the draft id."""
        reply = EmailMessage()
        reply["To"] = parseaddr(email.sender)[1]
        reply["Subject"] = email.subject if email.subject.lower().startswith("re:") else f"Re: {email.subject}"
        if email.message_id:
            reply["In-Reply-To"] = email.message_id
            reply["References"] = email.message_id
        reply.set_content(body)
        raw = base64.urlsafe_b64encode(reply.as_bytes()).decode()
        draft = self._service.users().drafts().create(
            userId="me", body={"message": {"raw": raw, "threadId": email.thread_id}}
        ).execute()
        return draft["id"]

    def _label_id(self, name: str) -> str:
        if not self._labels:
            resp = self._service.users().labels().list(userId="me").execute()
            self._labels = {l["name"]: l["id"] for l in resp.get("labels", [])}
        if name not in self._labels:
            created = self._service.users().labels().create(
                userId="me", body={"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
            ).execute()
            self._labels[name] = created["id"]
        return self._labels[name]


def _plain_text(payload: dict) -> str:
    """The first text/plain part of a message, decoded."""
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")
    for part in payload.get("parts", []) or []:
        text = _plain_text(part)
        if text:
            return text
    return ""
