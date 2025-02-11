from django.urls import path
from .views import answer_list

urlpatterns = [
    path('answers/', answer_list, name='answer-list'),
]