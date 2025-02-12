from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.authentication import BasicAuthentication, SessionAuthentication
from answers.models import Answer
from answers.serializers import AnswerSerializer
from questions.models import Choice, Question
from questions.serializers import ChoiceSerializer
from questions.paginations import PageNumberPagination

# Create your views here.
@api_view(['GET', 'POST'])
@authentication_classes([JWTAuthentication,BasicAuthentication,SessionAuthentication])
@permission_classes([IsAuthenticated])
def answer_list(request):
    if request.method == 'GET':
        if not request.user.has_perm('answers.view_answer'):
            return Response(status=403)

        questions = Question.objects.all()
        paginator = PageNumberPagination()
        paginated_questions = paginator.paginate_queryset(questions, request)
        question_responses = []

        for question in paginated_questions:
            answer = Answer.objects.filter(question=question, user=request.user).first()
            question_data = {
                'question_id': question.id,
                'question_text': question.question_text,
                'choices': [],
                'choice': None
            }

            choices = Choice.objects.filter(question=question)[:5]  # Limit choices to 5 per question
            choice_serializer = ChoiceSerializer(choices, many=True)
            question_data['choices'] = choice_serializer.data

            if answer:
                choice = answer.choice
                is_correct = choice.is_answer == 1
                question_data['choice'] = {
                    'choice_id': choice.id,
                    'choice_text': choice.choice_text,
                    'is_correct': is_correct
                }
            else:
                question_data['choice'] = {
                    'choice_id': None,
                    'choice_text': None,
                    'is_correct': False
                }
            
            question_responses.append(question_data)

        return paginator.get_paginated_response(question_responses)
    
    elif request.method == 'POST':
        if not request.user.has_perm('answers.add_answer'):
            return Response(status=403)

        question_id = request.data.get('question')  # Get question_id from request data

        if Answer.objects.filter(question_id=question_id, user=request.user).exists():
            return Response({'error': 'You have already answered this question.'}, status=400)

        serializer = AnswerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=201)
        
        return Response(serializer.errors, status=400)