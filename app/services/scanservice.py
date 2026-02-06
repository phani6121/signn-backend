from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from ..core.firebase import firestore_manager
from ..schemas.scan import ScanFrameRequest, ScanStartRequest, ScanStartResponse
from .shiftservice import analysis_status, scans, shifts, utc_now_iso


def start_scan(payload: ScanStartRequest) -> ScanStartResponse:
    if payload.shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")
    scan_id = uuid4().hex
    scans[scan_id] = {"shift_id": payload.shift_id, "started_at": utc_now_iso(), "frames": 0}
    firestore_manager.create_document(
        "scans",
        scan_id,
        {
            "scan_id": scan_id,
            "session_id": payload.shift_id,
            "started_at": scans[scan_id]["started_at"],
            "frames": 0,
        },
        merge=True,
    )
    return ScanStartResponse(scan_id=scan_id, started_at=scans[scan_id]["started_at"])


def add_scan_frame(payload: ScanFrameRequest) -> Dict[str, object]:
    if payload.scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")
    scans[payload.scan_id]["frames"] = int(scans[payload.scan_id]["frames"]) + 1
    shift_id = scans[payload.scan_id]["shift_id"]
    analysis_status[shift_id] = "processing"
    firestore_manager.create_document(
        "analysis_status",
        shift_id,
        {
            "session_id": shift_id,
            "status": "processing",
            "updated_at": utc_now_iso(),
        },
        merge=True,
    )
    firestore_manager.create_document(
        "scans",
        payload.scan_id,
        {
            "frames": scans[payload.scan_id]["frames"],
            "updated_at": utc_now_iso(),
        },
        merge=True,
    )
    return {
        "scan_id": payload.scan_id,
        "frames": scans[payload.scan_id]["frames"],
        "received_at": utc_now_iso(),
    }
