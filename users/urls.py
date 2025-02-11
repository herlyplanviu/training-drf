from django.urls import path

from . import views

urlpatterns = [
    # ex: /polls/
    path("profile/", views.get_user, name="profile"),
    path('profile/change-avatar', views.change_avatar, name='change-avatar'),
]