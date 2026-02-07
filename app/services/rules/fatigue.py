def calculate_fatigue(metrics: dict):
    eye_closed_run = metrics.get("eye_closed_run_sec", 0)
    eye_closed_total = metrics.get("eye_closed_total_sec", 0)

    if eye_closed_run >= 1.5 or eye_closed_total >= 3.0:
        return "detected"

    return "not_detected"
