from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from ..core.firebase import firestore_manager
from ..schemas.cognitive import CognitiveStartRequest, CognitiveStartResponse
from ..schemas.evaluation import EvaluationResultResponse
from ..schemas.shift import (
    ShiftCameraRequest,
    ShiftConsentRequest,
    ShiftStartRequest,
    ShiftStartResponse,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


shifts: Dict[str, Dict[str, object]] = {}
scans: Dict[str, Dict[str, object]] = {}
analysis_status: Dict[str, str] = {}
evaluation_results: Dict[str, EvaluationResultResponse] = {}


def start_shift(payload: ShiftStartRequest) -> ShiftStartResponse:
    shift_id = uuid4().hex
    shifts[shift_id] = {
        "user_id": payload.user_id,
        "location": payload.location,
        "consent": False,
        "camera_enabled": False,
        "started_at": utc_now_iso(),
    }
    analysis_status[shift_id] = "pending"
    firestore_manager.create_document(
        "shift",
        shift_id,
        {
            "session_id": shift_id,
            "user_id": payload.user_id,
            "consent": False,
            "camera_enabled": False,
            "started_at": shifts[shift_id]["started_at"],
        },
        merge=True,
    )
    firestore_manager.create_document(
        "analysis_status",
        shift_id,
        {
            "session_id": shift_id,
            "status": "pending",
            "updated_at": utc_now_iso(),
        },
        merge=True,
    )
    return ShiftStartResponse(shift_id=shift_id, started_at=shifts[shift_id]["started_at"])


def set_shift_consent(shift_id: str, payload: ShiftConsentRequest) -> Dict[str, object]:
    if shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    shifts[shift_id]["consent"] = payload.consent
    firestore_manager.create_document(
        "shift",
        shift_id,
        {
            "consent": payload.consent,
            "updated_at": utc_now_iso(),
        },
        merge=True,
    )
    return {"shift_id": shift_id, "consent": payload.consent, "updated_at": utc_now_iso()}


def set_shift_camera(shift_id: str, payload: ShiftCameraRequest) -> Dict[str, object]:
    if shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    shifts[shift_id]["camera_enabled"] = payload.enabled
    firestore_manager.create_document(
        "shift",
        shift_id,
        {
            "camera_enabled": payload.enabled,
            "updated_at": utc_now_iso(),
        },
        merge=True,
    )
    return {"shift_id": shift_id, "camera_enabled": payload.enabled, "updated_at": utc_now_iso()}


def start_cognitive(payload: CognitiveStartRequest) -> CognitiveStartResponse:
    if payload.shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    cognitive_id = uuid4().hex
    started_at = utc_now_iso()
    firestore_manager.create_document(
        "cognitive_sessions",
        cognitive_id,
        {
            "cognitive_id": cognitive_id,
            "session_id": payload.shift_id,
            "started_at": started_at,
        },
        merge=True,
    )
    return CognitiveStartResponse(cognitive_id=cognitive_id, started_at=started_at)
