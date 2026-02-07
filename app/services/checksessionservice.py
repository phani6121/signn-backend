"""
Check Session Service - Manages check session lifecycle and data persistence
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import uuid4

from ..services.firebaseservice import get_firestore_client

logger = logging.getLogger(__name__)


class CheckSessionService:
    """Service for managing check sessions"""
    
    def __init__(self):
        self.db = get_firestore_client()
        self.collection = "shift"

    def _get_or_create_assessment_id(self, check_id: str, doc_name: str, prefix: str) -> str:
        doc_ref = self.db.collection(self.collection).document(check_id).collection("assessments").document(doc_name)
        doc = doc_ref.get()
        if doc.exists:
            existing = doc.to_dict() or {}
            session_id = existing.get("session_id")
            if session_id:
                return session_id
        return f"{prefix}_{uuid4().hex[:8]}"
    
    def create_session(self, user_id: str) -> Dict[str, Any]:
        """
        Create a new check session for a user
        
        Args:
            user_id: The user starting the check
            
        Returns:
            Dictionary with check_id and session data
        """
        try:
            # Reuse latest open shift session for this user if it exists
            try:
                query = (
                    self.db.collection(self.collection)
                    .where("user_id", "==", user_id)
                    .order_by("created_at", direction="DESCENDING")
                    .limit(1)
                )
                docs = list(query.stream())
                if docs:
                    existing_data = docs[0].to_dict() or {}
                    if not existing_data.get("finished_at"):
                        check_id = docs[0].id
                        logger.info(f"Reusing open shift session {check_id} for user {user_id}")
                        return {
                            "success": True,
                            "check_id": check_id,
                            "message": "Existing shift session reused"
                        }
            except Exception:
                # If query fails, fall back to creating a new session
                pass

            check_id = f"check_{uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            
            session_data = {
                "shift_session_id": check_id,
                "user_id": user_id,
                "consent": False,
                "camera_enabled": False,
                "started_at": now,
                "created_at": now,
                "updated_at": now,
            }
            
            self.db.collection(self.collection).document(check_id).set(session_data)
            logger.info(f"Created check session {check_id} for user {user_id}")
            
            return {
                "success": True,
                "check_id": check_id,
                "message": "Check session created"
            }
        except Exception as e:
            logger.error(f"Error creating check session: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def update_session_consent(self, check_id: str, consent_agreed: bool) -> Dict[str, Any]:
        """Save consent step to session"""
        try:
            now = datetime.now(timezone.utc).isoformat()
            
            self.db.collection(self.collection).document(check_id).update({
                "shift_session_id": check_id,
                "consent": consent_agreed,
                "consent_updated_at": now,
                "updated_at": now
            })
            
            logger.info(f"Updated consent for session {check_id}")
            return {"success": True, "message": "Consent saved"}
        except Exception as e:
            logger.error(f"Error updating consent: {e}")
            return {"success": False, "error": str(e)}
    
    def update_session_vision(self, check_id: str, vision_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save vision analysis results to session"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            vision_data["timestamp"] = now
            session = self.get_session(check_id) or {}
            assessment_id = self._get_or_create_assessment_id(check_id, "vision_analysis", "vision")

            self.db.collection(self.collection).document(check_id).update({
                "shift_session_id": check_id,
                "user_id": session.get("user_id"),
                "updated_at": now
            })
            self.db.collection(self.collection).document(check_id).collection("assessments").document("vision_analysis").set({
                "session_id": assessment_id,
                "shift_session_id": check_id,
                **vision_data
            }, merge=True)
            
            logger.info(f"Updated vision analysis for session {check_id}")
            return {"success": True, "message": "Vision analysis saved"}
        except Exception as e:
            logger.error(f"Error updating vision analysis: {e}")
            return {"success": False, "error": str(e)}
    
    def update_session_cognitive(self, check_id: str, cognitive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save cognitive test results to session"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            cognitive_data["timestamp"] = now
            session = self.get_session(check_id) or {}
            assessment_id = self._get_or_create_assessment_id(check_id, "cognitive_test", "cog")

            self.db.collection(self.collection).document(check_id).update({
                "shift_session_id": check_id,
                "user_id": session.get("user_id"),
                "updated_at": now
            })
            self.db.collection(self.collection).document(check_id).collection("assessments").document("cognitive_test").set({
                "session_id": assessment_id,
                "shift_session_id": check_id,
                **cognitive_data
            }, merge=True)
            
            logger.info(f"Updated cognitive test for session {check_id}")
            return {"success": True, "message": "Cognitive test saved"}
        except Exception as e:
            logger.error(f"Error updating cognitive test: {e}")
            return {"success": False, "error": str(e)}
    
    def update_session_behavioral(self, check_id: str, behavioral_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save behavioral assessment answers to session"""
        try:
            now = datetime.now(timezone.utc).isoformat()

            behavioral_data["timestamp"] = now
            session = self.get_session(check_id) or {}
            assessment_id = self._get_or_create_assessment_id(check_id, "behavioral_assessment", "behav")

            self.db.collection(self.collection).document(check_id).update({
                "shift_session_id": check_id,
                "user_id": session.get("user_id"),
                "updated_at": now
            })
            self.db.collection(self.collection).document(check_id).collection("assessments").document("behavioral_assessment").set({
                "session_id": assessment_id,
                "shift_session_id": check_id,
                **behavioral_data
            }, merge=True)
            
            logger.info(f"Updated behavioral assessment for session {check_id}")
            return {"success": True, "message": "Behavioral assessment saved"}
        except Exception as e:
            logger.error(f"Error updating behavioral assessment: {e}")
            return {"success": False, "error": str(e)}
    
    def update_session_result(
        self, 
        check_id: str, 
        overall_status: str,
        status_reason: str,
        detection_report: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save final result and detection to session"""
        try:
            now = datetime.utcnow().isoformat()

            # Calculate session duration
            session = self.get_session(check_id)
            if session and session.get("created_at"):
                created = datetime.fromisoformat(session["created_at"])
                now_dt = datetime.now(timezone.utc)
                duration = (now_dt - created).total_seconds()
            else:
                duration = None

            update_data = {
                "shift_session_id": check_id,
                "user_id": session.get("user_id") if session else None,
                "overall_status": overall_status,
                "status_reason": status_reason,
                "finished_at": now,
                "final_result_timestamp": now,
                "updated_at": now,
            }
            
            if detection_report:
                update_data["detection_report"] = detection_report
            
            if duration:
                update_data["session_duration_seconds"] = duration
            
            self.db.collection(self.collection).document(check_id).update(update_data)
            
            logger.info(f"Updated final result for session {check_id}: {overall_status}")
            return {"success": True, "message": "Final result saved"}
        except Exception as e:
            logger.error(f"Error updating final result: {e}")
            return {"success": False, "error": str(e)}
    
    def get_session(self, check_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a check session"""
        try:
            doc = self.db.collection(self.collection).document(check_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            logger.error(f"Error retrieving session {check_id}: {e}")
            return None
    
    def get_user_sessions(self, user_id: str) -> list[Dict[str, Any]]:
        """Get all check sessions for a user"""
        try:
            docs = self.db.collection(self.collection).where("user_id", "==", user_id).stream()
            sessions = [doc.to_dict() for doc in docs]
            return sessions
        except Exception as e:
            logger.error(f"Error retrieving sessions for user {user_id}: {e}")
            return []
    
    def get_user_latest_session(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent check session for a user"""
        try:
            query = (
                self.db.collection(self.collection)
                .where("user_id", "==", user_id)
                .order_by("created_at", direction="DESCENDING")
                .limit(1)
            )
            docs = list(query.stream())
            if docs:
                return docs[0].to_dict()
            return None
        except Exception as e:
            logger.error(f"Error retrieving latest session for user {user_id}: {e}")
            return None


# Create singleton instance
check_session_service = CheckSessionService()
