from django.db import models

from quizzes.models import Quiz

# Create your models here.
class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    
    class Meta:
        permissions = (
            ("export_question", "Can export question"),
        )

    def __str__(self):
        return self.question_text


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='choices')
    choice_text = models.CharField(max_length=200)
    is_answer = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text