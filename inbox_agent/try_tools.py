"""Try the agent's two tools by hand, with no model involved.

    python -m inbox_agent.try_tools "Refund please"

Reads one real unread email through our Gmail wrapper, then calls the tools the way the
model would. The tools only write to this email's Decision; nothing here changes Gmail.
"""
import asyncio
import sys

from .agent import Decision, build_tools
from .config import SECRETS_DIR
from .gmail import GmailClient


def find(gmail: GmailClient, subject: str):
    for message_id in gmail.list_unread():
        email = gmail.get_message(message_id)
        if subject.lower() in email.subject.lower():
            return email
    sys.exit(f"No unread email with {subject!r} in the subject.")


async def call(tool, args: dict) -> None:
    result = await tool.handler(args)
    mark = "error" if result.get("is_error") else "ok"
    print(f"{tool.name}({', '.join(f'{k}={v!r}' for k, v in args.items())})")
    print(f"  -> {mark}: {result['content'][0]['text']}\n")


async def main(subject: str) -> None:
    email = find(GmailClient.from_token(SECRETS_DIR), subject)
    print(f"From:    {email.sender}\nSubject: {email.subject}\n\n{email.body.strip()[:240]}\n")

    decision = Decision()
    apply_label, create_draft = build_tools(decision)
    await call(create_draft, {"body": "Thanks, we'll look into it."})
    await call(apply_label, {"label": "refund", "reason": "wants money back"})
    await call(apply_label, {"label": "billing", "reason": "yearly plan by mistake, wants monthly"})
    await call(apply_label, {"label": "support", "reason": "second try"})
    await call(create_draft, {"body": "Thanks for letting us know. A person will follow up today.\n\nThe Support Team"})
    print(f"Decision: label={decision.label!r}, draft saved={decision.draft is not None}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "Refund"))
