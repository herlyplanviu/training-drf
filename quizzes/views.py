# quizzes/views.py
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from quizzes.models import Quiz
from quizzes.serializers import QuizOnlySerializer

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizOnlySerializer
    authentication_classes = [JWTAuthentication, BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        if not request.user.has_perm('quizzes.view_quiz'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        quizzes = self.queryset
        paginator = self.pagination_class()
        paginator.page_size = 5
        paginated_quizzes = paginator.paginate_queryset(quizzes, request)

        quiz_responses = []
        for quiz in paginated_quizzes:
            is_answered = quiz.user == request.user  # Or however you check quiz completion
            serialized_quiz = QuizOnlySerializer(quiz).data
            serialized_quiz["is_answered"] = is_answered
            quiz_responses.append(serialized_quiz)

        return paginator.get_paginated_response(quiz_responses)

    def retrieve(self, request, *args, **kwargs):
        quiz = get_object_or_404(self.queryset, pk=kwargs['pk'])
        if not request.user.has_perm('quizzes.view_quiz'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        is_answered = quiz.user == request.user
        serializer = self.get_serializer(quiz)
        quiz_data = serializer.data
        quiz_data["is_answered"] = is_answered
        
        return Response(quiz_data)
    
    def create(self, request, *args, **kwargs):
        if not request.user.has_perm('quizzes.add_quiz'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        quiz = get_object_or_404(self.queryset, pk=kwargs['pk'])
        
        if not request.user.has_perm('quizzes.change_quiz'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(quiz, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=quiz.user)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        quiz = get_object_or_404(self.queryset, pk=kwargs['pk'])
        
        if not request.user.has_perm('quizzes.delete_quiz'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        self.perform_destroy(quiz)
        return Response(status=status.HTTP_204_NO_CONTENT)
