"""The loop around the agent: plain code picks the emails, the agent decides each one."""
from __future__ import annotations

from sqlmodel import Session

from .agent import Decision, triage
from .db import Draft, Triage, already_triaged
from .gmail import GmailClient


async def triage_inbox(gmail: GmailClient, session: Session, limit: int = 25) -> list[tuple[str, Decision]]:
    results = []
    for message_id in gmail.list_unread(limit):
        if already_triaged(session, message_id):
            continue
        email = gmail.get_message(message_id)
        decision = await triage(email)
        if decision.label:
            gmail.add_label(message_id, decision.label)
        session.add(Triage(
            gmail_id=email.id, thread_id=email.thread_id, sender=email.sender, subject=email.subject,
            label=decision.label or "unlabelled", reason=decision.reason, cost_usd=decision.cost_usd,
        ))
        if decision.draft:
            session.add(Draft(gmail_id=email.id, body=decision.draft))  # pending: nothing in Gmail yet
        session.commit()
        results.append((email.subject, decision))
    return results
