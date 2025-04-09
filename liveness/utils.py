import json
from uuid import UUID
import cv2
import numpy as np
import face_recognition
import base64

from users.models import Person
from .modules.blink import detect_blink
from .modules.open_mouth import detect_mouth_open
from .modules.nod import detect_nod
from .modules.emotion import detect_emotion
from asgiref.sync import sync_to_async

def uuid_to_bin(uuid_obj: UUID) -> bytes:
    return uuid_obj.bytes

def bin_to_uuid(bin_data: bytes) -> UUID:
    return UUID(bytes=bin_data)

@sync_to_async
def send_error(ws, message: str):
    return ws.send_json({
        "error": message,
        "challenge": None,
        "action_detected": False
    })

def decode_frame(data: str):
    return cv2.imdecode(np.frombuffer(base64.b64decode(data), np.uint8), cv2.IMREAD_COLOR)

def is_low_light(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray) < 50  # Adjust threshold as needed

def resize_to_square(frame):
    height, width = frame.shape[:2]
    size = max(height, width)
    return cv2.resize(frame, (size, size))

def match_face(frame, face):
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)
    stored_encoding = np.frombuffer(face.face_encoding, dtype=np.float64)

    for encoding in face_encodings:
        if face_recognition.compare_faces([stored_encoding], encoding)[0]:
            return True
    return False

def get_landmarks(results):
    return np.array([(lm.x, lm.y, lm.z) for lm in results.multi_face_landmarks[0].landmark])

def detect_challenge_action(challenge, frame, landmarks):
    return (
        (challenge == "blink" and detect_blink(landmarks)) or
        (challenge == "mouth_open" and detect_mouth_open(landmarks)) or
        (challenge == "happy" and detect_emotion(frame, "happy")) or
        (challenge == "surprise" and detect_emotion(frame, "surprise")) or
        (challenge == "nod" and detect_nod(landmarks))
    )
    
@sync_to_async
def get_person(user_id):
    return Person.objects.get(user_id=user_id)

async def send_error(self, message):
    await self.send(text_data=json.dumps({
        "error": message,
        "challenge": None,
        "action_detected": False
    }))