"""Run the agent from the terminal:  python -m inbox_agent.cli [--limit N] [--show]"""
import argparse
import asyncio
import time

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

    def row(subject, d):
        draft = "draft" if d.draft else "     "
        print(f"{(d.label or '?'):<16} {draft}  ${d.cost_usd:.4f}  {subject[:48]}", flush=True)
        for name in d.blocked:
            print(f"{'':16} BLOCKED  {name}", flush=True)

    start = time.monotonic()
    with Session(engine) as session:
        results = asyncio.run(triage_inbox(gmail, session, args.limit, print if args.show else None, row))
    total = sum(d.cost_usd for _, d in results)
    seconds = time.monotonic() - start
    print(f"\n{len(results)} email{'' if len(results) == 1 else 's'} · ${total:.4f} total · {seconds:.0f} s")


if __name__ == "__main__":
    main()
