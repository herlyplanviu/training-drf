from django.urls import re_path
from .views import LivenessConsumer

websocket_urlpatterns = [
    re_path(r"ws/liveness/$", LivenessConsumer.as_asgi()),
]