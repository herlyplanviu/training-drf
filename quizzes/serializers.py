from rest_framework import serializers

from quizzes.models import Quiz
from users.serializers import UserProfileSerializer

class QuizSerializer(serializers.ModelSerializer):
    questions = serializers.SerializerMethodField()
    user = UserProfileSerializer(many=False, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'code', 'created_at', 'user', 'questions']
        
    def get_questions(self, obj):
        from questions.models import Question  # Import model directly
        return list(obj.questions.values('id', 'question_text'))
    

class QuizOnlySerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(many=False, read_only=True)

    class Meta:
        model = Quiz
        fields = ['id', 'code', 'created_at', 'user']