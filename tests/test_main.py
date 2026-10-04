import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

import inbox_agent.main as main
from inbox_agent.db import Draft, Triage
from inbox_agent.gmail import GmailClient


@pytest.fixture
def client(service):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(Triage(gmail_id="m1", thread_id="t-m1", sender="Maya <maya.ortiz@example.com>",
                     subject="Export to CSV broke", label="bug", reason="export broken", cost_usd=0.009))
        s.add(Draft(gmail_id="m1", body="Thanks Maya, a person will follow up."))
        s.commit()

    def session_override():
        with Session(engine) as s:
            yield s

    main.app.dependency_overrides[main.get_session] = session_override
    main.app.dependency_overrides[main.get_gmail] = lambda: GmailClient(service)
    with TestClient(main.app) as c:
        c.engine = engine
        yield c
    main.app.dependency_overrides.clear()


def test_dashboard_shows_the_queue(client):
    page = client.get("/").text
    assert "Export to CSV broke" in page and "Thanks Maya" in page and "It never sends." in page


def test_approve_creates_the_gmail_draft_and_nothing_else(client, service):
    r = client.post("/drafts/1/approve", data={"body": "Thanks Maya, edited."}, follow_redirects=False)
    assert r.status_code == 303
    assert len(service.created_drafts) == 1
    with Session(client.engine) as s:
        d = s.get(Draft, 1)
        assert d.status == "approved" and d.gmail_draft_id == "D1" and d.body == "Thanks Maya, edited."


def test_reject_never_touches_gmail(client, service):
    client.post("/drafts/1/reject", follow_redirects=False)
    assert service.created_drafts == []
    with Session(client.engine) as s:
        assert s.get(Draft, 1).status == "rejected"


def test_a_decided_draft_cannot_be_decided_again(client):
    client.post("/drafts/1/reject", follow_redirects=False)
    assert client.post("/drafts/1/approve", data={"body": "x"}, follow_redirects=False).status_code == 404
