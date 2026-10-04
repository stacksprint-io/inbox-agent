import asyncio

import pytest

from inbox_agent.agent import Decision, make_guard


def decide(tool_name):
    d = Decision()
    out = asyncio.run(make_guard(d)({"tool_name": tool_name, "tool_input": {}}, None, None))
    return out, d


@pytest.mark.parametrize("name", ["mcp__inbox__apply_label", "mcp__inbox__create_draft"])
def test_our_two_tools_are_allowed(name):
    out, d = decide(name)
    assert out == {} and d.blocked == []


@pytest.mark.parametrize("name", ["mcp__inbox__send_email", "mcp__gmail__send", "Bash", "WebFetch", "mcp__inbox__forward", "mcp__inbox__trash_message"])
def test_everything_else_is_denied(name):
    out, d = decide(name)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert d.blocked == [name]
