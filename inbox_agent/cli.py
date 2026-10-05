"""Run the agent from the terminal:  python -m inbox_agent.cli [--limit N] [--show]"""
import argparse
import asyncio

from sqlmodel import Session

from .config import SECRETS_DIR
from .db import engine, init_db
from .gmail import GmailClient
from .runner import triage_inbox


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--show", action="store_true", help="print each step of the agent loop")
    args = ap.parse_args()
    init_db()
    gmail = GmailClient.from_token(SECRETS_DIR)
    with Session(engine) as session:
        results = asyncio.run(triage_inbox(gmail, session, args.limit, print if args.show else None))
    total = 0.0
    if args.show:
        print()
    for subject, d in results:
        total += d.cost_usd
        draft = "draft" if d.draft else "     "
        print(f"{(d.label or '?'):<16} {draft}  ${d.cost_usd:.4f}  {subject[:48]}")
        for name in d.blocked:
            print(f"{'':16} BLOCKED  {name}")
    print(f"\n{len(results)} email{'' if len(results) == 1 else 's'} · ${total:.4f} total")


if __name__ == "__main__":
    main()
