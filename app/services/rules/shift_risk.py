import logging

logger = logging.getLogger(__name__)


def calculate_shift_risk(
    stress_detected: bool,
    mood: str,
    fatigue_score: float,
    eye_aspect_ratio: float,
):
    high = stress_detected and mood == "angry" and fatigue_score >= 0.25
    low = (not stress_detected) and mood in ("happy", "neutral") and eye_aspect_ratio >= 0.22

    if high:
        result = {
            "shift_risk": "HIGH",
            "action": "BREAK_REQUIRED",
        }
    elif low:
        result = {
            "shift_risk": "LOW",
            "action": "LOGIN_ALLOWED",
        }
    else:
        result = {
            "shift_risk": "MEDIUM",
            "action": "REVIEW_REQUIRED",
        }

    logger.info(
        "calc_shift_risk stress_detected=%s mood=%s fatigue_score=%s eye_aspect_ratio=%s thresholds=high(stress+angry+fatigue>=0.25) low(!stress+happy|neutral+ear>=0.22) result=%s",
        stress_detected,
        mood,
        fatigue_score,
        eye_aspect_ratio,
        result,
    )

    return result
