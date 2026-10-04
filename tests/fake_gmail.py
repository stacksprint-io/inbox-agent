"""A fake Gmail API service. It records calls, and it explodes if anything tries to send."""
from __future__ import annotations

import base64
from email.message import EmailMessage


class _Call:
    def __init__(self, result):
        self._result = result

    def execute(self):
        return self._result() if callable(self._result) else self._result


class FakeService:
    def __init__(self, emails: list[dict] | None = None):
        self.emails = {e["id"]: e for e in (emails or [])}
        self.label_ids: dict[str, str] = {}
        self.applied: list[tuple[str, str]] = []
        self.created_drafts: list[dict] = []

    def users(self):
        return self

    def messages(self):
        return _Messages(self)

    def labels(self):
        return _Labels(self)

    def drafts(self):
        return _Drafts(self)

    def __getattr__(self, name):
        if "send" in name:
            raise AssertionError(f"something tried to call {name}")
        raise AttributeError(name)


class _Messages:
    def __init__(self, svc):
        self.svc = svc

    def list(self, userId, q, maxResults):
        return _Call({"messages": [{"id": i} for i in self.svc.emails]})

    def get(self, userId, id, format):
        e = self.svc.emails[id]
        msg = EmailMessage()
        msg.set_content(e["body"])
        data = base64.urlsafe_b64encode(e["body"].encode()).decode()
        return _Call({
            "id": id, "threadId": e.get("thread_id", "t-" + id),
            "payload": {"mimeType": "text/plain", "body": {"data": data}, "headers": [
                {"name": "From", "value": e["from"]},
                {"name": "Subject", "value": e["subject"]},
                {"name": "Message-ID", "value": f"<{id}@example.com>"},
            ]},
        })

    def modify(self, userId, id, body):
        for label_id in body["addLabelIds"]:
            self.svc.applied.append((id, label_id))
        return _Call({})

    def send(self, *a, **k):
        raise AssertionError("messages().send was called")


class _Labels:
    def __init__(self, svc):
        self.svc = svc

    def list(self, userId):
        return _Call({"labels": [{"name": n, "id": i} for n, i in self.svc.label_ids.items()]})

    def create(self, userId, body):
        label_id = f"L{len(self.svc.label_ids) + 1}"
        self.svc.label_ids[body["name"]] = label_id
        return _Call({"id": label_id, "name": body["name"]})


class _Drafts:
    def __init__(self, svc):
        self.svc = svc

    def create(self, userId, body):
        self.svc.created_drafts.append(body)
        return _Call({"id": f"D{len(self.svc.created_drafts)}"})

    def send(self, *a, **k):
        raise AssertionError("drafts().send was called")
