"""
Service for health impairment detection and reporting
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from ..schemas.detection import ImpairmentSignal, DetectionResult, FinalReport

logger = logging.getLogger(__name__)

# In-memory storage for detection results (no database persistence)
_IN_MEMORY_DETECTIONS: Dict[str, Dict] = {}


class DetectionService:
    """Service to handle impairment detection and reporting"""
    
    STATUS_COLORS = {
        "green": "#4CAF50",    # OK - all good
        "orange": "#FF9800",   # WARNING - some issues
        "red": "#FF4444"       # CRITICAL - serious issues
    }
    
    @staticmethod
    def determine_overall_status(impairments: Dict[str, ImpairmentSignal]) -> tuple[str, bool]:
        """
        Determine overall status based on detected impairments.
        
        Returns: (status, action_required)
        - status: "green", "orange", or "red"
        - action_required: boolean
        """
        critical_detected = False
        warning_detected = False
        
        for impairment in impairments.values():
            if impairment.status == "critical":
                critical_detected = True
            elif impairment.status == "warning":
                warning_detected = True
        
        if critical_detected:
            return "red", True
        elif warning_detected:
            return "orange", True
        else:
            return "green", False
    
    @staticmethod
    def get_recommendations(impairments: Dict[str, ImpairmentSignal]) -> List[str]:
        """Generate recommendations based on detected impairments"""
        recommendations = []
        
        if impairments.get("intoxication").detected:
            recommendations.append("Do not drive. Call a taxi or ask for help.")
        
        if impairments.get("fatigue").detected:
            recommendations.extend([
                "Take a 15-minute break immediately",
                "Get fresh air and drink water",
                "Consider rescheduling your trip"
            ])
        
        if impairments.get("stress").detected:
            recommendations.extend([
                "Take deep breaths and relax",
                "Find a quiet place to calm down",
                "Reschedule if possible"
            ])
        
        if impairments.get("fever").detected:
            recommendations.extend([
                "Seek medical attention",
                "Rest and hydrate",
                "Contact your healthcare provider"
            ])
        
        return recommendations if recommendations else ["You are fit to drive. Safe driving!"]
    
    @staticmethod
    def save_detection_result(
        user_id: str,
        check_id: str,
        impairments: Dict[str, dict],
        mood: Optional[str] = None
    ) -> DetectionResult:
        """
        Save detection result in memory (no database persistence).
        
        Args:
            user_id: ID of the user being checked
            check_id: Unique ID for this check
            impairments: Dict of impairment data
            mood: Detected mood/emotional state
            
        Returns:
            DetectionResult object
        """
        try:
            # Parse impairment signals
            impairment_signals = {}
            for imp_name, imp_data in impairments.items():
                detected = imp_data.get("detected", False)
                confidence = imp_data.get("confidence", 0.0)
                
                # Determine status based on detection and confidence
                if not detected:
                    status = "ok"
                elif confidence > 0.8:
                    status = "critical"
                else:
                    status = "warning"
                
                impairment_signals[imp_name] = ImpairmentSignal(
                    name=imp_name.capitalize(),
                    detected=detected,
                    confidence=confidence,
                    status=status,
                    details=imp_data.get("details")
                )
            
            # Determine overall status
            overall_status, action_required = DetectionService.determine_overall_status(impairment_signals)
            
            # Get action message
            action_message = None
            if action_required:
                if overall_status == "red":
                    action_message = "A critical issue was detected: Please remove eyewear and rescan. You cannot proceed with the check."
                elif overall_status == "orange":
                    action_message = "Warning: Some issues detected. Please review and confirm before proceeding."
            
            # Create detection result
            now = datetime.utcnow()
            detection_result = DetectionResult(
                user_id=user_id,
                check_id=check_id,
                timestamp=now,
                mood=mood,
                intoxication=impairment_signals.get("intoxication"),
                fatigue=impairment_signals.get("fatigue"),
                stress=impairment_signals.get("stress"),
                fever=impairment_signals.get("fever"),
                overall_status=overall_status,
                action_required=action_required,
                action_message=action_message
            )
            
            # Save in memory only (no database persistence)
            check_data = {
                'user_id': user_id,
                'check_id': check_id,
                'timestamp': now,
                'mood': mood,
                'impairments': {
                    k: {
                        'name': v.name,
                        'detected': v.detected,
                        'confidence': v.confidence,
                        'status': v.status,
                        'details': v.details
                    }
                    for k, v in impairment_signals.items()
                },
                'overall_status': overall_status,
                'action_required': action_required,
                'action_message': action_message,
                'created_at': now,
                'updated_at': now,
            }
            _IN_MEMORY_DETECTIONS[check_id] = check_data
            logger.info(f"Detection result cached for user {user_id}, check {check_id}")
            
            return detection_result
            
        except Exception as e:
            logger.error(f"Error saving detection result: {e}")
            raise
    
    @staticmethod
    def get_final_report(user_id: str, check_id: str) -> FinalReport:
        """
        Retrieve final report for a check.
        
        Args:
            user_id: ID of the user
            check_id: Unique ID for the check
            
        Returns:
            FinalReport object
        """
        try:
            # Get check data from memory
            check_data = _IN_MEMORY_DETECTIONS.get(check_id)
            
            if not check_data:
                raise ValueError(f"Check not found: {check_id}")
            
            if check_data.get('user_id') != user_id:
                raise ValueError("User not authorized for this check")
            
            # Parse impairments
            impairments_data = check_data.get('impairments', {})
            detections = {}
            
            for imp_name, imp_data in impairments_data.items():
                detections[imp_name] = ImpairmentSignal(
                    name=imp_data.get('name', imp_name),
                    detected=imp_data.get('detected', False),
                    confidence=imp_data.get('confidence', 0.0),
                    status=imp_data.get('status', 'ok'),
                    details=imp_data.get('details')
                )
            
            overall_status = check_data.get('overall_status', 'green')
            
            # Get recommendations
            recommendations = DetectionService.get_recommendations(detections)
            
            # Create final report
            report = FinalReport(
                user_id=user_id,
                check_id=check_id,
                timestamp=check_data.get('timestamp'),
                mood=check_data.get('mood'),
                detections=detections,
                overall_status=overall_status,
                status_color=DetectionService.STATUS_COLORS.get(overall_status, "#999999"),
                action_required=check_data.get('action_required', False),
                action_message=check_data.get('action_message'),
                recommendations=recommendations
            )
            
            logger.info(f"Final report retrieved for check {check_id}")
            return report
            
        except Exception as e:
            logger.error(f"Error retrieving final report: {e}")
            raise
    
    @staticmethod
    def get_user_checks(user_id: str, limit: int = 20) -> List[Dict]:
        """
        Get all checks for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of checks to retrieve
            
        Returns:
            List of check records
        """
        try:
            checks = [c for c in _IN_MEMORY_DETECTIONS.values() if c.get('user_id') == user_id]
            checks = checks[:limit]
            logger.info(f"Retrieved {len(checks)} checks for user {user_id}")
            return checks
        except Exception as e:
            logger.error(f"Error retrieving checks for user {user_id}: {e}")
            raise


# Create singleton instance
detection_service = DetectionService()
