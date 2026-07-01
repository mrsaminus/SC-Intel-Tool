from statistics import mean


def clamp_confidence(value):
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, numeric))


def average_confidence(values):
    cleaned = [clamp_confidence(value) for value in values]
    cleaned = [value for value in cleaned if value is not None]
    if not cleaned:
        return None
    return mean(cleaned)


def confidence_label(value):
    value = clamp_confidence(value)
    if value is None:
        return "Unknown"
    if value >= 0.85:
        return "High"
    if value >= 0.60:
        return "Medium"
    return "Low"


def confidence_warnings(value, minimum=0.60):
    value = clamp_confidence(value)
    if value is None:
        return ("confidence_unavailable",)
    if value < minimum:
        return ("low_confidence",)
    return ()
