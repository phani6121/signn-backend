from app.services.face_engine.metrics import compute_metrics


def run_face_scan(frames: list):
    """
    REAL implementation based on engine.py (2nd zip)

    frames: list of dicts where each frame already contains:
      frame["data"]["eye_aspect_ratio"]
      frame["data"]["eye_blink_rate"]
      frame["data"]["blink_variance"]
      frame["data"]["brow_furrow"]
      frame["data"]["lip_tighten"]
      frame["data"]["mouth_open"]
      frame["data"]["head_stability"]
      frame["data"]["head_tilt_variance"]
      frame["data"]["face_visibility"]
      frame["data"]["timestamp_ms"]

    Returns:
      metrics dict (EXACTLY what rules expect)
    """

    if not frames or not isinstance(frames, list):
        return {}

    # This uses EXACT logic extracted from engine.py
    metrics = compute_metrics(frames)

    return metrics
