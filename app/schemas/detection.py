"""
Schemas for health impairment detection and reporting
"""

from pydantic import BaseModel
from typing import Dict, List, Optional
from datetime import datetime


class ImpairmentSignal(BaseModel):
    """Individual impairment detection signal"""
    name: str  # e.g., "Intoxication", "Fatigue", "Stress", "Fever"
    detected: bool
    confidence: float  # 0.0 to 1.0
    status: str  # "ok", "warning", "critical"
    details: Optional[str] = None


class DetectionResult(BaseModel):
    """Complete detection result for a check"""
    user_id: str
    check_id: str
    timestamp: datetime
    mood: Optional[str] = None  # e.g., "Neutral", "Stressed", "Tired"
    
    # Individual impairments
    intoxication: ImpairmentSignal
    fatigue: ImpairmentSignal
    stress: ImpairmentSignal
    fever: ImpairmentSignal
    
    # Overall status
    overall_status: str  # "green", "orange", "red"
    action_required: bool
    action_message: Optional[str] = None


class SaveDetectionRequest(BaseModel):
    """Request to save detection results"""
    user_id: str
    check_id: str
    mood: Optional[str] = None
    impairments: Dict[str, dict]  # {"intoxication": {"detected": bool, "confidence": float}, ...}


class FinalReport(BaseModel):
    """Final report with all detected impairments"""
    user_id: str
    check_id: str
    timestamp: datetime
    mood: Optional[str] = None
    
    # Detection results
    detections: Dict[str, ImpairmentSignal]
    
    # Status
    overall_status: str  # "green", "orange", "red"
    status_color: str  # hex color for UI
    action_required: bool
    action_message: Optional[str] = None
    
    # Recommendations
    recommendations: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "testuser1",
                "check_id": "check_123",
                "timestamp": "2026-02-04T10:30:00",
                "mood": "Neutral",
                "detections": {
                    "intoxication": {
                        "name": "Intoxication",
                        "detected": False,
                        "confidence": 0.95,
                        "status": "ok"
                    },
                    "fatigue": {
                        "name": "Fatigue",
                        "detected": True,
                        "confidence": 0.87,
                        "status": "critical"
                    }
                },
                "overall_status": "red",
                "status_color": "#ff4444",
                "action_required": True,
                "action_message": "Critical issues detected. Please remove eyewear and rescan.",
                "recommendations": [
                    "Take a 15-minute break",
                    "Drink water",
                    "Get fresh air"
                ]
            }
        }
