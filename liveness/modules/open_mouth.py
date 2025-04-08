# Landmark indices
MOUTH_TOP, MOUTH_BOTTOM = 13, 14

def detect_mouth_open(landmarks):
    """Detect if the mouth is open using a simple threshold."""
    return abs(landmarks[MOUTH_TOP, 1] - landmarks[MOUTH_BOTTOM, 1]) > 0.05