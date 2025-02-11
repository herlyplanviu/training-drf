from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication

# Create your views here.
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user(request):
    user = request.user  # Get the current authenticated user

    # Get direct user permissions
    user_permissions = user.get_user_permissions()

    # Get permissions from groups
    group_permissions = user.get_group_permissions()

    # Combine both sets of permissions
    all_permissions = user_permissions.union(group_permissions)

    response_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "is_active": user.is_active,
            "permissions": list(all_permissions)
        }

    return Response(response_data)