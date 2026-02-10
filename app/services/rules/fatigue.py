import logging

logger = logging.getLogger(__name__)


def calculate_fatigue(metrics: dict):
    eye_closed_run = metrics.get("eye_closed_run_sec", 0)
    eye_closed_total = metrics.get("eye_closed_total_sec", 0)

    detected = eye_closed_run >= 1.5 or eye_closed_total >= 3.0
    logger.info(
        "calc_fatigue eye_closed_run_sec=%s eye_closed_total_sec=%s threshold_run_sec=1.5 threshold_total_sec=3.0 detected=%s",
        eye_closed_run,
        eye_closed_total,
        detected,
    )

    return "detected" if detected else "not_detected"
