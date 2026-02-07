def calculate_stress(metrics: dict):
    brow = metrics.get("brow_furrow", 0)
    lip = metrics.get("lip_tighten", 0)
    mouth = metrics.get("mouth_open", 0)

    if (
        brow >= 0.35
        or lip >= 0.35
        or (mouth >= 0.55 and (brow >= 0.35 or lip >= 0.35))
    ):
        return "detected"

    return "not_detected"
