from django_filters import rest_framework as filters
from .models import Quiz

class QuizFilter(filters.FilterSet):
    code = filters.CharFilter(lookup_expr='icontains')
    created_at = filters.DateFromToRangeFilter()

    class Meta:
        model = Quiz
        fields = ['code', 'created_at']
