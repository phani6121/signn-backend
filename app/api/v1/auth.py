from typing import Dict, Any, List, Optional
from datetime import datetime
import re

from fastapi import APIRouter, HTTPException

from ...schemas.auth import LoginRequest, LoginResponse
from ...services.authservice import login
from ...services.shiftservice import scans, shifts, utc_now_iso
from ...services.checksessionservice import check_session_service

router = APIRouter()


@router.post("/auth/login", response_model=LoginResponse)
def login_route(payload: LoginRequest) -> LoginResponse:
    """
    Login endpoint that accepts username or email with password.
    Updates ONLY the specific user's login information in the database.

    Example:
        POST /api/auth/login
        {
            "username": "testuser1",
            "password": "123456"
        }

    Or with email:
        POST /api/auth/login
        {
            "email": "testuser1@example.com",
            "password": "123456"
        }
    """
    try:
        return login(payload)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Login failed. Please try again.")


_TZ_RE = re.compile(r"(Z|[+-]\d{2}:\d{2})$")


def _normalize_iso(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if _TZ_RE.search(value):
        return value.replace("Z", "+00:00")
    # Assume UTC if no timezone info is present
    return f"{value}+00:00"


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    normalized = _normalize_iso(value)
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _session_timestamp(session: Dict[str, Any]) -> Optional[str]:
    return (
        session.get("final_result_timestamp")
        or session.get("finished_at")
        or session.get("updated_at")
        or session.get("created_at")
    )


@router.get("/user/dashboard")
def user_dashboard(user_id: str) -> Dict[str, object]:
    """
    User dashboard summary with recent checks.

    Example:
        GET /api/v1/user/dashboard?user_id=testuser1
    """
    sessions = check_session_service.get_user_sessions(user_id)
    # Only include completed sessions with a final status/timestamp
    completed_sessions = [
        s
        for s in sessions
        if s.get("overall_status")
        or s.get("final_result_timestamp")
        or s.get("finished_at")
    ]
    sessions_sorted = sorted(
        completed_sessions,
        key=lambda s: _parse_iso(_session_timestamp(s)) or datetime.min,
        reverse=True,
    )

    recent_sessions = sessions_sorted[:3]
    recent_checks: List[Dict[str, Any]] = []
    for session in recent_sessions:
        detection = session.get("detection_report") or {}
        recent_checks.append(
            {
                "check_id": session.get("shift_session_id") or session.get("check_id"),
                "timestamp": _session_timestamp(session),
                "overall_status": session.get("overall_status"),
                "status_reason": session.get("status_reason"),
                "latency_ms": detection.get("latency_ms") or detection.get("latency"),
                "session_duration_seconds": session.get("session_duration_seconds"),
            }
        )

    latest = sessions_sorted[0] if sessions_sorted else None
    last_30 = sessions_sorted[:30]
    counts = {"green": 0, "yellow": 0, "red": 0, "total": 0}
    for session in last_30:
        status = (session.get("overall_status") or "").upper()
        if status in ("GREEN", "YELLOW", "RED"):
            counts["total"] += 1
            if status == "GREEN":
                counts["green"] += 1
            elif status == "YELLOW":
                counts["yellow"] += 1
            elif status == "RED":
                counts["red"] += 1
    health_index = (
        round((counts["green"] / counts["total"]) * 100)
        if counts["total"] > 0
        else None
    )
    return {
        "user_id": user_id,
        "readiness_status": (latest or {}).get("overall_status"),
        "status_reason": (latest or {}).get("status_reason"),
        "last_check_at": _session_timestamp(latest) if latest else None,
        "recent_checks": recent_checks,
        "check_counts": counts,
        "health_index": health_index,
        "active_shifts": len([s for s in shifts.values() if s.get("user_id") == user_id]),
        "open_scans": len([s for s in scans.values() if s.get("user_id") == user_id]),
        "last_updated": utc_now_iso(),
    }
