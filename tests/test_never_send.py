"""Layer 3: no code in the app can send. If someone adds a send call, this fails."""
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "inbox_agent"
SEND_CALL = re.compile(r"\.send\s*\(|messages\(\)\.send|drafts\(\)\.send")


def test_no_send_call_anywhere_in_the_app():
    offenders = [
        f"{path.name}:{i}: {line.strip()}"
        for path in APP.rglob("*.py")
        for i, line in enumerate(path.read_text().splitlines(), 1)
        if SEND_CALL.search(line)
    ]
    assert offenders == []


def test_gmail_client_has_no_send_method():
    from inbox_agent.gmail import GmailClient
    assert not [m for m in dir(GmailClient) if "send" in m.lower()]
