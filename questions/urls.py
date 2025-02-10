from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("", views.question_list, name="question_list"),
    path("<int:pk>/", views.question_detail, name="question_detail"),

]