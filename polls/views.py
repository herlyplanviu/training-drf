from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


from polls.models import Question
from polls.paginations import PageNumberPagination
from polls.serializers import QuestionSerializer

# Create your views here.
@api_view(['GET', 'POST'])
def question_list(request):
    if request.method == 'GET':
        questions = Question.objects.order_by("-pub_date")

        paginator = PageNumberPagination()
        paginator.page_size = 5
        paginated_questions = paginator.paginate_queryset(questions, request)

        serializer = QuestionSerializer(paginated_questions, many=True)
        return paginator.get_paginated_response(serializer.data)

    elif request.method == 'POST':
        serializer = QuestionSerializer(data=request.data)  # Deserialize input data
        if serializer.is_valid():
            serializer.save()  # Save if valid
            return Response(serializer.data, status=status.HTTP_201_CREATED)  # Return created data
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)  # Handle errors
    
# Retrieve, update (PUT), or delete (DELETE) a single question
@api_view(['GET', 'PUT', 'DELETE'])
def question_detail(request, pk):
    question = get_object_or_404(Question, pk=pk)

    if request.method == 'GET':
        serializer = QuestionSerializer(question)
        return Response(serializer.data)

    elif request.method == 'PUT':  # Update an existing question
        serializer = QuestionSerializer(question, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':  # Delete a question
        question.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)