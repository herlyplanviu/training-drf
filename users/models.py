from django.db import models
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import User

# Create your models here.
class User(AbstractUser):
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)


class GoogleAuth(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.TextField()
    refresh_token = models.CharField(max_length=255, null=True, blank=True)
    token_uri = models.CharField(max_length=255)
    client_id = models.CharField(max_length=255)
    client_secret = models.CharField(max_length=255)
    scopes = models.TextField()

    def __str__(self):
        return f"{self.user.username}'s Google Auth"

class Person(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    face_encoding = models.BinaryField(null=True, blank=True)

    def __str__(self):
        return self.user.username
