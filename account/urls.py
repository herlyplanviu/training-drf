from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("profile/permissions/", views.get_user_permissions, name="profile_permissions"),
]