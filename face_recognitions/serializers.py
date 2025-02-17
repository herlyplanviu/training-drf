# face_recognition/serializers.py

from rest_framework import serializers

class FaceRecognitionSerializer(serializers.Serializer):
    image = serializers.ImageField()
    name = serializers.CharField(max_length=100, required=False)
