"""What the agent decided, and what the human decided about it."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Field, Session, SQLModel, create_engine, select

from .config import DB_PATH


def now() -> datetime:
    return datetime.now(timezone.utc)


class Triage(SQLModel, table=True):
    gmail_id: str = Field(primary_key=True)
    thread_id: str
    sender: str
    subject: str
    label: str
    reason: str
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=now)


class Draft(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    gmail_id: str = Field(foreign_key="triage.gmail_id")
    body: str
    status: str = "pending"  # pending -> approved | rejected
    gmail_draft_id: str | None = None  # set only when a human approves
    created_at: datetime = Field(default_factory=now)
    decided_at: datetime | None = None


engine = create_engine(f"sqlite:///{DB_PATH}")


def init_db(eng=None) -> None:
    SQLModel.metadata.create_all(eng or engine)


def already_triaged(session: Session, gmail_id: str) -> bool:
    return session.get(Triage, gmail_id) is not None


def pending_drafts(session: Session) -> list[tuple[Draft, Triage]]:
    rows = session.exec(select(Draft, Triage).where(Draft.gmail_id == Triage.gmail_id).where(Draft.status == "pending"))
    return list(rows)
