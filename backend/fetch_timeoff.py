"""
Slack Time-Off Parser
Fetches recent messages from a Slack channel and uses Google Gemini (via pydantic-ai)
to identify and extract time-off requests.

Resolves Slack user IDs → display names for both the sender and any @mentions
in the message body (e.g. coverage people).

Usage:
    python fetch_timeoff.py
    python fetch_timeoff.py --hours 48    # look back 48 hours (default: 24)
    python fetch_timeoff.py --limit 50    # fetch up to 50 messages (default: 100)
"""

import argparse
import re
import sys
import time

# Force UTF-8 output on Windows terminals
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.exceptions import ModelHTTPError
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

import os

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.getenv("SLACK_CHANNEL_ID")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

GEMINI_MODEL = "google-gla:gemini-2.5-flash"

# Free tier: 15 RPM → wait 4s between calls to stay safely under the limit
INTER_CALL_DELAY_SECONDS = 4
MAX_RETRIES = 4

# pydantic-ai's Google provider reads GOOGLE_API_KEY; map GEMINI_API_KEY if needed
if GEMINI_API_KEY and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

# ── Validate env ───────────────────────────────────────────────────────────────
missing = [k for k, v in {
    "SLACK_BOT_TOKEN": SLACK_BOT_TOKEN,
    "SLACK_CHANNEL_ID": SLACK_CHANNEL_ID,
    "GEMINI_API_KEY": GEMINI_API_KEY,
}.items() if not v]

if missing:
    print(f"ERROR: Missing environment variables: {', '.join(missing)}")
    print("  Add them to your .env file.")
    sys.exit(1)

# ── Pydantic output model ──────────────────────────────────────────────────────
class TimeOffDetails(BaseModel):
    """Structured output for a parsed Slack time-off message."""
    is_time_off_request: bool
    """Whether this message is about someone taking time off."""

    person_username: Optional[str] = None
    """Slack display name / username of the person taking time off."""

    start_date: Optional[str] = None
    """Full date when the time off begins, including year (e.g. '2/21/2026')."""

    end_date: Optional[str] = None
    """Full date when they return, including year (e.g. '2/22/2026'). Null if not mentioned."""

    reason: Optional[str] = None
    """Reason for the time off, if mentioned (e.g. 'sick', 'vacation', 'appointment')."""

    coverage_username: Optional[str] = None
    """The name or Slack username of who will handle their work while away.
    Use the resolved @display_name if they were @mentioned, otherwise use the plain name as written.
    Null only if no coverage person is mentioned at all — do not guess."""

    notes: Optional[str] = None
    """Any other relevant details from the message."""


# ── Pydantic AI agent ──────────────────────────────────────────────────────────
agent = Agent(
    GEMINI_MODEL,
    output_type=TimeOffDetails,
    system_prompt=(
        "You are an HR assistant that reads Slack messages and extracts time-off information. "
        "You will be given the message text, the Slack username of the sender, and the exact "
        "date and time the message was sent. "
        "Use the message sent date to resolve any partial or relative dates to full dates "
        "including the correct year (e.g. '2/21' sent in 2026 → '2/21/2026', "
        "'next Monday' sent on 2026-02-21 → '2/23/2026'). "
        "Determine if the message is a time-off request or announcement. "
        "If it is, extract: who is taking time off (use the sender's username unless the message "
        "clearly states someone else), the full start and end dates (with year), the reason if "
        "mentioned, and who will cover their work (use the resolved @mention username if present). "
        "For coverage: if the person was @mentioned, use their resolved display name; "
        "if they were named in plain text, use that name as written. "
        "Only set coverage_username to null if no coverage person is mentioned at all. "
        "If the message is not about time off (e.g. general chat, a question, a system event), "
        "set is_time_off_request to false and leave all other fields null."
    ),
)

# ── User resolution ────────────────────────────────────────────────────────────
_user_cache: dict[str, str] = {}  # user_id → display name

def resolve_user(client: WebClient, user_id: str) -> str:
    """Return the best display name for a Slack user ID, cached."""
    if user_id in _user_cache:
        return _user_cache[user_id]
    try:
        resp = client.users_info(user=user_id)
        profile = resp["user"]["profile"]
        # Prefer display_name, fall back to real_name, then name
        name = (
            profile.get("display_name")
            or profile.get("real_name")
            or resp["user"].get("name")
            or user_id
        )
        _user_cache[user_id] = name
        return name
    except SlackApiError:
        _user_cache[user_id] = user_id  # cache the raw ID on failure
        return user_id


def resolve_mentions(text: str, client: WebClient) -> str:
    """Replace all <@USERID> Slack mention tokens with @display_name."""
    def replacer(match: re.Match) -> str:
        user_id = match.group(1)
        return f"@{resolve_user(client, user_id)}"

    return re.sub(r"<@([A-Z0-9]+)>", replacer, text)


