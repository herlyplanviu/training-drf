from django.urls import path
from .views import PresenceCheckAPIView

urlpatterns = [
    path('presence-check/', PresenceCheckAPIView.as_view(), name='presence-check'),
]
