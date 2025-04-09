from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from geopy.distance import geodesic

# Reference location
REFERENCE_LOCATION = (-7.9673435, 112.6267206)  # (lat, lon)
DISTANCE = 20 # in meters

class PresenceCheckAPIView(APIView):
    def post(self, request, *args, **kwargs):
        try:
            lat = float(request.data.get('lat'))
            lon = float(request.data.get('lon'))
        except (TypeError, ValueError):
            return Response({"detail": "Invalid latitude or longitude."}, status=status.HTTP_400_BAD_REQUEST)

        user_location = (lat, lon)
        distance = geodesic(REFERENCE_LOCATION, user_location).meters

        if distance <= DISTANCE:
            return Response({"detail": "Success. You are within the allowed area."}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "You are out of area"}, status=status.HTTP_403_FORBIDDEN)
