from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timezone
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


def _normalize_iso(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    if not isinstance(value, str):
        return None
    if _TZ_RE.search(value):
        return value.replace("Z", "+00:00")
    # Assume UTC if no timezone info is present
    return f"{value}+00:00"


def _parse_iso(value: Optional[object]) -> Optional[datetime]:
    normalized = _normalize_iso(value)
    if not normalized:
        return None
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _session_timestamp(session: Dict[str, Any]) -> Optional[str]:
    return (
        session.get("final_result_timestamp")
        or session.get("finished_at")
        or session.get("updated_at")
        or session.get("created_at")
    )


def _parse_float(value: Optional[object]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _resolve_user_ids(user_id: str, username: Optional[str] = None) -> Set[str]:
    """
    Resolve possible aliases for the same user (document id / username / email).
    This prevents missing checks when sessions were saved with a different identifier.
    """
    aliases: Set[str] = {user_id}
    if isinstance(username, str) and username.strip():
        aliases.add(username.strip())
    db = check_session_service.db

    try:
        user_doc = db.collection("users").document(user_id).get()
        if user_doc.exists:
            data = user_doc.to_dict() or {}
            for key in ("username", "email"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    aliases.add(value.strip())
    except Exception:
        pass

    # If login identifier is username/email, resolve the actual user document id as well.
    for field in ("username", "email"):
        try:
            docs = list(
                db.collection("users")
                .where(field, "==", user_id)
                .limit(1)
                .stream()
            )
            if docs:
                doc = docs[0]
                aliases.add(doc.id)
                data = doc.to_dict() or {}
                for key in ("username", "email"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        aliases.add(value.strip())
        except Exception:
            continue

    return aliases


@router.get("/user/dashboard")
def user_dashboard(user_id: str, username: Optional[str] = None) -> Dict[str, object]:
    """
    User dashboard summary with recent checks.

    Example:
        GET /api/v1/user/dashboard?user_id=testuser1
    """
    resolved_user_ids = _resolve_user_ids(user_id, username)
    sessions_map: Dict[str, Dict[str, Any]] = {}
    for uid in resolved_user_ids:
        for session in check_session_service.get_user_sessions(uid):
            check_id = (
                session.get("shift_session_id")
                or session.get("check_id")
                or f"session_{len(sessions_map)}"
            )
            sessions_map[str(check_id)] = session
    sessions = list(sessions_map.values())
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
        key=lambda s: _parse_iso(_session_timestamp(s)) or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    recent_sessions = sessions_sorted[:3]
    recent_checks: List[Dict[str, Any]] = []
    for session in recent_sessions:
        detection = session.get("detection_report") or {}
        latency_ms = _parse_float(detection.get("latency_ms"))
        if latency_ms is None:
            latency_ms = _parse_float(detection.get("latency"))
        if latency_ms is None:
            latency_ms = _parse_float(session.get("latency_ms"))
        if latency_ms is None:
            latency_ms = _parse_float(session.get("latency"))
        if latency_ms is None:
            latency_ms = _parse_float((session.get("cognitive_test") or {}).get("latency"))
        if latency_ms is None:
            check_id = session.get("shift_session_id") or session.get("check_id")
            if check_id:
                try:
                    cognitive_doc = (
                        check_session_service.db
                        .collection("shift")
                        .document(str(check_id))
                        .collection("assessments")
                        .document("cognitive_test")
                        .get()
                    )
                    if cognitive_doc.exists:
                        cognitive_data = cognitive_doc.to_dict() or {}
                        latency_ms = _parse_float(cognitive_data.get("latency"))
                except Exception:
                    latency_ms = None
        recent_checks.append(
            {
                "check_id": session.get("shift_session_id") or session.get("check_id"),
                "timestamp": _session_timestamp(session),
                "overall_status": session.get("overall_status"),
                "status_reason": session.get("status_reason"),
                "latency_ms": latency_ms,
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
