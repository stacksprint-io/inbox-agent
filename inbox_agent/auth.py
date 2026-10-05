"""Sign in to Gmail once. Saves token.json next to credentials.json, outside the repo.

    python -m inbox_agent.auth              # opens the Google sign-in page
    python -m inbox_agent.auth --no-browser # prints the link instead

Sign in with your TEST account, never your real inbox.
"""
import sys

from .config import SECRETS_DIR
from .gmail import SCOPES


def main(open_browser: bool = True) -> None:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    client, token = SECRETS_DIR / "credentials.json", SECRETS_DIR / "token.json"
    if not client.exists():
        sys.exit(f"No OAuth client at {client}. Download it from Google Auth platform > Clients.")

    creds = Credentials.from_authorized_user_file(str(token), SCOPES) if token.exists() else None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None  # testing-mode sign-ins expire after 7 days: sign in again
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=open_browser)
    token.write_text(creds.to_json())
    token.chmod(0o600)

    profile = build("gmail", "v1", credentials=creds, cache_discovery=False).users().getProfile(userId="me").execute()
    print(f"Signed in as {profile['emailAddress']}. Token saved outside the repo.")


if __name__ == "__main__":
    main(open_browser="--no-browser" not in sys.argv)
