# face_recognition/utils.py

import cv2
import face_recognition
import numpy as np

import face_recognition

from users.models import Person

def encode_face(image_file):
    # Convert the uploaded image to an in-memory object (face_recognition works with files, not in-memory byte strings)
    image = face_recognition.load_image_file(image_file)
    encoding = face_recognition.face_encodings(image)

    if encoding:  # If there is at least one face encoding in the list
        return encoding[0]  # Return the first face encoding

    return None  # Return None if no face encodings are found

def recognize_face(image_path, known_face_encodings):
    unknown_image = face_recognition.load_image_file(image_path)
    unknown_encoding = face_recognition.face_encodings(unknown_image)

    if unknown_encoding:
        unknown_encoding = unknown_encoding[0]
        for known_encoding in known_face_encodings:
            results = face_recognition.compare_faces([known_encoding], unknown_encoding)
            if results[0]:
                return True  # Face recognized
    return False

    
def stream_video(self):
        # Open the video capture (using the default webcam)
        video_capture = cv2.VideoCapture(0)

        while True:
            # Capture frame-by-frame
            ret, frame = video_capture.read()
            
            # Find all face locations and face encodings in the current frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)

            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Check if the face matches any stored face encodings
                matches = face_recognition.compare_faces(
                    [np.frombuffer(person.face_encoding, dtype=np.float64) for person in Person.objects.all()],
                    face_encoding
                )

                name = "Unknown"  # Default name if no match
                color = (0, 0, 255)  # Red color for unknown face (BGR format)

                # If a match is found, retrieve the corresponding person's name and set the color to green
                if True in matches:
                    match_index = matches.index(True)
                    recognized_person = Person.objects.all()[match_index]
                    name = f'{recognized_person.user.first_name} {recognized_person.user.last_name}'
                    color = (0, 255, 0)  # Green color for recognized face

                # Get the coordinates of the face in the frame
                top, right, bottom, left = face_location

                # Draw a rectangle around the face
                cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

                # Display the name label
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.5, color, 1)

            # Encode the frame in JPEG format
            ret, jpeg = cv2.imencode('.jpg', frame)

            # If encoding was successful, yield the frame as part of the HTTP response
            if ret:
                # Convert the frame into a byte stream and yield it
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

        video_capture.release()