from django.urls import path

from .views import QuestionList

urlpatterns = [
    path('questions-list/',QuestionList.as_view(), name='userpage-question')
]
