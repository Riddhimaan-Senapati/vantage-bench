"""
routers/gmail.py
----------------
FastAPI router for Gmail-based OOO scanning.

Routes:
    POST /gmail/scan  → scan the inbox, update DB, return TimeOffSyncResult
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from crud import apply_timeoff_entries, tick_slack_ooo_status
from database import get_session
from gmail_parser import fetch_and_parse_gmail, is_gmail_configured
from models import TimeOffSyncResult

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post(
    "/scan",
    response_model=TimeOffSyncResult,
    summary="Scan Gmail inbox for OOO emails",
    description=(
        "Queries Gmail for emails matching OOO-related keywords (pre-filtered before "
        "reaching Gemini), classifies each with Gemini AI, and persists any detected "
        "OOO schedules to the database using the same pipeline as the Slack integration. "
        "Future OOOs are stored as pending and activated automatically when their start "
        "date arrives. Requires GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, and "
        "GMAIL_REFRESH_TOKEN in .env — run gmail_oauth_setup.py once to obtain them."
    ),
)
def scan_gmail(
    max_results: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Max emails to retrieve from the Gmail OOO keyword search.",
    ),
    db: Session = Depends(get_session),
) -> TimeOffSyncResult:
    if not is_gmail_configured():
        raise HTTPException(
            status_code=503,
            detail=(
                "Gmail is not configured. Add GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, "
                "and GMAIL_REFRESH_TOKEN to backend/.env. "
                "Run `python gmail_oauth_setup.py` from the backend directory to obtain "
                "your refresh token."
            ),
        )

    try:
        entries = fetch_and_parse_gmail(max_results=max_results)
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Gmail API error: {exc}",
        ) from exc

    # Reuse the same DB update logic as the Slack integration
    result = apply_timeoff_entries(db, entries)

    # Run the OOO scheduler so any entries whose start_date has arrived
    # are immediately activated (is_ooo = True, leave_status = "ooo")
    tick_slack_ooo_status(db)

    return result
