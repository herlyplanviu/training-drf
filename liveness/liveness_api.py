from fastapi import FastAPI, WebSocket
import cv2
import numpy as np
import mediapipe as mp
import base64
import random
from operator import attrgetter

# FastAPI app
app = FastAPI()

# Load MediaPipe FaceMesh
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)
mp_drawing = mp.solutions.drawing_utils

# Landmark indices
LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374
MOUTH_TOP, MOUTH_BOTTOM = 13, 14
CHIN, SIDEHEAD, TOPHEAD, BOTTOMHEAD = 199, 447, 10, 152

# Constants for nod detection
FRAMES_TO_ANALYZE = 10
NODDING_SENSITIVITY = 0.0125
SHAKING_SENSITIVITY = 0.02
VERTICAL_ADJUSTMENT = 0.2
HORIZONTAL_ADJUSTMENT = 0.12

# Store nodding frames
nodding_coordinates = []
shaking_coordinates = []
nod_count = 0


def detect_blink(landmarks):
    """Detect blink using Eye Aspect Ratio (EAR)."""
    return all(abs(landmarks[eye_top, 1] - landmarks[eye_bottom, 1]) < 0.02
               for eye_top, eye_bottom in [(LEFT_EYE_TOP, LEFT_EYE_BOTTOM), (RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM)])


def detect_mouth_open(landmarks):
    """Detect if the mouth is open using a simple threshold."""
    return abs(landmarks[MOUTH_TOP, 1] - landmarks[MOUTH_BOTTOM, 1]) > 0.05


def direction_changes(data, coord_index, sensitivity):
    """Detects the number of significant direction changes in NumPy landmarks."""
    if len(data) < 2:
        return 0

    peak_or_valley = data[0][coord_index]
    num_direction_changes = 0
    prev_direction = None

    for i in range(1, len(data)):
        current_data = data[i][coord_index]
        if abs(peak_or_valley - current_data) > sensitivity:
            current_direction = 'increasing' if peak_or_valley < current_data else 'decreasing'

            if prev_direction and current_direction != prev_direction:
                num_direction_changes += 1
                peak_or_valley = current_data
            elif not prev_direction:
                prev_direction = current_direction
                peak_or_valley = current_data

    return num_direction_changes


def detect_nod(landmarks):
    """Detect head nodding (YES) movement."""
    global nodding_coordinates, shaking_coordinates, nod_count

    chin = landmarks[CHIN]
    sidehead = landmarks[SIDEHEAD]
    tophead = landmarks[TOPHEAD]
    bottomhead = landmarks[BOTTOMHEAD]

    # Calculate distance adjustment
    distance_adjustment = (bottomhead[1] - tophead[1]) / 0.5

    # Store coordinates
    nodding_coordinates.append(chin)
    shaking_coordinates.append(sidehead)

    # Limit stored frames
    if len(nodding_coordinates) > FRAMES_TO_ANALYZE:
        nodding_coordinates.pop(0)
    if len(shaking_coordinates) > FRAMES_TO_ANALYZE:
        shaking_coordinates.pop(0)

    # Detect nodding (YES)
    if (direction_changes(nodding_coordinates, 2, NODDING_SENSITIVITY * distance_adjustment) > 0
            and direction_changes(shaking_coordinates, 2, SHAKING_SENSITIVITY * distance_adjustment) == 0
            and abs(max(nodding_coordinates, key=lambda lm: lm[1])[1] - min(nodding_coordinates, key=lambda lm: lm[1])[1])
            <= VERTICAL_ADJUSTMENT * distance_adjustment):

        nod_count += 1
        nodding_coordinates.clear()
        shaking_coordinates.clear()

        # Verify after 3 nods
        if nod_count >= 3:
            nod_count = 0
            return True

    return False


@app.websocket("/ws/liveness")
async def liveness_websocket(websocket: WebSocket):
    await websocket.accept()
    
    challenge = random.choice(["blink", "mouth_open", "nod"])  # Random challenge
    await websocket.send_json({"challenge": challenge})

    try:
        while True:
            data = await websocket.receive_text()
            frame = cv2.imdecode(np.frombuffer(base64.b64decode(data), np.uint8), cv2.IMREAD_COLOR)
            
            # Resize to square image to avoid MediaPipe warnings
            height, width = frame.shape[:2]
            size = max(height, width)
            frame = cv2.resize(frame, (size, size))

            results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            if results.multi_face_landmarks:
                landmarks = np.array([(lm.x, lm.y, lm.z) for lm in results.multi_face_landmarks[0].landmark])

                if ((challenge == "blink" and detect_blink(landmarks)) or
                        (challenge == "mouth_open" and detect_mouth_open(landmarks)) or
                        (challenge == "nod" and detect_nod(landmarks))):

                    await websocket.send_json({"challenge": challenge, "action_detected": True})
                    # break  # Challenge completed

    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        await websocket.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
