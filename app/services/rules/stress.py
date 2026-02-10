import logging

logger = logging.getLogger(__name__)


def calculate_stress(metrics: dict):
    brow = metrics.get("brow_furrow", 0)
    lip = metrics.get("lip_tighten", 0)
    mouth = metrics.get("mouth_open", 0)

    brow_trigger = brow >= 0.35
    lip_trigger = lip >= 0.35
    mouth_trigger = mouth >= 0.55 and (brow_trigger or lip_trigger)
    detected = brow_trigger or lip_trigger or mouth_trigger

    logger.info(
        "calc_stress brow_furrow=%s lip_tighten=%s mouth_open=%s thresholds=brow>=0.35 lip>=0.35 mouth>=0.55+{brow|lip} triggers=brow=%s lip=%s mouth_combo=%s detected=%s",
        brow,
        lip,
        mouth,
        brow_trigger,
        lip_trigger,
        mouth_trigger,
        detected,
    )

    return "detected" if detected else "not_detected"
