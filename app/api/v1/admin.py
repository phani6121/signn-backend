"""
Admin API endpoints
"""

import logging
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


class RecentReadinessItem(BaseModel):
    rider_id: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    check_id: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/readiness/recent", response_model=List[RecentReadinessItem])
async def get_recent_readiness(limit: int = Query(5, ge=5, le=10)):
    """
    Fetch recent readiness checks for the admin dashboard.

    Example:
        GET /api/v1/admin/readiness/recent?limit=10
    """
    try:
        db = get_firestore_client()
        query = (
            db.collection("shift")
            .order_by("updated_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        docs = list(query.stream())

        items: List[RecentReadinessItem] = []
        for doc in docs:
            data = doc.to_dict() or {}
            items.append(
                RecentReadinessItem(
                    rider_id=data.get("user_id"),
                    status=data.get("overall_status"),
                    reason=data.get("status_with_reason") or data.get("status_reason"),
                    check_id=data.get("shift_session_id") or doc.id,
                    updated_at=_to_iso(
                        data.get("updated_at")
                        or data.get("finished_at")
                        or data.get("created_at")
                    ),
                )
            )

        return items
    except Exception as e:
        logger.error(f"Error fetching recent readiness checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class LedgerItem(BaseModel):
    rider_id: Optional[str] = None
    status: Optional[str] = None
    reason: Optional[str] = None
    check_id: Optional[str] = None
    updated_at: Optional[str] = None


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
        query = db.collection("shift")

        if status:
            query = query.where("overall_status", "==", status)
        if rider_id:
            query = query.where("user_id", "==", rider_id)
        if start_date:
            query = query.where("updated_at", ">=", start_date)
        if end_date:
            query = query.where("updated_at", "<=", end_date)

        query = query.order_by("updated_at", direction=firestore.Query.DESCENDING)
        query = query.offset((page - 1) * limit).limit(limit)

        docs = list(query.stream())
        items: List[LedgerItem] = []
        for doc in docs:
            data = doc.to_dict() or {}
            items.append(
                LedgerItem(
                    rider_id=data.get("user_id"),
                    status=data.get("overall_status"),
                    reason=data.get("status_with_reason") or data.get("status_reason"),
                    check_id=data.get("shift_session_id") or doc.id,
                    updated_at=_to_iso(
                        data.get("updated_at")
                        or data.get("finished_at")
                        or data.get("created_at")
                    ),
                )
            )

        return LedgerResponse(page=page, limit=limit, items=items)
    except Exception as e:
        logger.error(f"Error fetching compliance ledger: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class DashboardMetricsResponse(BaseModel):
    total_active_riders: int
    fleet_readiness: Dict[str, int]
    fleet_operational_percentage: int
    fatigue_detections: int
    stress_detections: int
    shift_risk_detections: int


@router.get("/dashboard/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(
    date: Optional[str] = Query(
        default=None, description="YYYY-MM-DD in UTC. Defaults to today."
    ),
    batch_size: int = Query(500, ge=100, le=1000),
    max_batches: int = Query(20, ge=1, le=200),
):
    """
    Dashboard metrics for total active riders and fleet readiness.
    Metrics are based on riders scanned on the specified day (UTC).

    Example:
        GET /api/v1/admin/dashboard/metrics?date=2026-02-09
    """
    try:
        db = get_firestore_client()
        now = datetime.now(timezone.utc)
        if date:
            try:
                day = datetime.fromisoformat(date).date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Expected YYYY-MM-DD.",
                )
        else:
            day = now.date()

        day_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)
        day_start_iso = _to_iso(day_start)
        day_end_iso = _to_iso(day_end)

        latest_by_rider: Dict[str, Tuple[datetime, Dict[str, object]]] = {}

        def _consume_batches(field: str, start_value: object, end_value: object) -> None:
            last_doc = None
            batches = 0
            while True:
                query = db.collection("shift").order_by(
                    field, direction=firestore.Query.DESCENDING
                )
                if FieldFilter is not None:
                    query = query.where(filter=FieldFilter(field, ">=", start_value))
                    query = query.where(filter=FieldFilter(field, "<", end_value))
                else:
                    query = query.where(field, ">=", start_value)
                    query = query.where(field, "<", end_value)
                if last_doc is not None:
                    query = query.start_after(last_doc)
                query = query.limit(batch_size)

                docs = list(query.stream())
                if not docs:
                    break

                for doc in docs:
                    data = doc.to_dict() or {}
                    rider_id = data.get("user_id")
                    if not rider_id:
                        continue
                    ts = (
                        _parse_datetime(data.get("updated_at"))
                        or _parse_datetime(data.get("finished_at"))
                        or _parse_datetime(data.get("created_at"))
                    )
                    if not ts or ts < day_start or ts >= day_end:
                        continue
                    existing = latest_by_rider.get(rider_id)
                    if existing is None or ts > existing[0]:
                        latest_by_rider[rider_id] = (ts, data)

                last_doc = docs[-1]
                batches += 1
                if batches >= max_batches:
                    break

        # Handle mixed Firestore field types (timestamp vs ISO string).
        # Also account for documents that only have created_at/finished_at.
        for field in ("updated_at", "created_at", "finished_at"):
            _consume_batches(field, day_start, day_end)
            _consume_batches(field, day_start_iso, day_end_iso)

        counts = {"green": 0, "yellow": 0, "red": 0}
        for _, data in latest_by_rider.values():
            status = (data.get("overall_status") or "").upper()
            if status == "GREEN":
                counts["green"] += 1
            elif status == "YELLOW":
                counts["yellow"] += 1
            elif status == "RED":
                counts["red"] += 1

        total_active = 0
        try:
            for _ in db.collection("users").stream():
                total_active += 1
        except Exception:
            # Fallback to readiness-based count if users collection isn't available.
            total_active = sum(counts.values())
        fleet_pct = (
            round((counts["green"] / total_active) * 100) if total_active > 0 else 0
        )

        def _collect_detected_riders() -> Tuple[set[str], set[str], set[str]]:
            fatigue_riders: set[str] = set()
            stress_riders: set[str] = set()
            shift_risk_riders: set[str] = set()

            for rider_id, (_, shift_data) in latest_by_rider.items():
                check_id = shift_data.get("shift_session_id") or shift_data.get("check_id")
                if not check_id:
                    continue
                vision_doc = (
                    db.collection("shift")
                    .document(str(check_id))
                    .collection("assessments")
                    .document("vision_analysis")
                    .get()
                )
                if not vision_doc.exists:
                    continue
                data = vision_doc.to_dict() or {}
                if data.get("fatigueDetected") is True:
                    fatigue_riders.add(rider_id)
                if data.get("stressDetected") is True:
                    stress_riders.add(rider_id)
                if data.get("fatigueDetected") is True or data.get("stressDetected") is True:
                    shift_risk_riders.add(rider_id)

            return fatigue_riders, stress_riders, shift_risk_riders

        fatigue_riders, stress_riders, shift_risk_riders = _collect_detected_riders()

        fatigue_count = len(fatigue_riders)
        stress_count = len(stress_riders)
        shift_risk_count = len(shift_risk_riders)

        return DashboardMetricsResponse(
            total_active_riders=total_active,
            fleet_readiness=counts,
            fleet_operational_percentage=fleet_pct,
            fatigue_detections=fatigue_count,
            stress_detections=stress_count,
            shift_risk_detections=shift_risk_count,
        )
    except Exception as e:
        logger.error(f"Error fetching dashboard metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
