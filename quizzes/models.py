from django.db import models
from django.utils import timezone

from users.models import User

# Create your models here.
class Quiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=10)
    created_at = models.DateTimeField('created at', default=timezone.now)
    
    def __str__(self):
        return self.code