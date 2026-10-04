"""Insert the test emails in seed/emails.json into the test inbox as unread mail.

Uses the Gmail API's INSERT scope: the messages are placed straight into the inbox. Nothing is
sent from or to anywhere. This is test-data tooling, separate from the agent (whose scope is
gmail.modify and which can never send).

    python scripts/seed_inbox.py            # insert all
    python scripts/seed_inbox.py --only 3   # insert the first 3
    python scripts/seed_inbox.py --dry-run

Secrets: GMAIL_SECRETS_DIR (default ~/Development/_secrets/inbox-agent) holds credentials.json;
this script keeps its own token in token-seed.json there.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
from email.message import EmailMessage
from email.utils import formatdate
from pathlib import Path
import time

SCOPES = ["https://www.googleapis.com/auth/gmail.insert"]
ROOT = Path(__file__).resolve().parent.parent
SECRETS = Path(os.environ.get("GMAIL_SECRETS_DIR", "~/Development/_secrets/inbox-agent")).expanduser()
NO_BROWSER = False  # --no-browser: print the sign-in link instead of opening a browser


def gmail_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    token_path = SECRETS / "token-seed.json"
    creds = Credentials.from_authorized_user_file(str(token_path), SCOPES) if token_path.exists() else None
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(SECRETS / "credentials.json"), SCOPES)
            creds = flow.run_local_server(port=0, open_browser=not NO_BROWSER)
        token_path.write_text(creds.to_json())
        token_path.chmod(0o600)
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()
    global NO_BROWSER
    NO_BROWSER = args.no_browser
    emails = json.loads((ROOT / "seed" / "emails.json").read_text())[: args.only]
    if args.dry_run:
        for e in emails:
            print(f"would insert: {e['subject']}  ({e['from']})")
        return
    svc = gmail_service()
    # The insert scope can't read the profile, so the inbox address comes from the environment.
    me = os.environ.get("INBOX_ADDRESS", "you@gmail.com")
    now = time.time()
    for i, e in enumerate(emails):
        msg = EmailMessage()
        msg["From"] = e["from"]
        msg["To"] = me
        msg["Subject"] = e["subject"]
        msg["Date"] = formatdate(now - (len(emails) - i) * 300, localtime=True)  # five minutes apart
        msg.set_content(e["body"])
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().insert(
            userId="me", body={"raw": raw, "labelIds": ["INBOX", "UNREAD"]}, internalDateSource="dateHeader"
        ).execute()
        print(f"inserted: {e['subject']}")
    print(f"{len(emails)} emails inserted into {me}")


if __name__ == "__main__":
    main()