# ── Helpers ────────────────────────────────────────────────────────────────────
def ts_to_datetime(ts: str) -> datetime:
    """Convert a Slack timestamp string to a UTC datetime."""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc)


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def print_result(
    raw_text: str,
    resolved_text: str,
    sender_name: str,
    sent_at: datetime,
    details: TimeOffDetails,
) -> None:
    """Pretty-print the parsed time-off details."""
    print("\n" + "─" * 60)
    print(f"  Sent at   : {format_datetime(sent_at)}")
    print(f"  From      : @{sender_name}")
    print(f"  Message   : {resolved_text[:120]!r}")

    if not details.is_time_off_request:
        print("  Result    : Not a time-off message — skipped.")
        return

    person = (details.person_username or sender_name).lstrip("@")
    coverage = details.coverage_username.lstrip("@") if details.coverage_username else None

    print("  ✦ TIME-OFF DETECTED")
    print(f"  Person    : @{person}")
    print(f"  Off from  : {details.start_date or '(not specified)'}")
    print(f"  Off until : {details.end_date or '(not specified)'}")
    print(f"  Reason    : {details.reason or '(not mentioned)'}")
    print(f"  Coverage  : {'@' + coverage if coverage else '(not mentioned)'}")
    if details.notes:
        print(f"  Notes     : {details.notes}")


# ── Core logic ─────────────────────────────────────────────────────────────────
def fetch_messages(client: WebClient, channel: str, oldest_ts: str, limit: int) -> list[dict]:
    """Fetch messages from a channel newer than oldest_ts."""
    try:
        resp = client.conversations_history(
            channel=channel,
            oldest=oldest_ts,
            limit=limit,
        )
    except SlackApiError as e:
        print(f"ERROR fetching messages: {e.response['error']}")
        sys.exit(1)

    messages = resp.get("messages", [])
    # conversations_history returns newest-first; reverse for chronological order
    return list(reversed(messages))


def _retry_delay_from_error(exc: ModelHTTPError) -> int:
    """Extract the suggested retry delay (seconds) from a Gemini 429 error body."""
    try:
        details = exc.body.get("error", {}).get("details", [])
        for d in details:
            if "RetryInfo" in d.get("@type", ""):
                delay_str = d.get("retryDelay", "60s")
                return int(delay_str.rstrip("s")) + 5  # add 5s buffer
    except Exception:
        pass
    return 65  # safe default if we can't parse it


def parse_message(resolved_text: str, sender_name: str, sent_at: datetime) -> TimeOffDetails:
    """Send a single message to Gemini for parsing, with retry on 429."""
    prompt = (
        f"Sender Slack username : @{sender_name}\n"
        f"Message sent at       : {format_datetime(sent_at)} "
        f"(year: {sent_at.year})\n\n"
        f"Message:\n{resolved_text}"
    )
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = agent.run_sync(prompt)
            return result.output
        except ModelHTTPError as e:
            if e.status_code == 429 and attempt < MAX_RETRIES:
                wait = _retry_delay_from_error(e)
                print(f"  [rate-limited] waiting {wait}s before retry {attempt}/{MAX_RETRIES - 1}...")
                time.sleep(wait)
            else:
                raise


def main(hours_back: int, limit: int) -> None:
    slack = WebClient(token=SLACK_BOT_TOKEN)

    # Verify channel access
    try:
        info = slack.conversations_info(channel=SLACK_CHANNEL_ID)
        channel_name = info["channel"]["name"]
    except SlackApiError as e:
        print(f"ERROR: Cannot access channel — {e.response['error']}")
        sys.exit(1)

    now = datetime.now(tz=timezone.utc)
    oldest_ts = str(now.timestamp() - hours_back * 3600)

    print("Slack Time-Off Parser")
    print("=" * 60)
    print(f"Channel     : #{channel_name} ({SLACK_CHANNEL_ID})")
    print(f"Looking back: {hours_back} hours  |  max messages: {limit}")
    print(f"Model       : {GEMINI_MODEL}")

    messages = fetch_messages(slack, SLACK_CHANNEL_ID, oldest_ts, limit)

    # Filter: skip system subtypes (joins, bot integrations, etc.)
    human_messages = [
        m for m in messages
        if m.get("type") == "message" and not m.get("subtype")
    ]

    print(f"\nFetched {len(messages)} total messages, {len(human_messages)} are user messages.")

    if not human_messages:
        print("No user messages found in the specified time window.")
        return

    found = 0
    for msg in human_messages:
        raw_text = msg.get("text", "").strip()
        if not raw_text:
            continue

        sent_at = ts_to_datetime(msg["ts"])
        sender_id = msg.get("user", "")
        sender_name = resolve_user(slack, sender_id) if sender_id else "unknown"

        # Replace <@USERID> tokens with @display_name before sending to Gemini
        resolved_text = resolve_mentions(raw_text, slack)

        details = parse_message(resolved_text, sender_name, sent_at)
        print_result(raw_text, resolved_text, sender_name, sent_at, details)

        if details.is_time_off_request:
            found += 1

        # Respect free-tier rate limit (15 RPM) between calls
        time.sleep(INTER_CALL_DELAY_SECONDS)

    print(f"\n{'=' * 60}")
    print(f"Done. Found {found} time-off message(s) in {len(human_messages)} user message(s).")


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse Slack messages for time-off requests.")
    parser.add_argument("--hours", type=int, default=24, help="How many hours back to look (default: 24)")
    parser.add_argument("--limit", type=int, default=100, help="Max messages to fetch (default: 100)")
    args = parser.parse_args()

    main(hours_back=args.hours, limit=args.limit)
