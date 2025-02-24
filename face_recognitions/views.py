# face_recognition/views.py

from io import BytesIO
from django.http import StreamingHttpResponse
from django.views import View
import numpy as np

from face_recognitions.serializers import FaceRecognitionSerializer
from users.models import Person
from .utils import encode_face, recognize_face, stream_video
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class TrainFace(APIView):
    def post(self, request):
        # Get the uploaded image from the request
        image_file = request.FILES.get('image')

        encoding = encode_face(image_file)

        # If encoding is found, save it
        if encoding is not None:
            person, created = Person.objects.get_or_create(user=request.user)
            person.face_encoding = np.array(encoding)  # Store the encoding as a NumPy array
            person.save()
            
            return Response({"message": "Person trained successfully"}, status=status.HTTP_201_CREATED)
        
        return Response({"error": "No face found in the image"}, status=status.HTTP_400_BAD_REQUEST)

class TestFace(APIView):
    def post(self, request):
        # Deserialize the incoming data
        serializer = FaceRecognitionSerializer(data=request.data)
        
        if serializer.is_valid():
            # Get the image from the serializer
            image_file = serializer.validated_data.get('image')

            # Convert the InMemoryUploadedFile to a file-like object for face_recognition
            image_bytes = BytesIO(image_file.read())

            # Retrieve the currently logged-in user
            user = request.user

            # Retrieve the Person object for the logged-in user
            try:
                person = Person.objects.get(user=user)
            except Person.DoesNotExist:
                return Response({"error": "User does not have a registered face encoding."}, status=status.HTTP_400_BAD_REQUEST)

            # Get the face encoding for the logged-in user
            known_face_encoding = np.frombuffer(person.face_encoding, dtype=np.float64)

            # Call the recognize_face function to check if the face matches
            recognized = recognize_face(image_bytes, [known_face_encoding])

            # Return the result of the face recognition
            if recognized:
                return Response({"message": "Face match!"}, status=status.HTTP_200_OK)
            else:
                return Response({"message": "Face not match."}, status=status.HTTP_400_BAD_REQUEST)

        # Handle serializer errors if data is invalid
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class VideoRecognitionView(View):
    def get(self, request, *args, **kwargs):
        # Stream the video feed directly to the browser
        return StreamingHttpResponse(stream_video(self), content_type='multipart/x-mixed-replace; boundary=frame')