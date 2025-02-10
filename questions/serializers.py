from rest_framework import serializers
from .models import Question, Choice

# Choice Serializer (for nested relationship)
class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ['id', 'choice_text', 'votes']

# Question Serializer (including ChoiceSerializer)
class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)  # Include related choices

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'pub_date', 'choices']  # Include 'choices'
