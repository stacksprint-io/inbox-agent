# inbox-agent

An AI agent that triages a Gmail inbox: it reads unread mail, labels each email, and drafts a reply when one is needed, for you to approve. **It never sends.**

Built with the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview) for Python, FastAPI, SQLite and Bootstrap. It's the code from the StackSprint BUILD LAB video *How to Build an AI Agent That Does Real Work*, written to be read, so every file is small and commented.

![The review dashboard: stats, and a drafted reply waiting for Approve or Reject](docs/screenshots/dashboard.png)

- [What you need](#what-you-need)
- [Setup](#setup) (about 20 minutes, once)
- [Run it](#run-it)
- [How it works](#how-it-works)
- [Can an agent send email?](#can-an-agent-send-email)
- [Make it yours](#make-it-yours)
- [Cost](#cost)
- [Troubleshooting](#troubleshooting)
- [Learn more](#learn-more)

## What you need

| | Why | Where |
|---|---|---|
| **Python 3.12+** | the app and the SDK | [python.org/downloads](https://www.python.org/downloads/) (check with `python3 --version`) |
| **An Anthropic API key** | the model behind the agent; usage is billed per token | [Claude Console](https://platform.claude.com/), then [get an API key](https://platform.claude.com/docs/en/get-api-key) |
| **A throwaway Gmail account** | the inbox the agent works on | any new Google account. Never point an agent you're still building at your real inbox. |
| **A Google Cloud project** | lets the app use the Gmail API through OAuth | [Google Cloud console](https://console.cloud.google.com/), free for this |

You do **not** need to install Claude Code separately. The `claude-agent-sdk` package bundles its own Claude Code engine (on most platforms; see [Troubleshooting](#troubleshooting) for the exception).

## Setup

### 1. Get the code and install it

```bash
git clone https://github.com/stacksprint-io/inbox-agent.git
cd inbox-agent
python3.12 -m venv .venv          # or any Python 3.12+
source .venv/bin/activate         # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

This installs the Claude Agent SDK, FastAPI, the Google API client and pytest. Check it worked:

```bash
pytest
```

All tests should pass. They use a fake Gmail, so they need no key and no Google setup yet.

### 2. Set your Anthropic API key

Create a key in the [Claude Console](https://platform.claude.com/) and set it in the shell you'll run the agent from. The SDK reads `ANTHROPIC_API_KEY` from the environment. It does not load `.env` files on its own.

```bash
export ANTHROPIC_API_KEY=...      # Windows PowerShell: $env:ANTHROPIC_API_KEY = "..."
```

Never commit the key. `.env` is already in `.gitignore` if you keep it in one and load it yourself.

### 3. Set up Google Cloud for the Gmail API

Sign in to the [Google Cloud console](https://console.cloud.google.com/) with any Google account (it doesn't have to be the test inbox).

1. **Create a project**: project picker at the top, then **New project**.
2. **Enable the Gmail API**: [enable it here](https://console.cloud.google.com/apis/enableflow;apiid=gmail.googleapis.com), or **APIs & Services → Library**, search **Gmail API**, click **Enable**.
3. **Google Auth platform** (older guides call it the "OAuth consent screen"):
   - [**Branding**](https://console.cloud.google.com/auth/branding): an app name and a support email.
   - [**Audience**](https://console.cloud.google.com/auth/audience): user type **External**, publishing status **Testing**. Under **Test users**, add your throwaway Gmail address. While the app is in testing, only test users can sign in.
   - **Data access** (optional while testing): the app asks for one scope, `https://www.googleapis.com/auth/gmail.modify`.
   - [**Clients**](https://console.cloud.google.com/auth/clients), then **Create client**, application type **Desktop app**. Download its JSON.
4. Save that JSON as `credentials.json` in a secrets folder **outside the repo**. The app looks in `GMAIL_SECRETS_DIR`, which defaults to `~/Development/_secrets/inbox-agent/`:

```bash
mkdir -p ~/Development/_secrets/inbox-agent
mv ~/Downloads/client_secret_*.json ~/Development/_secrets/inbox-agent/credentials.json
```

Google's own walkthrough of the same steps: [Gmail API Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python).

### 4. Sign in once

```bash
python -m inbox_agent.auth            # add --no-browser to get a link instead
```

A browser opens. Sign in with the **test** account. Google warns that it hasn't verified the app: that's expected for an app in testing that only you use, so click **Continue** and allow access. You'll see:

```
Signed in as <your test account>. Token saved outside the repo.
```

The token is saved next to `credentials.json`, readable only by you. While the app stays in **Testing**, Google expires it after **7 days**; run the command again when it stops working.

### 5. (Optional) Put test emails in the inbox

`seed/emails.json` holds 12 realistic support emails: a refund, a bug report, a phishing attempt, an email that tries to give the agent orders, and so on. This copies them into the test inbox as unread mail. Nothing is sent from or to anyone:

```bash
export INBOX_ADDRESS=your-test-account@gmail.com   # the To: line of the test emails
python scripts/seed_inbox.py --dry-run   # list what it would insert
python scripts/seed_inbox.py             # insert all 12
python scripts/seed_inbox.py --pick 10   # insert one, by position
```

The seeder uses a separate, insert-only scope (`gmail.insert`), so it asks you to sign in once more and keeps its own `token-seed.json`. The agent never gets this scope.

## Run it

```bash
python -m inbox_agent.try_tools "Refund please"   # call the agent's two tools by hand, no model
python -m inbox_agent.cli --limit 5               # triage up to 5 unread emails in the terminal
python -m inbox_agent.cli --limit 1 --show        # same, printing every step of the agent loop
python -m inbox_agent.try_guard                   # break two guardrails on purpose, watch the third deny the send
uvicorn inbox_agent.main:app --reload             # the dashboard at http://127.0.0.1:8000
pytest                                            # the tests; Gmail is always faked
```

The CLI prints each email as it's decided: the label, whether it got a draft, and what it cost.

![A real run of python -m inbox_agent.cli on the 12 seeded emails: 12 emails, $0.0762 total, 71 s](docs/screenshots/cli-run.png)

In Gmail, every email now carries its label:

![The test inbox in Gmail after a run, each email with its Triage label](docs/screenshots/gmail-labelled.png)

On the dashboard, **Run triage** does the same, then each draft waits for you: edit it, **Approve** to create it as a Gmail draft, or **Reject**. Approved drafts appear in Gmail's **Drafts** folder. Sending them is up to you, in Gmail.

![An approved draft in Gmail's Drafts folder: the reply is there, and Send is still yours to press](docs/screenshots/gmail-draft.png)

Settings, all optional, read from the environment:

| Variable | Default | |
|---|---|---|
| `ANTHROPIC_API_KEY` | (required) | your API key |
| `GMAIL_SECRETS_DIR` | `~/Development/_secrets/inbox-agent` | where `credentials.json` and the token live |
| `INBOX_MODEL` | `claude-sonnet-5-5` | the Claude model the agent uses |
| `INBOX_DB` | `inbox.db` | the SQLite file for decisions and drafts |

## How it works

An agent is a model running in a loop with tools, a goal and limits. Here the loop gets **one email at a time**, so a mistake stays inside one email.

1. The **runner** reads unread mail through our Gmail wrapper. Reading is the runner's job, not a tool.
2. For each email, the **agent** (one Claude Agent SDK `query`) reads it and calls its two tools:
   - `apply_label(label)`: picks one of the allowed labels.
   - `create_draft(body)`: writes a reply. It's saved locally, not in Gmail.
3. The runner writes the decision back: the label goes on the email in Gmail, and the draft waits on the dashboard.
4. **You** approve or reject each draft. Only an approved draft becomes a Gmail draft.

| File | What it does |
|---|---|
| `inbox_agent/agent.py` | the system prompt, the two tools, the guard hook, the SDK options, `triage()` |
| `inbox_agent/gmail.py` | the only file that talks to Gmail: list, read, label, create a draft. No send. |
| `inbox_agent/runner.py` | reads unread mail, runs the agent on each email, applies the result |
| `inbox_agent/main.py` + `templates/index.html` | the FastAPI dashboard: run, approve, reject |
| `inbox_agent/cli.py` | the same run from the terminal, with the cost of each email |
| `inbox_agent/config.py` | the labels and their meanings, the model, file locations |
| `inbox_agent/db.py` | SQLite tables for decisions and drafts |
| `inbox_agent/auth.py` | the one-time Google sign-in |
| `tests/` | tools, guard, runner, dashboard and the never-send test, all with a fake Gmail |

### The dashboard (frontend)

There's no separate frontend project and no build step. The whole UI is one server-rendered page:

- **`inbox_agent/templates/index.html`**: a Jinja2 template styled with Bootstrap 5 from a CDN. It renders the stat cards, the drafts waiting for review (each in an editable text box with **Approve** and **Reject**), and the recently triaged emails with their label and cost.
- **`inbox_agent/main.py`**: the FastAPI routes behind it. `GET /` queries SQLite and renders the page. `POST /triage` starts a run in the background. `POST /drafts/{id}/approve` creates the Gmail draft from whatever text is in the box, and `POST /drafts/{id}/reject` discards it.
- **JavaScript**: a few lines of plain JS at the bottom of the template. One grows each draft box to fit its text, so you read the whole reply before approving. The other reloads the page every 2.5 seconds while a run is going, so each email appears as it's decided.

Buttons are plain HTML forms that post to those routes, so there's no client-side state to manage. To change the look, edit the `<style>` block at the top of the template.

Email bodies are untrusted input. An email that tells the assistant to do something is just text to triage: the system prompt says to label it `suspicious` and draft nothing.

## Can an agent send email?

**Yes.** Nothing about agents stops one from sending email. If you give an agent a tool that calls Gmail's send endpoint, and the sign-in allows sending, it can send, and it will whenever the model decides that's the next step. This agent can't send because we built it that way, not because the platform prevents it.

That matters more with Gmail than you might expect, because **Gmail has no "drafts only" permission**. Google's [scope list](https://developers.google.com/workspace/gmail/api/auth/scopes) describes `gmail.modify`, the scope this app uses, as "Read, compose, and send emails". `gmail.compose`, the narrowest scope that can create drafts, can send too. So the token this app holds *could* send mail. The rule has to live in the code, and here it's enforced three ways, each catching a different kind of mistake:

1. **The tools.** The agent is never given a send tool. Its two tools only write to one email's decision in our database. (Catches: a wrong or loosened prompt.)
2. **The guard.** A `PreToolUse` hook in `agent.py` allows only those two tool names and denies everything else before it runs. (Catches: someone adding a new tool later.)
3. **The code.** The app never calls `messages().send` or `drafts().send`, and `tests/test_never_send.py` fails if anyone adds one. (Catches: a code change.)

`python -m inbox_agent.try_guard` breaks the first two on purpose: it loosens the prompt and hands the agent a pre-approved `send_email` stub, then asks it to send. The guard denies the call before it runs:

![try_guard: the model calls send_email, the PreToolUse hook denies it, and the send tool is never reached](docs/screenshots/guard-deny.png)

Why go to that trouble? **A sent email can't be undone.** A wrong label costs you a click to fix, and a bad draft costs you an edit, but a sent email has already reached a customer, with whatever the model wrote: a promised refund, a wrong date, a reply to a phishing email. Models are good, not perfect, and they vary from run to run. When this agent was tested on 12 emails, every label was right, but 4 of the 7 drafts claimed "I've passed this along to the team", which the agent can't do. A person reading the drafts caught it before anyone saw it, and one line in the system prompt fixed it.

So the rule of thumb: let an agent do the reversible parts on its own (reading, labelling, drafting) and keep a human on the irreversible step (sending). If you do want an agent that sends, build up to it:

- Start with drafts only, like this repo, and read every draft for a while. Keep a test set with your expected answers and rerun it after every prompt change.
- Give it a send tool only for narrow cases you've measured, such as known recipients or a fixed template, and have that tool check those limits in code, not in the prompt.
- Add a rate limit and a log of everything sent, and keep the guard hook so any tool you didn't intend is still denied.

## Make it yours

The design carries over to any job that's repetitive, needs some judgment, has output a person can check, and where mistakes can be undone: invoices, leads, support tickets, form submissions.

- **Labels**: edit `LABELS` in `config.py`. Each label's one-line meaning goes into the system prompt. `NO_DRAFT` lists the labels that never get a reply.
- **Rules**: edit `SYSTEM_PROMPT` in `agent.py`. When the same mistake shows up in more than one draft, fix the instruction, not each draft, then rerun your test emails.
- **Tools**: tools are plain async functions with the SDK's `@tool` decorator ([custom tools guide](https://code.claude.com/docs/en/agent-sdk/custom-tools)). Add the new tool's name to `ALLOWED_TOOLS` too, or the guard denies it. Keep each tool narrow: it should do one thing and check its own inputs.
- **Source**: to work on something other than Gmail, replace `gmail.py` and the runner's read and write-back steps. The agent and the guard don't change.

## Cost

The SDK reports the cost of each run, and the CLI prints it. On the 12 seeded emails with `claude-sonnet-5-5`, a full run cost about **$0.076** and took about **70 seconds**: roughly **0.6 cents and 6 seconds per email**. That's from two runs on short emails; longer emails and other models cost more or less. See [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing) and the SDK's [cost tracking](https://code.claude.com/docs/en/agent-sdk/cost-tracking) guide. Run small batches first (`--limit 5`).

## Troubleshooting

- **`Not logged in` or `Invalid API key`**: `ANTHROPIC_API_KEY` isn't set in the shell running the agent. Export it there; the SDK doesn't read `.env` files.
- **"Access blocked" or `Error 403: access_denied` when signing in**: the account isn't on the app's **Test users** list. Add it under Google Auth platform, **Audience**.
- **"Google hasn't verified this app"**: expected while the app is in testing. Continue with your test account.
- **It worked last week and now the Gmail calls fail**: the 7-day testing token expired. Run `python -m inbox_agent.auth` again.
- **`credentials.json` not found**: it has to be in `GMAIL_SECRETS_DIR`, not in the repo.
- **The SDK can't find Claude Code**: some platforms (for example Windows on ARM64) get the SDK without a bundled binary. [Install Claude Code](https://code.claude.com/docs/en/setup) and the SDK finds it on your `PATH`.

## Learn more

- [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview) and [quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart)
- [Python SDK reference](https://code.claude.com/docs/en/agent-sdk/python) · [source](https://github.com/anthropics/claude-agent-sdk-python)
- [Custom tools](https://code.claude.com/docs/en/agent-sdk/custom-tools) · [Hooks](https://code.claude.com/docs/en/agent-sdk/hooks) · [Permissions](https://code.claude.com/docs/en/agent-sdk/permissions)
- [Securely deploying AI agents](https://code.claude.com/docs/en/agent-sdk/secure-deployment)
- [Gmail API Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python) · [Gmail API scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) · [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
