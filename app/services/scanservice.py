import logging
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from ..core.firebase import firestore_manager
from ..schemas.scan import ScanCompleteRequest, ScanFrameRequest, ScanStartRequest, ScanStartResponse
from .shiftservice import analysis_status, scans, shifts, utc_now_iso

from .face_engine.run_facescan import run_face_scan
from .rules.fatigue import calculate_fatigue
from .rules.stress import calculate_stress
from .rules.mood import calculate_mood
from .rules.shift_risk import calculate_shift_risk

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = True


def start_scan(payload: ScanStartRequest) -> ScanStartResponse:
    if payload.shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")

    scan_id = uuid4().hex
    scans[scan_id] = {
        "shift_id": payload.shift_id,
        "started_at": utc_now_iso(),
        "frames": 0,
        "frames_data": [],
    }

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

    return ScanStartResponse(
        scan_id=scan_id,
        started_at=scans[scan_id]["started_at"],
    )


def add_scan_frame(payload: ScanFrameRequest) -> Dict[str, object]:
    if payload.scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")

    frame_data = payload.frame_data or {}

    # -----------------------------
    # Update scan state (in-memory only)
    # -----------------------------
    scans[payload.scan_id]["frames"] += 1
    scans[payload.scan_id]["frames_data"].append(frame_data)

    # -----------------------------
    # Response (NON-BREAKING)
    # -----------------------------
    return {
        "scan_id": payload.scan_id,
        "frames": scans[payload.scan_id]["frames"],
        "received_at": utc_now_iso(),
    }


def complete_scan(payload: ScanCompleteRequest) -> Dict[str, object]:
    if payload.scan_id not in scans:
        raise HTTPException(status_code=404, detail="Scan not found")

    shift_id = scans[payload.scan_id]["shift_id"]
    frames_data = scans[payload.scan_id].get("frames_data", [])
    frames = [{"data": frame} for frame in frames_data]

    metrics = run_face_scan(frames)
    fatigue = calculate_fatigue(metrics)
    stress = calculate_stress(metrics)
    mood = calculate_mood(metrics)

    shift_risk = calculate_shift_risk(
        stress_detected=(stress == "detected"),
        mood=mood,
        fatigue_score=metrics.get("eye_blink_rate", 0),
        eye_aspect_ratio=metrics.get("eye_aspect_ratio", 0),
    )
    shift_risk_level = shift_risk.get("shift_risk") if isinstance(shift_risk, dict) else None

    logger.info(
        "scan_summary\n"
        "  shift_id=%s\n"
        "  scan_id=%s\n"
        "  metrics:\n"
        "    eye_blink_rate=%s\n"
        "    eye_aspect_ratio=%s\n"
        "    face_visibility=%s\n"
        "    brow_furrow=%s\n"
        "    lip_tighten=%s\n"
        "    mouth_open=%s\n"
        "    head_stability=%s\n"
        "    head_tilt_variance=%s\n"
        "    blink_variance=%s\n"
        "    eye_closed_run_sec=%s\n"
        "    eye_closed_total_sec=%s\n"
        "  rules:\n"
        "    fatigue=%s\n"
        "    stress=%s\n"
        "    mood=%s\n"
        "    shift_risk=%s",
        shift_id,
        payload.scan_id,
        metrics.get("eye_blink_rate"),
        metrics.get("eye_aspect_ratio"),
        metrics.get("face_visibility"),
        metrics.get("brow_furrow"),
        metrics.get("lip_tighten"),
        metrics.get("mouth_open"),
        metrics.get("head_stability"),
        metrics.get("head_tilt_variance"),
        metrics.get("blink_variance"),
        metrics.get("eye_closed_run_sec"),
        metrics.get("eye_closed_total_sec"),
        fatigue,
        stress,
        mood,
        shift_risk,
    )

    shift_update: Dict[str, object] = {
        "mood": mood,
        "shift_risk_level": shift_risk_level,
        "scan_id": payload.scan_id,
        "scan_frames": scans[payload.scan_id]["frames"],
        "scan_completed_at": utc_now_iso(),
    }
    if fatigue == "detected":
        shift_update["fatigue_detected"] = True
    if stress == "detected":
        shift_update["stress_detected"] = True
    if shift_risk_level == "HIGH":
        shift_update["shift_risk_high_detected"] = True

    firestore_manager.create_document(
        "shift",
        shift_id,
        shift_update,
        merge=True,
    )
    firestore_manager.create_document(
        "scans",
        payload.scan_id,
        {
            "scan_id": payload.scan_id,
            "session_id": shift_id,
            "frames": scans[payload.scan_id]["frames"],
            "metrics": metrics,
            "fatigue": fatigue,
            "stress": stress,
            "mood": mood,
            "shift_risk": shift_risk,
            "completed_at": utc_now_iso(),
        },
        merge=True,
    )

    analysis_status[shift_id] = "complete"
    firestore_manager.create_document(
        "analysis_status",
        shift_id,
        {
            "session_id": shift_id,
            "status": "complete",
            "updated_at": utc_now_iso(),
        },
        merge=True,
    )

    scans[payload.scan_id]["frames_data"] = []

    return {
        "scan_id": payload.scan_id,
        "shift_id": shift_id,
        "frames": scans[payload.scan_id]["frames"],
        "fatigue": fatigue,
        "stress": stress,
        "mood": mood,
        "shift_risk": shift_risk,
    }
