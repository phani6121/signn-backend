def calculate_mood(metrics: dict):
    brow = metrics.get("brow_furrow", 0)
    lip = metrics.get("lip_tighten", 0)
    mouth = metrics.get("mouth_open", 0)
    head_stability = metrics.get("head_stability", 0)
    blink_variance = metrics.get("blink_variance", 1)

    tension = 0
    if brow >= 0.5:
        tension += 1
    if lip >= 0.5:
        tension += 1
    if mouth >= 0.6 and (brow >= 0.5 or lip >= 0.5):
        tension += 1

    if tension >= 2:
        return "angry"
    if tension == 1:
        return "sad"

    if head_stability >= 0.9 and blink_variance <= 0.1:
        return "happy"

    return "neutral"
