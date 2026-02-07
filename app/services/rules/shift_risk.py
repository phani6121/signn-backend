def calculate_shift_risk(
    stress_detected: bool,
    mood: str,
    fatigue_score: float,
    eye_aspect_ratio: float,
):
    if (
        stress_detected
        and mood == "angry"
        and fatigue_score >= 0.25
    ):
        return {
            "shift_risk": "HIGH",
            "action": "BREAK_REQUIRED",
        }

    if (
        not stress_detected
        and mood in ("happy", "neutral")
        and eye_aspect_ratio >= 0.22
    ):
        return {
            "shift_risk": "LOW",
            "action": "LOGIN_ALLOWED",
        }

    return {
        "shift_risk": "MEDIUM",
        "action": "REVIEW_REQUIRED",
    }
