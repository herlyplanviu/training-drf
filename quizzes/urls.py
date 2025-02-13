# quizzes/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from quizzes.views import QuizViewSet

router = DefaultRouter()
router.register(r'quizzes', QuizViewSet)

urlpatterns = []
