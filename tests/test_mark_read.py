import os

import pytest

from inbox_agent.config import SECRETS_DIR
from inbox_agent.gmail import GmailClient

pytestmark = pytest.mark.skipif(not os.environ.get("INBOX_LIVE_TEST"), reason="set INBOX_LIVE_TEST=1 to run against the test inbox")


def test_mark_read_drops_unread_on_the_real_inbox():
    gmail = GmailClient.from_token(SECRETS_DIR)
    message_id = gmail.list_unread(1)[0]
    gmail.mark_read(message_id)
    assert message_id not in gmail.list_unread(25)
