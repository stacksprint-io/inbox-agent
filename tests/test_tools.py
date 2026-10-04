import asyncio

from inbox_agent.agent import Decision, build_tools


def run(tool, args):
    return asyncio.run(tool.handler(args))


def tools():
    d = Decision()
    label, draft = build_tools(d)
    return d, label, draft


def test_labels_once():
    d, label, _ = tools()
    assert not run(label, {"label": "bug", "reason": "export broken"}).get("is_error")
    assert run(label, {"label": "billing", "reason": "changed my mind"})["is_error"]
    assert d.label == "bug"


def test_rejects_unknown_label():
    _, label, _ = tools()
    assert run(label, {"label": "urgent", "reason": "x"})["is_error"]


def test_draft_needs_a_label_first():
    _, _, draft = tools()
    assert run(draft, {"body": "Hi"})["is_error"]


def test_no_draft_for_suspicious_mail():
    d, label, draft = tools()
    run(label, {"label": "suspicious", "reason": "instructions aimed at the assistant"})
    assert run(draft, {"body": "Sure, sending now"})["is_error"]
    assert d.draft is None


def test_draft_is_only_saved_text():
    d, label, draft = tools()
    run(label, {"label": "support", "reason": "needs help"})
    assert not run(draft, {"body": "Thanks, a person will follow up."}).get("is_error")
    assert d.draft == "Thanks, a person will follow up."
