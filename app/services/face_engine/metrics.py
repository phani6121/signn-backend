import statistics

# -----------------------------
# Constants (from engine.py)
# -----------------------------
EYE_AR_THRESH = 0.22
FPS = 30

MIN_SUSTAINED_CLOSED_SEC = 1.5
MAX_CUMULATIVE_CLOSED_SEC = 3.0


# -----------------------------
# Helpers
# -----------------------------
def _frame_ts_ms(frame):
    ts = frame.get("data", {}).get("timestamp_ms")
    if isinstance(ts, (int, float)):
        return ts
    return None


def _mean_frame_value(frames, key):
    vals = []
    for f in frames:
        v = f.get("data", {}).get(key)
        if isinstance(v, (int, float)):
            vals.append(v)
    if not vals:
        return None
    return statistics.mean(vals)


# -----------------------------
# Feature aggregation
# (EXACT COPY OF _aggregate_features)
# -----------------------------
def aggregate_features(frames):
    """
    Aggregate numeric facial features from frames.
    EXACTLY matches engine.py::_aggregate_features
    """

    if not frames:
        return {}

    def collect(key):
        vals = []
        for f in frames:
            v = f.get("data", {}).get(key)
            if isinstance(v, (int, float)):
                vals.append(v)
        return vals

    aggregates = {}

    mean_keys = [
        "eye_blink_rate",
        "head_stability",
        "face_visibility",
        "avg_eye_open_duration",
        "blink_variance",
        "head_tilt_variance",
    ]

    max_keys = [
        "brow_furrow",
        "lip_tighten",
        "mouth_open",
    ]

    for key in mean_keys:
        vals = collect(key)
        if vals:
            aggregates[key] = statistics.mean(vals)

    for key in max_keys:
        vals = collect(key)
        if vals:
            aggregates[key] = max(vals)

    if "face_visibility" not in aggregates and frames:
        aggregates["face_visibility"] = 0

    return aggregates


# -----------------------------
# Fatigue metrics
# (EXACT COPY OF _detect_fatigue_from_frames LOGIC)
# -----------------------------
def fatigue_time_metrics(frames):
    """
    Computes eye-closure time metrics required for fatigue rules.
    Returns:
      - eye_closed_run_sec
      - eye_closed_total_sec
    """

    closed_time_sec = 0.0
    closed_run_sec = 0.0
    last_ts_ms = None

    for f in frames:
        ear = f.get("data", {}).get("eye_aspect_ratio")
        if not isinstance(ear, (int, float)):
            continue

        ts_ms = _frame_ts_ms(f)
        if ts_ms is not None and last_ts_ms is not None:
            delta_sec = max(0.0, (ts_ms - last_ts_ms) / 1000.0)
        else:
            delta_sec = 1.0 / FPS

        if ts_ms is not None:
            last_ts_ms = ts_ms

        if ear < EYE_AR_THRESH:
            closed_time_sec += delta_sec
            closed_run_sec += delta_sec
        else:
            closed_run_sec = 0.0

    return {
        "eye_closed_run_sec": closed_run_sec,
        "eye_closed_total_sec": closed_time_sec,
    }


# -----------------------------
# PUBLIC ENTRY (THIS IS WHAT YOU CALL)
# -----------------------------
def compute_metrics(frames):
    """
    FINAL metrics object used by rules.
    This matches EXACTLY what engine.py produces.
    """

    aggregates = aggregate_features(frames)
    fatigue_metrics = fatigue_time_metrics(frames)
    ear_mean = _mean_frame_value(frames, "eye_aspect_ratio")

    metrics = {}
    metrics.update(aggregates)
    metrics.update(fatigue_metrics)

    if isinstance(ear_mean, (int, float)):
        metrics["eye_aspect_ratio"] = ear_mean

    return metrics
