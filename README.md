# inbox-agent

An AI agent that triages a Gmail inbox: it reads unread mail, labels it, and drafts replies for you to approve. **It never sends.**

Built with the Claude Agent SDK, FastAPI, SQLite and Bootstrap.

## Setup

You need a throwaway Gmail account for testing. Never point an agent you're still building at your real inbox.

### 1. Anthropic API key
Create a key in the [Claude Console](https://console.anthropic.com/) and set it as an environment variable. The Claude Agent SDK reads it. Never commit it.

```bash
export ANTHROPIC_API_KEY=...
```

### 2. Google Cloud
1. Create a project in the [Google Cloud console](https://console.cloud.google.com/).
2. **APIs & Services → Library**: find the **Gmail API** and click **Enable**.
3. **Google Auth platform** (older guides call it the OAuth consent screen):
   - **Branding**: an app name and a support email.
   - **Audience**: user type **External**, publishing status **Testing**. Under **Test users**, add your test account. While testing, only test users can sign in.
   - **Data access** (optional while testing): the app uses one scope, `https://www.googleapis.com/auth/gmail.modify`. Gmail has no draft-only scope, so the never-send rule lives in this code (see `CLAUDE.md`).
   - **Clients → Create client**: application type **Desktop app**. Download its JSON.
4. Save the JSON as `credentials.json` in a secrets folder **outside the repo**. The app reads `GMAIL_SECRETS_DIR` (default `~/Development/_secrets/inbox-agent/`).

### 3. Install
Python 3.12 or newer. The SDK package brings its own Claude Code engine, so there's nothing else to install.

```bash
git clone https://github.com/stacksprint-io/inbox-agent.git
cd inbox-agent
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Sign in once
```bash
python -m inbox_agent.auth
```
A browser opens. Google warns that it hasn't verified the app: that's expected for an app in testing that only you use, so continue and allow access with your test account. The token is saved next to `credentials.json`, readable only by you.

While the app stays in **Testing**, Google expires the sign-in after **7 days**. When it stops working, run the command again.

## Run it

```bash
python -m inbox_agent.try_tools "Refund please"   # call the two tools by hand, no model
python -m inbox_agent.cli --limit 5                # triage unread mail from the terminal
uvicorn inbox_agent.main:app --reload              # the review dashboard
pytest                                             # tests, Gmail is always faked
```
