from django.db import models
from django.db import models
from questions.models import Question, Choice
from users.models import User

# Create your models here.

class Answer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"Answer by {self.user} to question {self.question}"
