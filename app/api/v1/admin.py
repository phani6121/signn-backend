"""
Admin API endpoints
"""

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from firebase_admin import firestore

try:
    from google.cloud.firestore_v1 import FieldFilter
except Exception:  # pragma: no cover - fallback for older clients
    FieldFilter = None

from app.services.firebaseservice import get_firestore_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["admin"])

# Caches
_METRICS_CACHE_TTL_SECONDS = 300
_dashboard_metrics_cache: Dict[str, Tuple[float, "DashboardMetricsResponse"]] = {}

_RECENT_CACHE_TTL_SECONDS = 8
_recent_readiness_cache: Dict[str, Tuple[float, List["RecentReadinessItem"]]] = {}


# -----------------------------
# Helpers
# -----------------------------
def _to_iso(value: Optional[object]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).isoformat()
        return value.isoformat()
    return str(value)


def _parse_datetime(value: Optional[object]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
            dt = datetime.fromisoformat(normalized)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return None


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


def _is_final_status(status: Optional[object]) -> bool:
    s = (status or "")
    if not isinstance(s, str):
        return False
    s = s.upper()
    return s in {"GREEN", "YELLOW", "RED"}


# -----------------------------
# Recent readiness
# -----------------------------
class RecentReadinessItem(BaseModel):
    rider_id: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    check_id: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/readiness/recent", response_model=List[RecentReadinessItem])
async def get_recent_readiness(
    limit: int = Query(default=10, ge=10, le=10),
    range_days: Optional[int] = Query(
        default=None, ge=1, le=365, description="Trailing window in days."
    ),
    all_time: bool = Query(
        default=False, description="If true, fetches checks across all available records."
    ),
):
    """
    Fetch recent readiness checks for the admin dashboard.

    Examples:
        GET /api/v1/admin/readiness/recent?all_time=true
        GET /api/v1/admin/readiness/recent?range_days=7
    """
    try:
        cache_key = f"recent:{limit}:{range_days}:{all_time}"
        cache_hit = _recent_readiness_cache.get(cache_key)
        if cache_hit and (time.time() - cache_hit[0]) < _RECENT_CACHE_TTL_SECONDS:
            return cache_hit[1]

        db = get_firestore_client()
        now = datetime.now(timezone.utc)
        cutoff: Optional[datetime] = None if all_time else (
            now - timedelta(days=range_days) if range_days is not None else None
        )

        # Pull a small candidate set from indexed queries.
        candidate_limit = max(limit * 5, 50)

        candidates: Dict[str, Tuple[datetime, dict]] = {}

        def _consume(field: str, start_value: Optional[object]) -> None:
            query = db.collection("shift").order_by(field, direction=firestore.Query.DESCENDING)
            if start_value is not None:
                if FieldFilter is not None:
                    query = query.where(filter=FieldFilter(field, ">=", start_value))
                else:
                    query = query.where(field, ">=", start_value)

            docs = list(query.limit(candidate_limit).stream())
            for doc in docs:
                data = doc.to_dict() or {}

                overall_status = (data.get("overall_status") or "").upper()
                final_ts = (
                    data.get("final_result_timestamp")
                    or data.get("finished_at")
                    or data.get("updated_at")
                    or data.get("created_at")
                )

                # Only finalized checks
                if overall_status not in {"GREEN", "YELLOW", "RED"}:
                    continue
                ts = _parse_datetime(final_ts)
                if ts is None:
                    continue

                if cutoff is not None and ts < cutoff:
                    continue

                doc_id = str(doc.id)
                existing = candidates.get(doc_id)
                if existing is None or ts > existing[0]:
                    candidates[doc_id] = (ts, data)

        cutoff_iso = _to_iso(cutoff) if cutoff is not None else None
        for field in ("updated_at", "created_at", "finished_at"):
            if cutoff is None:
                _consume(field, None)
            else:
                _consume(field, cutoff)
                if cutoff_iso is not None:
                    _consume(field, cutoff_iso)

        rows: List[Tuple[datetime, RecentReadinessItem]] = []
        for doc_id, (ts, data) in candidates.items():
            overall_status = (data.get("overall_status") or "").upper()
            if overall_status not in {"GREEN", "YELLOW", "RED"}:
                continue

            rows.append(
                (
                    ts,
                    RecentReadinessItem(
                        rider_id=data.get("user_id"),
                        status=overall_status,
                        reason=data.get("status_with_reason") or data.get("status_reason"),
                        check_id=data.get("shift_session_id") or doc_id,
                        updated_at=_to_iso(ts),
                    ),
                )
            )

        rows.sort(key=lambda x: x[0], reverse=True)
        items = [item for _, item in rows[:limit]]
        _recent_readiness_cache[cache_key] = (time.time(), items)
        return items

    except Exception as e:
        logger.error(f"Error fetching recent readiness checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Compliance ledger
# -----------------------------
class LedgerItem(BaseModel):
    rider_id: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    check_id: Optional[str] = None
    updated_at: Optional[str] = None
    latency_ms: Optional[float] = None


class LedgerResponse(BaseModel):
    page: int
    limit: int
    total: Optional[int] = None
    items: List[LedgerItem]


@router.get("/compliance/ledger", response_model=LedgerResponse)
async def get_compliance_ledger(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: Optional[str] = Query(default=None),
    rider_id: Optional[str] = Query(default=None),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
):
    """
    Fetch full compliance ledger with pagination and filters.

    Example:
        GET /api/v1/admin/compliance/ledger?page=1&limit=50&status=GREEN
    """
    try:
        db = get_firestore_client()
        normalized_status = status.upper() if status else None
        start_dt = _parse_datetime(start_date) if start_date else None
        end_dt = _parse_datetime(end_date) if end_date else None

        if start_date and start_dt is None:
            raise HTTPException(status_code=400, detail="Invalid start_date format.")
        if end_date and end_dt is None:
            raise HTTPException(status_code=400, detail="Invalid end_date format.")

        # Avoid composite-index dependency: only order_by, filter in-memory.
        base_query = db.collection("shift").order_by("updated_at", direction=firestore.Query.DESCENDING)

        offset = (page - 1) * limit
        batch_size = min(max(limit * 2, 100), 500)
        max_batches = 40

        last_doc = None
        batches = 0
        matched_seen = 0
        items: List[LedgerItem] = []

        while len(items) < limit and batches < max_batches:
            query = base_query
            if last_doc is not None:
                query = query.start_after(last_doc)

            docs = list(query.limit(batch_size).stream())
            if not docs:
                break

            for doc in docs:
                data = doc.to_dict() or {}

                if rider_id and str(data.get("user_id") or "") != rider_id:
                    continue

                final_ts = (
                    data.get("final_result_timestamp")
                    or data.get("finished_at")
                    or data.get("updated_at")
                    or data.get("created_at")
                )
                ts = _parse_datetime(final_ts)
                if ts is None:
                    continue

                if start_dt and ts < start_dt:
                    continue
                if end_dt and ts > end_dt:
                    continue

                row_status = (data.get("overall_status") or "").upper()
                if row_status not in {"GREEN", "YELLOW", "RED"}:
                    continue
                if normalized_status and row_status != normalized_status:
                    continue

                # If GREEN tab is requested, ensure all 3 checks completed & passed.
                if normalized_status == "GREEN":
                    check_id = data.get("shift_session_id") or doc.id
                    assessments = db.collection("shift").document(str(check_id)).collection("assessments")
                    vision_doc = assessments.document("vision_analysis").get()
                    cognitive_doc = assessments.document("cognitive_test").get()
                    behavioral_doc = assessments.document("behavioral_assessment").get()
                    if not vision_doc.exists or not cognitive_doc.exists or not behavioral_doc.exists:
                        continue
                    cognitive_data = cognitive_doc.to_dict() or {}
                    behavioral_data = behavioral_doc.to_dict() or {}
                    if cognitive_data.get("passed") is not True:
                        continue
                    answers = behavioral_data.get("answers")
                    if not isinstance(answers, list) or len(answers) == 0:
                        continue

                matched_seen += 1
                if matched_seen <= offset:
                    continue

                # latency (best-effort)
                latency_ms = _parse_float(data.get("latency_ms"))
                if latency_ms is None:
                    latency_ms = _parse_float(data.get("latency"))
                if latency_ms is None:
                    latency_ms = _parse_float((data.get("cognitive_test") or {}).get("latency"))

                if latency_ms is None:
                    # Optional extra read if not present inline
                    check_id = data.get("shift_session_id") or doc.id
                    cognitive_doc = (
                        db.collection("shift")
                        .document(str(check_id))
                        .collection("assessments")
                        .document("cognitive_test")
                        .get()
                    )
                    if cognitive_doc.exists:
                        cognitive_data = cognitive_doc.to_dict() or {}
                        latency_ms = _parse_float(cognitive_data.get("latency"))

                items.append(
                    LedgerItem(
                        rider_id=data.get("user_id"),
                        status=row_status,
                        reason=data.get("status_with_reason") or data.get("status_reason"),
                        check_id=data.get("shift_session_id") or doc.id,
                        updated_at=_to_iso(ts),
                        latency_ms=latency_ms,
                    )
                )
                if len(items) >= limit:
                    break

            last_doc = docs[-1]
            batches += 1

        return LedgerResponse(page=page, limit=limit, items=items)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching compliance ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Dashboard metrics
# -----------------------------
class DashboardMetricsResponse(BaseModel):
    total_active_riders: int
    active_riders_change_pct: Optional[float] = None
    shift_ready_count: int
    shift_not_ready_count: int
    fleet_readiness: Dict[str, int]
    fleet_operational_percentage: int
    fatigue_detections: int
    stress_detections: int
    shift_risk_detections: int


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    date: Optional[str] = Query(default=None, description="YYYY-MM-DD in UTC. Defaults to today."),
    range_days: Optional[int] = Query(
        default=None, ge=1, le=365, description="Trailing window in days (e.g. 1, 7, 14, 21)."
    ),
    all_time: bool = Query(default=False, description="If true, computes metrics across all available records."),
    batch_size: int = Query(500, ge=100, le=1000),
    max_batches: int = Query(20, ge=1, le=200),
):
    """
    Dashboard metrics for total active riders and fleet readiness.

    Examples:
        GET /api/v1/admin/dashboard/metrics?date=2026-02-09
        GET /api/v1/admin/dashboard/metrics?range_days=7
        GET /api/v1/admin/dashboard/metrics?all_time=true
    """
    try:
        db = get_firestore_client()
        now = datetime.now(timezone.utc)

        if all_time:
            window_start = datetime(1970, 1, 1, tzinfo=timezone.utc)
            window_end = now + timedelta(seconds=1)
            window_key = "all_time"
        elif range_days is not None:
            window_end = now
            window_start = now - timedelta(days=range_days)
            window_key = f"range_days:{range_days}"
        elif date:
            try:
                day = datetime.fromisoformat(date).date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")
            window_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
            window_end = window_start + timedelta(days=1)
            window_key = f"date:{day.isoformat()}"
        else:
            day = now.date()
            window_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
            window_end = window_start + timedelta(days=1)
            window_key = f"date:{day.isoformat()}"

        cache_key = f"{window_key}:{batch_size}:{max_batches}"
        cache_hit = _dashboard_metrics_cache.get(cache_key)
        if cache_hit and (time.time() - cache_hit[0]) < _METRICS_CACHE_TTL_SECONDS:
            return cache_hit[1]

        window_start_iso = _to_iso(window_start)
        window_end_iso = _to_iso(window_end)

        # 1) Collect candidate shift docs within window (dedupe by doc id)
        checks_by_id: Dict[str, Tuple[datetime, dict]] = {}

        def _consume_batches(field: str, start_value: object, end_value: object) -> None:
            last_doc = None
            batches = 0
            while True:
                query = db.collection("shift").order_by(field, direction=firestore.Query.DESCENDING)
                if FieldFilter is not None:
                    query = query.where(filter=FieldFilter(field, ">=", start_value))
                    query = query.where(filter=FieldFilter(field, "<", end_value))
                else:
                    query = query.where(field, ">=", start_value)
                    query = query.where(field, "<", end_value)

                if last_doc is not None:
                    query = query.start_after(last_doc)

                docs = list(query.limit(batch_size).stream())
                if not docs:
                    break

                for doc in docs:
                    data = doc.to_dict() or {}
                    ts = (
                        _parse_datetime(data.get("updated_at"))
                        or _parse_datetime(data.get("finished_at"))
                        or _parse_datetime(data.get("created_at"))
                    )
                    if not ts or ts < window_start or ts >= window_end:
                        continue

                    doc_id = str(doc.id)
                    existing = checks_by_id.get(doc_id)
                    if existing is None or ts > existing[0]:
                        checks_by_id[doc_id] = (ts, data)

                last_doc = docs[-1]
                batches += 1
                if batches >= max_batches:
                    break

        for field in ("updated_at", "created_at", "finished_at"):
            _consume_batches(field, window_start, window_end)
            _consume_batches(field, window_start_iso, window_end_iso)

        # 2) Latest check per rider (by timestamp)
        latest_by_rider: Dict[str, Tuple[datetime, dict, str]] = {}
        for doc_id, (ts, data) in checks_by_id.items():
            rider_id = data.get("user_id")
            if not rider_id:
                continue
            rider_key = str(rider_id)
            existing = latest_by_rider.get(rider_key)
            if existing is None or ts > existing[0]:
                latest_by_rider[rider_key] = (ts, data, doc_id)

        # 3) Fleet readiness counts (based on latest per rider)
        counts = {"green": 0, "yellow": 0, "red": 0}
        for _, (_, data, _) in latest_by_rider.items():
            status = (data.get("overall_status") or "").upper()
            if status == "GREEN":
                counts["green"] += 1
            elif status == "YELLOW":
                counts["yellow"] += 1
            elif status == "RED":
                counts["red"] += 1

        # Shift Risk = YELLOW
        shift_risk_count = counts["yellow"]
        # Shift Not Ready = RED
        shift_not_ready_count = counts["red"]

        # Shift Ready = GREEN and all three checks complete + cognitive passed + behavioral answers present
        shift_ready_count = 0
        for _, (_, data, doc_id) in latest_by_rider.items():
            status = (data.get("overall_status") or "").upper()
            if status != "GREEN":
                continue

            check_id = data.get("shift_session_id") or data.get("check_id") or doc_id
            assessments = db.collection("shift").document(str(check_id)).collection("assessments")

            vision_doc = assessments.document("vision_analysis").get()
            cognitive_doc = assessments.document("cognitive_test").get()
            behavioral_doc = assessments.document("behavioral_assessment").get()

            if not vision_doc.exists or not cognitive_doc.exists or not behavioral_doc.exists:
                continue

            cognitive_data = cognitive_doc.to_dict() or {}
            behavioral_data = behavioral_doc.to_dict() or {}

            if cognitive_data.get("passed") is not True:
                continue

            answers = behavioral_data.get("answers")
            if not isinstance(answers, list) or len(answers) == 0:
                continue

            shift_ready_count += 1

        # Business rule (same as colleague):
        # Active = shift ready + shift risk
        total_active = shift_ready_count + shift_risk_count

        fleet_total = sum(counts.values())
        fleet_pct = (
            round(((shift_ready_count + shift_risk_count) / fleet_total) * 100)
            if fleet_total > 0
            else 0
        )

        # Active riders change vs yesterday (based on timestamps we already have)
        yesterday_day = (now - timedelta(days=1)).date()
        yesterday_start = datetime.combine(yesterday_day, datetime.min.time(), tzinfo=timezone.utc)
        yesterday_end = yesterday_start + timedelta(days=1)

        yesterday_riders: set[str] = set()
        for rider_id, (ts, _, _) in latest_by_rider.items():
            if yesterday_start <= ts < yesterday_end:
                yesterday_riders.add(rider_id)

        previous_active_for_change = len(yesterday_riders)
        current_active_for_change = total_active

        if previous_active_for_change > 0:
            active_riders_change_pct: Optional[float] = round(
                ((current_active_for_change - previous_active_for_change) / previous_active_for_change) * 100,
                1,
            )
        else:
            active_riders_change_pct = 100.0 if current_active_for_change > 0 else 0.0

        # Detection counts: unique riders detected in latest check window
        fatigue_riders: set[str] = set()
        stress_riders: set[str] = set()

        for rider_id, (_, shift_data, doc_id) in latest_by_rider.items():
            check_id = (
                shift_data.get("shift_session_id")
                or shift_data.get("check_id")
                or doc_id
            )
            assessments = db.collection("shift").document(str(check_id)).collection("assessments")
            vision_doc = assessments.document("vision_analysis").get()
            if not vision_doc.exists:
                continue

            vision_data = vision_doc.to_dict() or {}
            if vision_data.get("fatigueDetected") is True:
                fatigue_riders.add(rider_id)
            if vision_data.get("stressDetected") is True:
                stress_riders.add(rider_id)

        fatigue_count = len(fatigue_riders)
        stress_count = len(stress_riders)

        response = DashboardMetricsResponse(
            total_active_riders=total_active,
            active_riders_change_pct=active_riders_change_pct,
            shift_ready_count=shift_ready_count,
            shift_not_ready_count=shift_not_ready_count,
            fleet_readiness=counts,
            fleet_operational_percentage=fleet_pct,
            fatigue_detections=fatigue_count,
            stress_detections=stress_count,
            shift_risk_detections=shift_risk_count,
        )

        _dashboard_metrics_cache[cache_key] = (time.time(), response)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
