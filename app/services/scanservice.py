import logging
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException

from ..core.firebase import firestore_manager
from ..schemas.scan import ScanFrameRequest, ScanStartRequest, ScanStartResponse
from .shiftservice import analysis_status, scans, shifts, utc_now_iso

from .face_engine.run_facescan import run_face_scan
from .rules.fatigue import calculate_fatigue
from .rules.stress import calculate_stress
from .rules.mood import calculate_mood
from .rules.shift_risk import calculate_shift_risk

logger = logging.getLogger(__name__)


def start_scan(payload: ScanStartRequest) -> ScanStartResponse:
    if payload.shift_id not in shifts:
        raise HTTPException(status_code=404, detail="Shift not found")

    scan_id = uuid4().hex
    scans[scan_id] = {
        "shift_id": payload.shift_id,
        "started_at": utc_now_iso(),
        "frames": 0,
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

    # -----------------------------
    # Update scan state
    # -----------------------------
    scans[payload.scan_id]["frames"] += 1
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

    # -----------------------------
    # Build frame (engine_service.py compatible)
    # -----------------------------
    frame_data = payload.frame_data or {}

    frame = {
        "data": {
            "eye_aspect_ratio": frame_data.get("eye_aspect_ratio"),
            "eye_blink_rate": frame_data.get("eye_blink_rate"),
            "blink_variance": frame_data.get("blink_variance"),
            "brow_furrow": frame_data.get("brow_furrow"),
            "lip_tighten": frame_data.get("lip_tighten"),
            "mouth_open": frame_data.get("mouth_open"),
            "head_stability": frame_data.get("head_stability"),
            "head_tilt_variance": frame_data.get("head_tilt_variance"),
            "face_visibility": frame_data.get("face_visibility", 1.0),
            "timestamp_ms": frame_data.get("timestamp_ms"),
        }
    }

    # -----------------------------
    # Store frame
    # -----------------------------
    firestore_manager.create_document(
        "scan_frames",
        f"{payload.scan_id}_{scans[payload.scan_id]['frames']}",
        {
            "scan_id": payload.scan_id,
            "data": frame["data"],
            "created_at": utc_now_iso(),
        },
    )

    # -----------------------------
    # Fetch frames for metrics
    # -----------------------------
    frames_docs = firestore_manager.get_collection(
        "scan_frames",
        filters={"scan_id": payload.scan_id},
    )

    frames = [{"data": doc["data"]} for doc in frames_docs]

    # -----------------------------
    # Metrics + Rules (ENGINE LOGIC)
    # -----------------------------
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
        "scan_metrics shift_id=%s scan_id=%s fatigue=%s stress=%s mood=%s shift_risk=%s eye_blink_rate=%s eye_aspect_ratio=%s face_visibility=%s brow_furrow=%s lip_tighten=%s mouth_open=%s head_stability=%s head_tilt_variance=%s blink_variance=%s",
        shift_id,
        payload.scan_id,
        fatigue,
        stress,
        mood,
        shift_risk,
        metrics.get("eye_blink_rate"),
        metrics.get("eye_aspect_ratio"),
        metrics.get("face_visibility"),
        metrics.get("brow_furrow"),
        metrics.get("lip_tighten"),
        metrics.get("mouth_open"),
        metrics.get("head_stability"),
        metrics.get("head_tilt_variance"),
        metrics.get("blink_variance"),
    )

    shift_update: Dict[str, object] = {
        "mood": mood,
        "shift_risk_level": shift_risk_level,
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

    # -----------------------------
    # Response (NON-BREAKING)
    # -----------------------------
    return {
        "scan_id": payload.scan_id,
        "frames": scans[payload.scan_id]["frames"],
        "received_at": utc_now_iso(),

        # NEW outputs
        "fatigue": fatigue,
        "stress": stress,
        "mood": mood,
        "shift_risk": shift_risk,
    }
