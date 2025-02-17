from rest_framework import serializers

from quizzes.models import Quiz
from quizzes.serializers import QuizOnlySerializer
from .models import Question, Choice

# Choice Serializer (for nested relationship)
class ChoiceSerializer(serializers.ModelSerializer):
    question = serializers.PrimaryKeyRelatedField(queryset=Question.objects.all())
    
    is_answer = serializers.BooleanField(required=False)
    class Meta:
        model = Choice
        fields = ['id', 'choice_text', 'is_answer', 'question']

# Question Serializer (including ChoiceSerializer)
class QuestionSerializer(serializers.ModelSerializer):
    choices = ChoiceSerializer(many=True, read_only=True)  # Include related choices
    # quiz = QuizOnlySerializer(many=False, read_only=True)
    quiz = serializers.PrimaryKeyRelatedField(queryset=Quiz.objects.all())

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'pub_date', 'choices', 'quiz']  # Include 'choices'
        
class QuestionOnlySerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['id']  # Include 'choices'
