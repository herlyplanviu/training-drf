from rest_framework import serializers
from .models import User
from .models import GoogleAuth

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'avatar']

class GoogleAuthSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoogleAuth
        fields = ['token', 'refresh_token', 'token_uri', 'client_id', 'client_secret', 'scopes']
