from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from users.serializers import UserProfileSerializer

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
    
    l = request.user.groups.values_list('name',flat = True)
    l_as_list = list(l)

    response_data = {
            "id": user.id,
            "name": {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": f"{user.first_name} {user.last_name}"
                },
            "username": user.username,
            "email": user.email,
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "is_active": user.is_active,
            "roles": l_as_list,
            "permissions": list(all_permissions)
        }

    return Response(response_data)

@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def change_avatar(request):
    user = request.user
    serializer = UserProfileSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)