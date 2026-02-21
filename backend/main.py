"""
FastAPI server — Slack Time-Off API

Endpoints:
    GET  /health          → liveness check
    GET  /timeoff         → fetch last 24h, return list of time-off entries
    GET  /timeoff?hours=48 → look back further
    GET  /timeoff?limit=50 → cap messages fetched
    POST /ping            → DM a team member asking them to confirm availability
"""

import os
import sys
from datetime import datetime

# Force UTF-8 on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from slack_parser import TimeOffEntry, fetch_and_parse

load_dotenv()

# ── Env ────────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Dummy Slack user ID used for all availability pings while real user mapping is
# not yet set up. Replace with a real Slack member ID (e.g. U012AB3CD) in .env.
SLACK_PING_USER_ID = os.getenv("SLACK_PING_USER_ID", "")

if GEMINI_API_KEY and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

missing = [k for k, v in {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_CHANNEL_ID": SLACK_CHANNEL_ID,
    "GEMINI_API_KEY": GEMINI_API_KEY,
}.items() if not v]

if missing:
    raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")

# ── Slack client (shared, created once at startup) ─────────────────────────────
slack_client = WebClient(token=SLACK_BOT_TOKEN)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Slack Time-Off API",
    description="Reads a Slack channel and extracts time-off announcements using Gemini.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Routes ─────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get(
    "/timeoff",
    response_model=list[TimeOffEntry],
    summary="Get time-off announcements",
    description=(
        "Fetches recent Slack messages and returns a JSON list of detected "
        "time-off entries. Only messages that Gemini classifies as time-off "
        "requests or announcements are included."
    ),
)
def get_timeoff(
    hours: int = Query(default=24, ge=1, le=720, description="How many hours back to look"),
    limit: int = Query(default=100, ge=1, le=999, description="Max messages to fetch from Slack"),
):
    try:
        entries = fetch_and_parse(
            slack=slack_client,
            channel_id=SLACK_CHANNEL_ID,
            hours_back=hours,
            limit=limit,
        )
    except SlackApiError as e:
        raise HTTPException(status_code=502, detail=f"Slack error: {e.response['error']}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return entries


# ── Availability ping ───────────────────────────────────────────────────────────

class PingRequest(BaseModel):
    member_name: str
    """Display name of the person being asked (e.g. 'Jordan Lee')."""

    task_title: str
    """Title of the task that needs coverage."""

    project_name: str = ""
    """Project the task belongs to."""

    priority: str = "P1"
    """Task priority label: P0, P1, or P2."""

    deadline: str = ""
    """ISO 8601 deadline string (e.g. '2026-02-22T17:00:00Z')."""

    context_reason: str = ""
    """Why this person was suggested (shown in the DM for context)."""


class PingResponse(BaseModel):
    ok: bool
    message_ts: str
    channel: str


@app.post(
    "/ping",
    response_model=PingResponse,
    summary="Send an availability check DM",
    description=(
        "Opens a Slack DM with SLACK_PING_USER_ID (a single dummy user while real "
        "per-member Slack IDs are not yet wired up) and sends a formatted availability "
        "check message for the given task. Called by the 'Check availability' button "
        "in the CoverageIQ frontend."
    ),
)
def post_ping(body: PingRequest):
    if not SLACK_PING_USER_ID:
        raise HTTPException(
            status_code=500,
            detail="SLACK_PING_USER_ID is not set in .env. Add a real Slack member ID (e.g. U012AB3CD).",
        )

    # ── Parse deadline ──────────────────────────────────────────────────────────
    deadline_formatted = "(not specified)"
    is_urgent = False
    if body.deadline:
        try:
            dt = datetime.fromisoformat(body.deadline.replace("Z", "+00:00"))
            hours_left = (dt.timestamp() - datetime.utcnow().timestamp()) / 3600
            is_urgent = hours_left < 48
            deadline_formatted = dt.strftime("%a, %b %-d at %-I:%M %p UTC")
        except ValueError:
            deadline_formatted = body.deadline

    priority_emoji = {"P0": ":red_circle:", "P1": ":large_yellow_circle:", "P2": ":large_green_circle:"}.get(
        body.priority, ":white_circle:"
    )
    first_name = body.member_name.split()[0] if body.member_name else "there"
    header_text = "🚨 Urgent coverage check" if is_urgent else "📋 Coverage check"

    # ── Open DM channel ─────────────────────────────────────────────────────────
    # conversations_open returns a channel ID even if the DM is new.
    # Requires the bot to have: im:write + chat:write scopes.
    try:
        dm = slack_client.conversations_open(users=[SLACK_PING_USER_ID])
    except SlackApiError as e:
        raise HTTPException(status_code=502, detail=f"conversations_open failed: {e.response['error']}")

    dm_channel = dm["channel"]["id"]

    # ── Send message ────────────────────────────────────────────────────────────
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": header_text, "emoji": True},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"Hey {first_name}! Your team lead is checking if you can cover a task"
                    + (" — *this is time-sensitive*" if is_urgent else "") + "."
                ),
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{priority_emoji} *{body.task_title}*\n_{body.project_name}_",
            },
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Deadline*\n{deadline_formatted}" + (" ⚠️" if is_urgent else "")},
                {"type": "mrkdwn", "text": f"*Priority*\n{priority_emoji} {body.priority}"},
            ],
        },
    ]

    if body.context_reason:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Why you were suggested*\n{body.context_reason}"},
        })

    blocks += [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please *reply in this thread* to confirm or decline. Your team lead will finalise coverage once they hear back.",
            },
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": ":robot_face: Sent from *CoverageIQ* · Enterprise Planning"}],
        },
    ]

    fallback = (
        f"Hey {first_name}! Can you cover '{body.task_title}' ({body.priority} · {body.project_name})? "
        f"Deadline: {deadline_formatted}."
    )

    try:
        result = slack_client.chat_postMessage(
            channel=dm_channel,
            text=fallback,
            blocks=blocks,
        )
    except SlackApiError as e:
        raise HTTPException(status_code=502, detail=f"chat_postMessage failed: {e.response['error']}")

    return PingResponse(ok=True, message_ts=result["ts"], channel=dm_channel)
