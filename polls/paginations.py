from rest_framework.pagination import PageNumberPagination

class PageNumberPagination(PageNumberPagination):
    page_size = 5  # Default number of items per page
    page_size_query_param = "page_size"  # Allow clients to control page size
    max_page_size = 50  # Prevent very large requests