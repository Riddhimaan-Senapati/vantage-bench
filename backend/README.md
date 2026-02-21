# Slack Time-Off Backend

Reads a Slack channel, detects time-off announcements using Google Gemini, and exposes the results via a FastAPI REST API. Also includes a CLI script for ad-hoc terminal use.

---

## How it works

1. Fetches recent messages from a Slack channel via `conversations.history`
2. Resolves Slack user IDs and `<@mention>` tokens to display names
3. Sends each message (with sender name + timestamp) to `gemini-2.5-flash` via [pydantic-ai](https://ai.pydantic.dev/)
4. Gemini classifies whether the message is a time-off request and extracts structured fields (person, dates, coverage, reason)
5. Returns only the detected time-off entries as a JSON list

---

## Project structure

```
backend/
├── main.py            # FastAPI server — GET /timeoff
├── slack_parser.py    # Shared core logic (Gemini agent, user resolution, parsing)
├── fetch_timeoff.py   # CLI — prints results to the terminal
├── requirements.txt
└── .env               # Credentials (never commit this)
```

---

## Prerequisites

### 1. Slack bot
Your Slack app needs to be created and installed in your workspace with these **bot token scopes**:

| Scope | Why |
|---|---|
| `channels:history` | Read public channel messages |
| `channels:read` | Get channel info |
| `users:read` | Resolve user IDs to display names |

> For **private channels**, also add `groups:history` and `groups:read`.

### 2. Google Gemini API key
Get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey).

---

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create your .env file
cp .env.example .env   # or create it manually
```

Add the following to `.env`:

```env
SLACK_BOT_TOKEN=xoxb-...        # Bot token from Slack app → OAuth & Permissions
SLACK_CHANNEL_ID=C...            # Right-click channel in Slack → View channel details → bottom of About
GEMINI_API_KEY=AIza...           # From Google AI Studio
```

---

## Running the API server

```bash
python -m uvicorn main:app --reload --port 8000
```

The server starts at `http://localhost:8000`.

Interactive API docs: `http://localhost:8000/docs`

---

## API reference

### `GET /health`
Liveness check.

```json
{ "status": "ok" }
```

---

### `GET /timeoff`
Returns a list of detected time-off entries from the Slack channel.

**Query parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `hours` | int | `24` | How many hours back to look (max 720) |
| `limit` | int | `100` | Max messages to fetch from Slack (max 999) |

**Example request:**
```
GET /timeoff?hours=48
```

**Example response:**
```json
[
  {
    "sent_at": "2026-02-21T17:29:40+00:00",
    "sender": "rsenapati",
    "message": "I will be out of office from 2/21 to 2/22. Om Mehta can handle my remaining tasks.",
    "person_username": "rsenapati",
    "start_date": "2/21/2026",
    "end_date": "2/22/2026",
    "reason": "out of office",
    "coverage_username": "Om Mehta",
    "notes": null
  }
]
```

Returns an empty list `[]` if no time-off messages are found in the time window.

---

## CLI usage

For quick terminal output without running the server:

```bash
python fetch_timeoff.py                # last 24 hours
python fetch_timeoff.py --hours 48     # last 48 hours
python fetch_timeoff.py --limit 50     # cap at 50 messages
```

---

## Rate limits

The script uses `gemini-2.5-flash` on the free tier (15 requests/minute). A 4-second delay is inserted between Gemini API calls automatically. If a `429` rate-limit error is returned, the script reads the retry delay from the error body and waits before retrying (up to 4 attempts).

---

## Environment variables

| Variable | Required | Description |
|---|---|---|
| `SLACK_BOT_TOKEN` | Yes | Slack bot token (`xoxb-...`) |
| `SLACK_CHANNEL_ID` | Yes | Slack channel ID (`C...`) |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
