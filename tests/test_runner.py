import asyncio

import inbox_agent.runner as runner
from inbox_agent.agent import Decision
from inbox_agent.db import Draft, Triage
from inbox_agent.gmail import GmailClient


def test_labels_in_gmail_and_queues_drafts_without_touching_gmail_drafts(service, session, monkeypatch):
    async def fake_triage(email):
        if "AI assistant" in email.subject:
            return Decision(label="suspicious", reason="instructions aimed at the assistant")
        return Decision(label="bug", reason="export broken", draft="Thanks, a person will follow up.")

    monkeypatch.setattr(runner, "triage", fake_triage)
    results = asyncio.run(runner.triage_inbox(GmailClient(service), session))
    assert len(results) == 2
    assert session.get(Triage, "m2").label == "suspicious"
    drafts = session.query(Draft).all()
    assert [d.gmail_id for d in drafts] == ["m1"] and drafts[0].status == "pending"
    assert service.created_drafts == []  # nothing reaches Gmail until a human approves
    # a second run skips what's already triaged
    assert asyncio.run(runner.triage_inbox(GmailClient(service), session)) == []
