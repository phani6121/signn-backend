"""
Check Session API endpoints
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...schemas.check import (
    CreateSessionRequest,
    UpdateSessionRequest,
    SessionResponse,
    CheckSession
)
from ...services.checksessionservice import check_session_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/check", tags=["check"])


class UpdateConsentRequest(BaseModel):
    check_id: str
    agreed: bool


class UpdateVisionRequest(BaseModel):
    check_id: str
    vision_data: Dict[str, Any]


class UpdateCognitiveRequest(BaseModel):
    check_id: str
    latency: Optional[float] = None
    round_latencies: Optional[list[float]] = None
    score: Optional[float] = None
    passed: Optional[bool] = None


class UpdateBehavioralRequest(BaseModel):
    check_id: str
    answers: list[Dict[str, Any]]


class UpdateResultRequest(BaseModel):
    check_id: str
    overall_status: str
    status_reason: str
    detection_report: Optional[Dict[str, Any]] = None


@router.post("/session/create")
async def create_session(request: CreateSessionRequest):
    """
    Create a new check session for a user
    
    Example:
        POST /api/v1/check/session/create
        {
            "user_id": "testuser1"
        }
    """
    try:
        result = check_session_service.create_session(request.user_id, request.shift_type)
        return result
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/consent")
async def save_consent(request: UpdateConsentRequest):
    """
    Save consent step to session
    
    Example:
        PUT /api/v1/check/session/consent
        {
            "check_id": "check_abc123",
            "agreed": true
        }
    """
    try:
        result = check_session_service.update_session_consent(
            request.check_id,
            request.agreed
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Error saving consent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/vision")
async def save_vision(request: UpdateVisionRequest):
    """
    Save vision analysis results to session
    
    Example:
        PUT /api/v1/check/session/vision
        {
            "check_id": "check_abc123",
            "vision_data": {
                "intoxicationDetected": false,
                "fatigueDetected": true,
                "stressDetected": false,
                "feverDetected": false,
                "mood": "neutral"
            }
        }
    """
    try:
        result = check_session_service.update_session_vision(
            request.check_id,
            request.vision_data
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Error saving vision analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/cognitive")
async def save_cognitive(request: UpdateCognitiveRequest):
    """
    Save cognitive test results to session
    
    Example:
        PUT /api/v1/check/session/cognitive
        {
            "check_id": "check_abc123",
            "latency": 250,
            "score": 85,
            "passed": true
        }
    """
    try:
        cognitive_data = {
            "latency": request.latency,
            "round_latencies": request.round_latencies,
            "score": request.score,
            "passed": request.passed
        }
        result = check_session_service.update_session_cognitive(
            request.check_id,
            cognitive_data
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Error saving cognitive test: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/behavioral")
async def save_behavioral(request: UpdateBehavioralRequest):
    """
    Save behavioral assessment answers to session
    
    Example:
        PUT /api/v1/check/session/behavioral
        {
            "check_id": "check_abc123",
            "answers": [
                {
                    "question_id": "q1",
                    "question": "How are you feeling?",
                    "answer": "Good"
                }
            ]
        }
    """
    try:
        behavioral_data = {
            "answers": request.answers
        }
        result = check_session_service.update_session_behavioral(
            request.check_id,
            behavioral_data
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Error saving behavioral assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/session/result")
async def save_result(request: UpdateResultRequest):
    """
    Save final result and detection to session
    
    Example:
        PUT /api/v1/check/session/result
        {
            "check_id": "check_abc123",
            "overall_status": "GREEN",
            "status_reason": "All clear to proceed",
            "detection_report": {
                "check_id": "check_abc123",
                "overall_status": "green",
                "status_color": "#4CAF50",
                "recommendations": []
            }
        }
    """
    try:
        result = check_session_service.update_session_result(
            request.check_id,
            request.overall_status,
            request.status_reason,
            request.detection_report
        )
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Error saving final result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{check_id}")
async def get_session(check_id: str):
    """
    Retrieve a check session by ID
    
    Example:
        GET /api/v1/check/session/check_abc123
    """
    try:
        session = check_session_service.get_session(check_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "success": True,
            "check_id": check_id,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/sessions")
async def get_user_sessions(user_id: str):
    """
    Get all check sessions for a user
    
    Example:
        GET /api/v1/check/user/testuser1/sessions
    """
    try:
        sessions = check_session_service.get_user_sessions(user_id)
        return {
            "success": True,
            "user_id": user_id,
            "total": len(sessions),
            "sessions": sessions
        }
    except Exception as e:
        logger.error(f"Error retrieving user sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{user_id}/latest")
async def get_latest_session(user_id: str):
    """
    Get the most recent check session for a user
    
    Example:
        GET /api/v1/check/user/testuser1/latest
    """
    try:
        session = check_session_service.get_user_latest_session(user_id)
        if not session:
            raise HTTPException(status_code=404, detail="No sessions found for user")
        return {
            "success": True,
            "user_id": user_id,
            "session": session
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving latest session: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/health-check")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "check-session"}
