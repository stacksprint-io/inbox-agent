"""The dashboard: run the agent, then approve or reject every draft it wrote.

    uvicorn inbox_agent.main:app --reload
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, func, select

from .config import LABELS, SECRETS_DIR
from .db import Draft, Triage, engine, init_db, now, pending_drafts
from .gmail import GmailClient
from .runner import triage_inbox

app = FastAPI(title="Inbox Agent")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
state = {"running": False, "last": None}


def get_session():
    with Session(engine) as session:
        yield session


_gmail: GmailClient | None = None


def get_gmail() -> GmailClient:
    global _gmail
    if _gmail is None:
        _gmail = GmailClient.from_token(SECRETS_DIR)
    return _gmail


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, session: Session = Depends(get_session)):
    queue = pending_drafts(session)
    recent = session.exec(select(Triage).order_by(Triage.created_at.desc()).limit(20)).all()
    stats = {
        "triaged": session.exec(select(func.count()).select_from(Triage)).one(),
        "pending": len(queue),
        "approved": session.exec(select(func.count()).select_from(Draft).where(Draft.status == "approved")).one(),
        "cost": session.exec(select(func.coalesce(func.sum(Triage.cost_usd), 0.0))).one(),
    }
    return templates.TemplateResponse(request, "index.html", {
        "queue": queue, "recent": recent, "stats": stats, "labels": LABELS, "running": state["running"],
    })


@app.get("/status")
def status():
    return JSONResponse({"running": state["running"]})


@app.post("/triage")
def run_triage(background: BackgroundTasks, gmail: GmailClient = Depends(get_gmail)):
    if not state["running"]:
        state["running"] = True
        background.add_task(_run, gmail)
    return RedirectResponse("/", status_code=303)


def _run(gmail: GmailClient) -> None:
    try:
        with Session(engine) as session:
            asyncio.run(triage_inbox(gmail, session))
    finally:
        state["running"] = False


@app.post("/drafts/{draft_id}/approve")
def approve(draft_id: int, body: str = Form(...), session: Session = Depends(get_session),
            gmail: GmailClient = Depends(get_gmail)):
    """The human approves: NOW a Gmail draft is created. Sending stays with the human, in Gmail."""
    draft = _pending(session, draft_id)
    email = gmail.get_message(draft.gmail_id)
    draft.body = body.strip() or draft.body
    draft.gmail_draft_id = gmail.create_draft(email, draft.body)
    draft.status, draft.decided_at = "approved", now()
    session.add(draft)
    session.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/drafts/{draft_id}/reject")
def reject(draft_id: int, session: Session = Depends(get_session)):
    """Rejected drafts never reach Gmail."""
    draft = _pending(session, draft_id)
    draft.status, draft.decided_at = "rejected", now()
    session.add(draft)
    session.commit()
    return RedirectResponse("/", status_code=303)


def _pending(session: Session, draft_id: int) -> Draft:
    draft = session.get(Draft, draft_id)
    if draft is None or draft.status != "pending":
        raise HTTPException(404, "No pending draft with that id")
    return draft
