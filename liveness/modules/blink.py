# Landmark indices
LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374

def detect_blink(landmarks):
    """Detect blink using Eye Aspect Ratio (EAR)."""
    return all(abs(landmarks[eye_top, 1] - landmarks[eye_bottom, 1]) < 0.02
               for eye_top, eye_bottom in [(LEFT_EYE_TOP, LEFT_EYE_BOTTOM), (RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM)])