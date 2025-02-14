from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from answers.models import Answer
from questions.models import Choice, Question
from questions.paginations import PageNumberPagination
from questions.serializers import ChoiceSerializer, QuestionOnlySerializer, QuestionSerializer
from rest_framework.generics import ListAPIView

class QuestionList(ListAPIView): 
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    pagination_class = PageNumberPagination
    
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    authentication_classes = [JWTAuthentication, BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination

    def get_permissions(self):
        # Only authenticated users can create, update, or delete
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()

    def list(self, request , *args, **kwargs):
        if not request.user.has_perm('questions.view_question'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        # Coba versioning
        version = kwargs.get('version', None)
        
        if version == "v1":
            total = request.GET.get("total")
            if total is None:
                questions = Question.objects.all()
            else:
                total = int(total)
                questions = Question.objects.order_by('?')[:total]
                
            paginator = self.pagination_class()
            paginator.page_size = 5
            paginated_questions = paginator.paginate_queryset(questions, request)

            question_responses = []
            for index, question in enumerate(paginated_questions, start=1):
                answer_exists = Answer.objects.filter(question=question, user=request.user).exists()
                if request.GET.get("choices") == "0":
                    serialized_question = QuestionOnlySerializer(question).data
                else:
                    serialized_question = QuestionSerializer(question).data
                serialized_question["is_answered"] = answer_exists
                serialized_question["number"] = index
                question_responses.append(serialized_question)
                

            return paginator.get_paginated_response(question_responses)
        
        elif version == 'v2':
            return Response(status=status.HTTP_501_NOT_IMPLEMENTED, data={"detail": "Not implemented yet"})

    def retrieve(self, request, *args, **kwargs):
        question = get_object_or_404(self.queryset, pk=kwargs['pk'])
        if not request.user.has_perm('questions.view_question'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        answer_exists = Answer.objects.filter(question=question, user=request.user).exists()

        serializer = self.get_serializer(question)
        question_data = serializer.data
        question_data["is_answered"] = answer_exists
        
        return Response(question_data)
    
    def create(self, request, *args, **kwargs):
        # Check permission for creating a question
        if not request.user.has_perm('questions.add_question'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        question = get_object_or_404(self.queryset, pk=kwargs['pk'])
        
        # Check permission for updating a question
        if not request.user.has_perm('questions.change_question'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(question, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        question = get_object_or_404(self.queryset, pk=kwargs['pk'])
        
        # Check permission for deleting a question
        if not request.user.has_perm('questions.delete_question'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        self.perform_destroy(question)
        return Response(status=status.HTTP_204_NO_CONTENT)

class ChoiceViewSet(viewsets.ModelViewSet):
    queryset = Choice.objects.all()
    serializer_class = ChoiceSerializer
    authentication_classes = [JWTAuthentication, BasicAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PageNumberPagination
    pagination_class.page_size = 10

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAuthenticated]
        return super().get_permissions()
    
    def list(self, request, *args, **kwargs):
        if not request.user.has_perm('questions.view_choice'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        paginator = self.pagination_class()
        paginated_choices = paginator.paginate_queryset(self.queryset, request)
        
        serializer = self.get_serializer(paginated_choices, many=True)
        return paginator.get_paginated_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        choice = get_object_or_404(self.queryset, pk=kwargs['pk'])
        if not request.user.has_perm('questions.view_choice'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(choice)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        # Check permission for creating a choice
        if not request.user.has_perm('questions.add_choice'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def update(self, request, *args, **kwargs):
        choice = get_object_or_404(self.queryset, pk=kwargs['pk'])
        
        # Check permission for updating a choice
        if not request.user.has_perm('questions.change_choice'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        serializer = self.get_serializer(choice, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        return Response(serializer.data)
    
    def destroy(self, request, *args, **kwargs):
        choice = get_object_or_404(self.queryset, pk=kwargs['pk'])
        
        # Check permission for deleting a choice
        if not request.user.has_perm('questions.delete_choice'):
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        self.perform_destroy(choice)
        return Response(status=status.HTTP_204_NO_CONTENT)
