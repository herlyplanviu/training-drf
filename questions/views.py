from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication



from questions.models import Choice, Question
from questions.paginations import PageNumberPagination
from questions.serializers import ChoiceSerializer, QuestionSerializer

# Create your views here.
@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def question_list(request):
    if request.method == 'GET':
        if not request.user.has_perm('questions.view_question'):
            return Response(status=403)
        
        questions = Question.objects.order_by("-pub_date")

        paginator = PageNumberPagination()
        paginator.page_size = 5
        paginated_questions = paginator.paginate_queryset(questions, request)

        serializer = QuestionSerializer(paginated_questions, many=True)
        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        if not request.user.has_perm('questions.add_question'):
            return Response(status=403)
        
        serializer = QuestionSerializer(data=request.data)  # Deserialize input data
        if serializer.is_valid():
            serializer.save()  # Save if valid
            return Response(serializer.data, status=status.HTTP_201_CREATED)  # Return created data
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # Handle errors
    
@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)

    if request.method == 'GET':
        if not request.user.has_perm('questions.view_question'):
            return Response(status=403)
        
        serializer = QuestionSerializer(question)
        return Response(serializer.data)

    elif request.method == 'PUT':  # Update an existing question
        if not request.user.has_perm('questions.change_question'):
            return Response(status=403)
        
        serializer = QuestionSerializer(question, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':  # Delete a question
        if not request.user.has_perm('questions.delete_question'):
            return Response(status=403)
        
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def choice_list(request):
    if request.method == 'GET':
        if not request.user.has_perm('questions.view_choice'):
            return Response(status=403)
        
        choices = Choice.objects.all()
        
        paginator = PageNumberPagination()
        paginator.page_size = 5
        paginated_choices = paginator.paginate_queryset(choices, request)
        
        serializer = ChoiceSerializer(paginated_choices, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        if not request.user.has_perm('questions.add_choice'):
            return Response(status=403)
        
        serializer = ChoiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PUT', 'DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def choice_detail(request, pk):
    try:
        choice = Choice.objects.get(pk=pk)
    except Choice.DoesNotExist:
        return Response({'error': 'Choice not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        if not request.user.has_perm('questions.view_choice'):
            return Response(status=403)
        
        serializer = ChoiceSerializer(choice)
        return Response(serializer.data)

    elif request.method == 'PUT':
        if not request.user.has_perm('questions.change_choice'):
            return Response(status=403)
        
        serializer = ChoiceSerializer(choice, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        if not request.user.has_perm('questions.delete_choice'):
            return Response(status=403)
        
        choice.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)