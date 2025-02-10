from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("questions/", views.question_list, name="question_list"),
    path("questions/<int:pk>/", views.question_detail, name="question_detail"),
    path("choices/", views.choice_list, name="choice_list"),  # List & Create
    path("choices/<int:pk>/", views.choice_detail, name="choice_detail"),  # Retrieve, Update, Delete
]