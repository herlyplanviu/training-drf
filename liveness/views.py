import json
import cv2
import random
from channels.generic.websocket import AsyncWebsocketConsumer
from users.models import Person
from .utils import decode_frame, get_person, is_low_light, resize_to_square, match_face, get_landmarks, detect_challenge_action, send_error
from .modules.spoof import detect_spoofing
import mediapipe as mp

mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(refine_landmarks=True)

class LivenessConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['query_string'].decode().split("user_id=")[-1]
        if not self.user_id:
            await send_error(self, "Missing user_id")
            await self.close()
            return
        
        try:
            self.face = await get_person(self.user_id)
        except Person.DoesNotExist:
            await send_error(self, "Face not registered")
            await self.close()
            return

        self.challenge = random.choice(["blink", "mouth_open", "happy", "surprise"])
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            frame = decode_frame(text_data)

            if is_low_light(frame):
                await send_error(self, "Low light condition")
                return

            frame = resize_to_square(frame)
            results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            if not results.multi_face_landmarks:
                await send_error(self, "No face detected")
                return

            if not match_face(frame, self.face):
                await send_error(self, "Face does not match")
                return

            spoofing = detect_spoofing(frame)
            if spoofing:
                print("Liveness:", spoofing["label"])
            else:
                print("No face or not confident enough")

            landmarks = get_landmarks(results)
            action_detected = bool(detect_challenge_action(self.challenge, frame, landmarks))

            await self.send(text_data=json.dumps({
                "error": None,
                "challenge": self.challenge,
                "action_detected": action_detected
            }))


            if action_detected:
                await self.close()

        except Exception as e:
            print("Error in receive:", e)
            await send_error(self, "Internal server error")

