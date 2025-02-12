from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestionViewSet, ChoiceViewSet, QuestionList

router = DefaultRouter()
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'choices', ChoiceViewSet, basename='choice')

urlpatterns = [
    path('', include(router.urls)),
    path('questions-list/',QuestionList.as_view(), name='userpage-question')
]
