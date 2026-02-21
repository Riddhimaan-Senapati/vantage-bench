"""
seed.py
-------
Populates the SQLite database with the 24 team members, 6 at-risk tasks,
and their pre-ranked suggestions — matching the mock data used by the
Next.js frontend (coverageiq/lib/mock-data.ts).

Run once:
    python seed.py

Safe to run multiple times: skips seeding if team_members table is not empty.

After seeding, Maya Patel's calendar_pct is automatically computed from
dummy_maya_calendar.ics so one member has a live ICS-derived availability.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlmodel import Session, select

from database import create_db_and_tables, engine
from models import Suggestion, Task, TeamMember, WeekAvailability

NOW = datetime.now(timezone.utc)
THREE_HOURS_AGO = NOW - timedelta(hours=3)

# ── Member seed data ───────────────────────────────────────────────────────────

MEMBERS: list[dict] = [
    {"id": "mem-001", "name": "Alex Chen",       "role": "Senior Backend Engineer",   "team": "Engineering", "confidence_score": 82, "skills": ["Node.js","PostgreSQL","Security","AWS"],         "calendar_pct": 90,  "task_load_hours": 22, "leave_status": "available", "is_ooo": False, "week": (80, 75, 85, 70, 90)},
    {"id": "mem-002", "name": "Lee Park",         "role": "Mobile Engineer",           "team": "Engineering", "confidence_score": 55, "skills": ["React Native","Swift","Kotlin","GraphQL"],       "calendar_pct": 60,  "task_load_hours": 34, "leave_status": "partial",   "is_ooo": False, "week": (60, 40, 55, 65, 50)},
    {"id": "mem-003", "name": "Rohan Mehta",      "role": "Staff Engineer",            "team": "Engineering", "confidence_score": 20, "skills": ["OAuth","Microservices","Go","Kubernetes"],       "calendar_pct": 40,  "task_load_hours": 45, "leave_status": "ooo",       "is_ooo": True,  "week": ( 0,  0,  0, 30, 60)},
    {"id": "mem-004", "name": "Priya Sharma",     "role": "Payments Engineer",         "team": "Engineering", "confidence_score": 74, "skills": ["Stripe","Payments","Python","Django"],           "calendar_pct": 80,  "task_load_hours": 28, "leave_status": "available", "is_ooo": False, "week": (70, 80, 65, 75, 70)},
    {"id": "mem-005", "name": "Marcus Webb",      "role": "DevOps Engineer",           "team": "Engineering", "confidence_score": 91, "skills": ["Kubernetes","Terraform","CI/CD","Monitoring"],   "calendar_pct": 95,  "task_load_hours": 18, "leave_status": "available", "is_ooo": False, "week": (90, 95, 88, 92, 85)},
    {"id": "mem-006", "name": "Isabella Torres",  "role": "Frontend Engineer",         "team": "Engineering", "confidence_score": 15, "skills": ["React","Performance","TypeScript","Webpack"],    "calendar_pct": 30,  "task_load_hours": 50, "leave_status": "ooo",       "is_ooo": True,  "week": ( 0,  0, 10, 40, 70)},
    {"id": "mem-007", "name": "Jordan Kim",       "role": "Backend Engineer",          "team": "Engineering", "confidence_score": 88, "skills": ["OAuth","Node.js","Redis","REST APIs"],           "calendar_pct": 90,  "task_load_hours": 20, "leave_status": "available", "is_ooo": False, "week": (85, 90, 80, 88, 82)},
    {"id": "mem-008", "name": "Evan Liu",         "role": "Product Manager",           "team": "Product",     "confidence_score": 67, "skills": ["OKRs","Roadmapping","Analytics","JIRA"],        "calendar_pct": 70,  "task_load_hours": 30, "leave_status": "available", "is_ooo": False, "week": (65, 70, 60, 68, 72)},
    {"id": "mem-009", "name": "Camille Dubois",   "role": "Senior Backend Engineer",   "team": "Engineering", "confidence_score": 10, "skills": ["Payments","Java","Spring Boot","Kafka"],        "calendar_pct": 20,  "task_load_hours": 55, "leave_status": "ooo",       "is_ooo": True,  "week": ( 0,  0,  0, 20, 50)},
    {"id": "mem-010", "name": "Aisha Okafor",     "role": "UX Researcher",             "team": "Design",      "confidence_score": 95, "skills": ["User Research","Figma","Usability Testing","Surveys"], "calendar_pct": 100, "task_load_hours": 12, "leave_status": "available", "is_ooo": False, "week": (95,100, 90, 95, 88)},
    {"id": "mem-011", "name": "Felix Wagner",     "role": "UI Designer",               "team": "Design",      "confidence_score": 78, "skills": ["Figma","Accessibility","Design Systems","Prototyping"], "calendar_pct": 85, "task_load_hours": 24, "leave_status": "available", "is_ooo": False, "week": (78, 82, 75, 80, 70)},
    {"id": "mem-012", "name": "Maya Patel",       "role": "Senior Frontend Engineer",  "team": "Engineering", "confidence_score": 92, "skills": ["React","TypeScript","Performance","Testing"],    "calendar_pct": 63,  "task_load_hours": 16, "leave_status": "available", "is_ooo": False, "week": (90, 95, 88, 92, 85), "ics_path": "dummy_maya_calendar.ics"},
    {"id": "mem-013", "name": "Morgan Blake",     "role": "QA Engineer",               "team": "Engineering", "confidence_score": 43, "skills": ["Selenium","Cypress","Accessibility Testing","Test Plans"], "calendar_pct": 50, "task_load_hours": 38, "leave_status": "partial", "is_ooo": False, "week": (50, 45, 55, 40, 60)},
    {"id": "mem-014", "name": "Nadia Kowalski",   "role": "Senior PM",                 "team": "Product",     "confidence_score": 88, "skills": ["Metrics","Data Analysis","OKRs","Stakeholder Management"], "calendar_pct": 90, "task_load_hours": 20, "leave_status": "available", "is_ooo": False, "week": (88, 85, 90, 82, 80)},
    {"id": "mem-015", "name": "Sam Rivera",       "role": "Backend Engineer",          "team": "Engineering", "confidence_score": 79, "skills": ["Stripe","Node.js","TypeScript","REST APIs"],    "calendar_pct": 85,  "task_load_hours": 22, "leave_status": "available", "is_ooo": False, "week": (75, 82, 78, 80, 72)},
    {"id": "mem-016", "name": "Sofia Andersen",   "role": "Lead Designer",             "team": "Design",      "confidence_score": 25, "skills": ["Design Systems","Figma","Brand","CSS Tokens"],   "calendar_pct": 35,  "task_load_hours": 48, "leave_status": "ooo",       "is_ooo": True,  "week": ( 0,  0, 20, 50, 75)},
    {"id": "mem-017", "name": "Derek Osei",       "role": "Designer",                  "team": "Design",      "confidence_score": 35, "skills": ["WCAG","Accessibility","UX Writing","Figma"],    "calendar_pct": 45,  "task_load_hours": 40, "leave_status": "partial",   "is_ooo": False, "week": (35, 40, 30, 45, 50)},
    {"id": "mem-018", "name": "Zoe Fernandez",    "role": "UI Designer",               "team": "Design",      "confidence_score": 62, "skills": ["CSS","Design Systems","Figma","Motion Design"],  "calendar_pct": 70,  "task_load_hours": 28, "leave_status": "available", "is_ooo": False, "week": (62, 65, 58, 70, 60)},
    {"id": "mem-019", "name": "Chris Nakamura",   "role": "Site Reliability Engineer", "team": "Engineering", "confidence_score": 85, "skills": ["Incident Response","Monitoring","Go","PagerDuty"], "calendar_pct": 90, "task_load_hours": 18, "leave_status": "available", "is_ooo": False, "week": (82, 88, 85, 80, 90)},
    {"id": "mem-020", "name": "Taylor Morgan",    "role": "Data Analyst",              "team": "Product",     "confidence_score": 58, "skills": ["SQL","Python","Looker","Data Analytics"],       "calendar_pct": 65,  "task_load_hours": 32, "leave_status": "available", "is_ooo": False, "week": (55, 62, 58, 60, 65)},
    {"id": "mem-021", "name": "Dana Ellis",       "role": "Frontend Engineer",         "team": "Engineering", "confidence_score": 73, "skills": ["React","Recharts","D3.js","TypeScript"],         "calendar_pct": 80,  "task_load_hours": 26, "leave_status": "available", "is_ooo": False, "week": (72, 78, 70, 75, 68)},
    {"id": "mem-022", "name": "Lucas Petit",      "role": "Product Manager",           "team": "Product",     "confidence_score": 18, "skills": ["OKRs","Product Strategy","Metrics","Roadmapping"], "calendar_pct": 25, "task_load_hours": 52, "leave_status": "ooo",      "is_ooo": True,  "week": ( 0,  0,  0, 25, 60)},
    {"id": "mem-023", "name": "Aria Johnson",     "role": "Senior Designer",           "team": "Design",      "confidence_score": 96, "skills": ["Figma","Design Tokens","CSS","Component Libraries"], "calendar_pct": 100, "task_load_hours": 10, "leave_status": "available", "is_ooo": False, "week": (96,100, 92, 95, 90)},
    {"id": "mem-024", "name": "Riley Scott",      "role": "Designer",                  "team": "Design",      "confidence_score": 70, "skills": ["WCAG","Accessibility","Figma","User Testing"],   "calendar_pct": 75,  "task_load_hours": 26, "leave_status": "available", "is_ooo": False, "week": (70, 72, 68, 74, 65)},
]

# ── Task + suggestion seed data ────────────────────────────────────────────────

TASKS: list[dict] = [
    {
        "id": "task-001", "title": "Auth service migration to OAuth 2.0",
        "priority": "P0", "assignee_id": "mem-003",
        "deadline": NOW + timedelta(hours=26),
        "project_name": "Platform / Core Auth", "status": "at-risk",
        "suggestions": [
            ("mem-007", 94, 29, "Suggested because Jordan has OAuth & Node.js expertise and is 71% free today"),
            ("mem-012", 81, 45, "Maya built the original auth layer and has 55% capacity available"),
            ("mem-001", 68, 62, "Alex has backend security experience and is partially available this sprint"),
        ],
    },
    {
        "id": "task-002", "title": "Production incident: payment gateway timeout",
        "priority": "P0", "assignee_id": "mem-009",
        "deadline": NOW + timedelta(hours=8),
        "project_name": "Payments / Gateway", "status": "at-risk",
        "suggestions": [
            ("mem-015", 88, 35, "Sam has Stripe API experience and their afternoon is clear"),
            ("mem-004", 76, 50, "Priya worked on the original gateway integration last quarter"),
            ("mem-019", 70, 40, "Chris has incident response experience and is on-call this week"),
        ],
    },
    {
        "id": "task-003", "title": "Dashboard performance regression fix",
        "priority": "P1", "assignee_id": "mem-006",
        "deadline": NOW + timedelta(hours=48),
        "project_name": "Frontend / Analytics", "status": "at-risk",
        "suggestions": [
            ("mem-012", 91, 38, "Maya has React profiling expertise and is 62% available today"),
            ("mem-021", 79, 55, "Dana has worked on Recharts optimization and has 45% bandwidth"),
            ("mem-002", 65, 70, "Lee identified similar regressions on the mobile app last month"),
        ],
    },
    {
        "id": "task-004", "title": "Design system token migration (Q1 deadline)",
        "priority": "P1", "assignee_id": "mem-016",
        "deadline": NOW + timedelta(hours=72),
        "project_name": "Design / System", "status": "at-risk",
        "suggestions": [
            ("mem-023", 96, 22, "Aria owns the Figma token library and has 78% availability this week"),
            ("mem-011", 82, 48, "Felix contributed to the original token spec and is partially free"),
            ("mem-018", 71, 60, "Zoe has CSS variable migration experience from the v2 rebrand"),
        ],
    },
    {
        "id": "task-005", "title": "Q1 OKR report: product metrics compile",
        "priority": "P2", "assignee_id": "mem-022",
        "deadline": NOW + timedelta(days=5),
        "project_name": "Product / Strategy", "status": "at-risk",
        "suggestions": [
            ("mem-014", 85, 30, "Nadia owns the metrics dashboard and can pull this in ~2 hours"),
            ("mem-008", 74, 42, "Evan prepared last quarter's OKR deck and knows the format"),
            ("mem-020", 60, 55, "Taylor has data analytics skills and bandwidth mid-week"),
        ],
    },
    {
        "id": "task-006", "title": "Accessibility audit: WCAG 2.2 compliance",
        "priority": "P2", "assignee_id": "mem-017",
        "deadline": NOW + timedelta(days=7),
        "project_name": "Design / Accessibility", "status": "at-risk",
        "suggestions": [
            ("mem-011", 88, 35, "Felix is a11y-certified and has 65% availability next week"),
            ("mem-024", 77, 50, "Riley completed WCAG 2.1 audit last cycle and knows the tools"),
            ("mem-013", 62, 68, "Morgan has screen-reader testing experience from the mobile project"),
        ],
    },
]


# ── Seeding logic ──────────────────────────────────────────────────────────────

def seed(db: Session) -> None:
    # Guard: skip if already seeded
    existing = db.exec(select(TeamMember)).first()
    if existing:
        print("Database already seeded — skipping.")
        return

    print("Seeding team members...")
    for m in MEMBERS:
        week = m.pop("week")
        ics_path = m.pop("ics_path", None)
        member = TeamMember(
            **m,
            ics_path=ics_path,
            last_synced=THREE_HOURS_AGO,
        )
        db.add(member)
        db.add(WeekAvailability(
            member_id=m["id"],
            monday=week[0], tuesday=week[1], wednesday=week[2],
            thursday=week[3], friday=week[4],
        ))

    print("Seeding tasks and suggestions...")
    for t in TASKS:
        suggestions = t.pop("suggestions")
        db.add(Task(**t))
        for rank, (member_id, skill_pct, workload_pct, reason) in enumerate(suggestions):
            db.add(Suggestion(
                task_id=t["id"],
                member_id=member_id,
                skill_match_pct=skill_pct,
                workload_pct=workload_pct,
                context_reason=reason,
                rank=rank,
            ))

    db.commit()
    print(f"Seeded {len(MEMBERS)} members and {len(TASKS)} tasks.")

    # Run ICS availability for Maya Patel so she has a live calendar_pct
    _sync_maya(db)


def _sync_maya(db: Session) -> None:
    """After seeding, compute Maya Patel's real availability from her ICS file."""
    from calendar_availability import get_availability_report
    from crud import update_member_calendar_pct
    from datetime import date

    ics_path = Path(__file__).parent / "dummy_maya_calendar.ics"
    if not ics_path.exists():
        print("Warning: dummy_maya_calendar.ics not found — skipping ICS sync for Maya.")
        return

    today = date.today()
    report = get_availability_report(
        ics_path=ics_path,
        range_start=today,
        range_end=today + timedelta(weeks=1),
    )
    updated = update_member_calendar_pct(db, "mem-012", report["availability_pct"])
    print(
        f"Maya Patel calendar synced: {report['availability_pct']}% available "
        f"({report['total_available_minutes']}/{report['total_work_minutes']} min) "
        f"→ confidence_score={updated.confidence_score}"
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    create_db_and_tables()
    with Session(engine) as db:
        seed(db)
    print("Done.")
