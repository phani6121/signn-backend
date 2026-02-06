"""
Detection and reporting API endpoints
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Optional

from ...schemas.detection import SaveDetectionRequest, FinalReport, ImpairmentSignal
from ...services.detectionservice import detection_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/detection", tags=["detection"])


class SaveDetectionPayload(BaseModel):
    """Payload for saving detection results"""
    user_id: str
    mood: Optional[str] = None
    intoxication: Dict = {}
    fatigue: Dict = {}
    stress: Dict = {}
    fever: Dict = {}


@router.post("/save")
async def save_detection(payload: SaveDetectionPayload):
    """
    Save health impairment detection results.
    
    Example:
        POST /api/v1/detection/save
        {
            "user_id": "testuser1",
            "mood": "Neutral",
            "intoxication": {"detected": false, "confidence": 0.95},
            "fatigue": {"detected": true, "confidence": 0.87},
            "stress": {"detected": false, "confidence": 0.10},
            "fever": {"detected": false, "confidence": 0.05}
        }
    """
    try:
        # Generate unique check ID
        check_id = f"check_{uuid4().hex[:12]}"
        
        # Prepare impairments data
        impairments = {
            "intoxication": payload.intoxication or {"detected": False, "confidence": 0},
            "fatigue": payload.fatigue or {"detected": False, "confidence": 0},
            "stress": payload.stress or {"detected": False, "confidence": 0},
            "fever": payload.fever or {"detected": False, "confidence": 0},
        }
        
        # Save detection result
        result = detection_service.save_detection_result(
            user_id=payload.user_id,
            check_id=check_id,
            impairments=impairments,
            mood=payload.mood
        )
        
        return {
            "success": True,
            "check_id": check_id,
            "user_id": payload.user_id,
            "overall_status": result.overall_status,
            "action_required": result.action_required,
            "action_message": result.action_message,
            "impairments": {
                "intoxication": {
                    "name": result.intoxication.name,
                    "detected": result.intoxication.detected,
                    "confidence": result.intoxication.confidence,
                    "status": result.intoxication.status
                },
                "fatigue": {
                    "name": result.fatigue.name,
                    "detected": result.fatigue.detected,
                    "confidence": result.fatigue.confidence,
                    "status": result.fatigue.status
                },
                "stress": {
                    "name": result.stress.name,
                    "detected": result.stress.detected,
                    "confidence": result.stress.confidence,
                    "status": result.stress.status
                },
                "fever": {
                    "name": result.fever.name,
                    "detected": result.fever.detected,
                    "confidence": result.fever.confidence,
                    "status": result.fever.status
                }
            }
        }
    except Exception as e:
        logger.error(f"Error saving detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{check_id}")
async def get_report(check_id: str, user_id: str) -> FinalReport:
    """
    Get final report for a check with color-coded status.
    
    Status colors:
    - Green (#4CAF50): All good - No critical issues detected
    - Orange (#FF9800): Warning - Some issues detected but not critical
    - Red (#FF4444): Critical - Serious issues detected, action required
    
    Example:
        GET /api/v1/detection/report/check_abc123?user_id=testuser1
    """
    try:
        report = detection_service.get_final_report(user_id, check_id)
        return report
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error retrieving report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/checks/{user_id}")
async def get_user_checks(user_id: str, limit: int = 20):
    """
    Get all checks for a user.
    
    Example:
        GET /api/v1/detection/checks/testuser1?limit=10
    """
    try:
        checks = detection_service.get_user_checks(user_id, limit)
        
        return {
            "user_id": user_id,
            "total": len(checks),
            "checks": [
                {
                    "check_id": check.get("check_id"),
                    "timestamp": check.get("timestamp"),
                    "overall_status": check.get("overall_status"),
                    "status_color": {
                        "green": "#4CAF50",
                        "orange": "#FF9800",
                        "red": "#FF4444"
                    }.get(check.get("overall_status"), "#999999"),
                    "mood": check.get("mood"),
                    "action_required": check.get("action_required")
                }
                for check in checks
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving checks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health-check")
async def health_check():
    """
    Health check for detection service.
    
    Example:
        POST /api/v1/detection/health-check
    """
    return {
        "status": "healthy",
        "service": "detection",
        "status_colors": {
            "green": "#4CAF50 (OK - No issues)",
            "orange": "#FF9800 (WARNING - Some issues)",
            "red": "#FF4444 (CRITICAL - Action required)"
        }
    }
