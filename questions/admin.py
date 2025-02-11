from django.contrib import admin

from questions.models import Question
from questions.models import Choice

# Register your models here.
admin.site.register(Question)
admin.site.register(Choice)