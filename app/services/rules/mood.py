import logging

logger = logging.getLogger(__name__)


def calculate_mood(metrics: dict):
    brow = metrics.get("brow_furrow", 0)
    lip = metrics.get("lip_tighten", 0)
    mouth = metrics.get("mouth_open", 0)
    head_stability = metrics.get("head_stability", 0)
    blink_variance = metrics.get("blink_variance", 1)

    brow_tense = brow >= 0.5
    lip_tense = lip >= 0.5
    mouth_tense = mouth >= 0.6 and (brow_tense or lip_tense)

    tension = 0
    if brow_tense:
        tension += 1
    if lip_tense:
        tension += 1
    if mouth_tense:
        tension += 1

    happy = head_stability >= 0.9 and blink_variance <= 0.1

    if tension >= 2:
        mood = "angry"
    elif tension == 1:
        mood = "sad"
    elif happy:
        mood = "happy"
    else:
        mood = "neutral"

    logger.info(
        "calc_mood brow_furrow=%s lip_tighten=%s mouth_open=%s head_stability=%s blink_variance=%s thresholds=brow>=0.5 lip>=0.5 mouth>=0.6+{brow|lip} happy=head>=0.9+blink<=0.1 tension=%s mood=%s",
        brow,
        lip,
        mouth,
        head_stability,
        blink_variance,
        tension,
        mood,
    )

    return mood
