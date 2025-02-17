# face_recognition/urls.py

from django.urls import path
from .views import TrainFace, TestFace, VideoRecognitionView

urlpatterns = [
    path('train/', TrainFace.as_view(), name='train_face'),
    path('test/', TestFace.as_view(), name='test_face'),
    path('video/', VideoRecognitionView.as_view(), name='video_recognition'),  # Map the URL to the VideoRecognitionView
]
