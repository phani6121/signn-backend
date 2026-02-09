"""
Check Session Schema - Tracks all steps of the shift readiness check
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ConsentData(BaseModel):
    """User consent agreement"""
    agreed: bool
    timestamp: Optional[str] = None
    ip_address: Optional[str] = None


class VisionAnalysisData(BaseModel):
    """Face scan and vision analysis results"""
    intoxicationDetected: Optional[bool] = None
    fatigueDetected: Optional[bool] = None
    stressDetected: Optional[bool] = None
    feverDetected: Optional[bool] = None
    eyewearDetected: Optional[bool] = None
    blinkInstructionFollowed: Optional[bool] = None
    eyeScleraRednessScore: Optional[float] = None
    facialDroopingDetected: Optional[bool] = None
    microNodsDetected: Optional[bool] = None
    pupilReactivityScore: Optional[float] = None
    mood: Optional[str] = None
    timestamp: Optional[str] = None


class CognitiveTestData(BaseModel):
    """Cognitive test results"""
    latency: Optional[float] = None
    score: Optional[float] = None
    passed: Optional[bool] = None
    timestamp: Optional[str] = None


class BehavioralAnswerData(BaseModel):
    """Behavioral assessment answers"""
    question_id: str
    question: str
    answer: str


class BehavioralData(BaseModel):
    """Complete behavioral assessment"""
    answers: list[BehavioralAnswerData]
    timestamp: Optional[str] = None


class CheckSession(BaseModel):
    """Complete check session tracking all steps"""
    check_id: str
    user_id: str
    shift_type: Optional[str] = None
    
    # Step 1: Login
    login_timestamp: Optional[str] = None
    
    # Step 2: Consent
    consent: Optional[ConsentData] = None
    
    # Step 3: Vision Analysis
    vision_analysis: Optional[VisionAnalysisData] = None
    
    # Step 4: Cognitive Test
    cognitive_test: Optional[CognitiveTestData] = None
    
    # Step 5: Behavioral Assessment
    behavioral_assessment: Optional[BehavioralData] = None
    
    # Final Result
    overall_status: Optional[str] = None  # GREEN, YELLOW, RED
    status_reason: Optional[str] = None
    final_result_timestamp: Optional[str] = None
    
    # Detection Results (if applicable)
    detection_report: Optional[Dict[str, Any]] = None
    
    # Metadata
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    session_duration_seconds: Optional[float] = None


class CreateSessionRequest(BaseModel):
    """Request to create a new check session"""
    user_id: str
    shift_type: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    """Request to update a check session"""
    step: str  # "consent", "vision", "cognitive", "behavioral", "result"
    data: Dict[str, Any]


class SessionResponse(BaseModel):
    """Response with check session data"""
    success: bool
    check_id: str
    message: Optional[str] = None
    session: Optional[CheckSession] = None
