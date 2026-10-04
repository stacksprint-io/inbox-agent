from inbox_agent.gmail import GmailClient


def test_reads_an_email(service):
    email = GmailClient(service).get_message("m1")
    assert email.subject == "Export to CSV broke" and "spins" in email.body


def test_labels_under_triage(service):
    GmailClient(service).add_label("m1", "bug")
    assert "Triage/bug" in service.label_ids and service.applied == [("m1", service.label_ids["Triage/bug"])]


def test_draft_is_a_threaded_reply_to_the_sender(service):
    gmail = GmailClient(service)
    email = gmail.get_message("m1")
    draft_id = gmail.create_draft(email, "Thanks, we're on it.")
    sent = service.created_drafts[0]["message"]
    assert draft_id == "D1" and sent["threadId"] == "t-m1"
    import base64
    raw = base64.urlsafe_b64decode(sent["raw"]).decode()
    assert "To: maya.ortiz@example.com" in raw and "Subject: Re: Export to CSV broke" in raw
    assert "In-Reply-To: <m1@example.com>" in raw
