from django.shortcuts import render
from Users.models import *
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import *
from Users.serializers import *
import jwt
import datetime
from rest_framework_simplejwt.authentication import JWTAuthentication
from .driveUpload import upload_to_drive
import io
from googleapiclient.http import MediaIoBaseUpload
from .serializers import * 
from .models import *

def get_user_from_token(token):
    
    print("11111111111")
    jwt_auth = JWTAuthentication()
    validated_token = jwt_auth.get_validated_token(token)  # Validate and decode
    user = jwt_auth.get_user(validated_token)  # Get user instance
    return user


@api_view(['POST'])
def profilePhoto(request):
  
    try:
        access_token = request.data.get("access_token")
        if not access_token:
            return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)

        # Decode token and get user_id
        user = get_user_from_token(access_token)

        if not user:
            return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)


        # Fetch profile photos
        photos = ProfilePhoto.objects.filter(user=user).order_by("position")

        if not photos.exists():
            return Response({"photo": ""}, status=status.HTTP_200_OK)

        # You can return all photos or just the first one
        serializer = ProfilePhotoSerializer(photos, many=True)

        return Response({
            "photo": serializer.data[0]['url'],   # just first photo
            "photos": serializer.data             # all photos
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(e)
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def updatePhoto(request):
    access_token = request.data.get("access_token")
    print(1)
    photo = request.FILES.get("photo")

    if not access_token or not photo:
        return Response({"error": "access_token and photo are required"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_user_from_token(access_token)

    if not user:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        # ✅ Upload to Google Drive
        print(2)
        filename = f"{user.phone_number}.jpg"
        file_obj = io.BytesIO(photo.read())  # keep in memory
        print(33)
        photo_url = upload_to_drive(
            file_obj,
            filename,
            photo.content_type,
            "1EfzI9DfMDO-n24-c_XgKElxQJVSWR3XR"
        )
        print(4)

        # ✅ Save in DB
        profile_photo = ProfilePhoto.objects.create(
            user=user,
            url=photo_url,
            position=0
        )
        print(6)
        print(ProfilePhotoSerializer(profile_photo).data)
        return Response(ProfilePhotoSerializer(profile_photo).data, status=status.HTTP_200_OK)

    except Exception as e:
        print("Error in updatePhoto:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def getProfileData(request):
    access_token = request.data.get("access_token")

    if not access_token :
        return Response({"error": "access_token required"}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        # ✅ Decode JWT access token
        user = get_user_from_token(access_token)

        if not user:
            return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

        profile = UserProfile.objects.filter(user=user).first()
        if not profile:
            return Response({"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND)

        serializer = UserProfileSerializer(profile)

        return Response({
            "name": profile.full_name,
            "gender": profile.gender,
            "dob": profile.birthdate.strftime("%d %b %Y"),
            "interests": [i.name for i in profile.interests.all()],
        }, status=status.HTTP_200_OK)

    except jwt.ExpiredSignatureError:
        return Response({"error": "Token expired"}, status=status.HTTP_401_UNAUTHORIZED)
    except jwt.InvalidTokenError:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def addInterest(request):
    """
    Add a new interest for the logged-in user.
    Request: { "access_token": "xxx", "interest": "Football" }
    """
    access_token = request.data.get("access_token")
    interest_name = request.data.get("interest")

    if not access_token or not interest_name:
        return Response({"error": "access_token and interest are required"},
                        status=status.HTTP_400_BAD_REQUEST)

    user = get_user_from_token(access_token)

    if not user:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        
        profile, created = UserProfile.objects.get_or_create(user=user)

        # ✅ Get or create interest
        interest, created = Interest.objects.get_or_create(name=interest_name)

        # ✅ Add interest to profile
        profile.interests.add(interest)

        # ✅ Return updated list
        interests = profile.interests.all()
        serializer = InterestSerializer(interests, many=True)
        return Response({
            "message": "Interest added successfully",
            "interests": serializer.data
        }, status=status.HTTP_200_OK)

    except Users.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["POST"])
def removeInterest(request):
    access_token = request.data.get("access_token")
    interest_name = request.data.get("interest")

    if not access_token or not interest_name:
        return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_user_from_token(access_token)

    if not user:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

   
    profile = user.profile
   
    try:
        interest = Interest.objects.get(name=interest_name)
        profile.interests.remove(interest)  # ✅ Remove relation
    except Interest.DoesNotExist:
        return Response({"error": "Interest not found"}, status=status.HTTP_404_NOT_FOUND)

    profile.save()

    # ✅ Return updated interests
    interests = profile.interests.all()
    serializer = InterestSerializer(interests, many=True)
    return Response({"interests": serializer.data}, status=status.HTTP_200_OK)

@api_view(["POST"])
def getProfiles(request):
    access_token = request.data.get("access_token")
    user = get_user_from_token(access_token)
    if not user:
        return Response({"error": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

    users = Users.objects.exclude(id=user.id)
    result = [UserListSerializer(u, context={"current_user": user}).data for u in users]
    return Response(result, status=status.HTTP_200_OK)
    

@api_view(["POST"])
def connect(request):
    access_token = request.data.get("access_token")
    to_user_id = request.data.get("to_user_id")
    to_username = request.data.get("to_username")

    if not access_token or (not to_user_id and not to_username):
        return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_user_from_token(access_token)
    if not user:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

    # Get target user
    try:
        if to_user_id:
            target_user = Users.objects.get(id=to_user_id)
        else:
            target_user = Users.objects.get(username=to_username)
    except Users.DoesNotExist:
        return Response({"error": "Target user not found"}, status=status.HTTP_404_NOT_FOUND)

    if user.id == target_user.id:
        return Response({"error": "You cannot connect with yourself"}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Check if connection already exists
    if Connection.objects.filter(user=user, connected_user=target_user).exists() or \
       Connection.objects.filter(user=target_user, connected_user=user).exists():
        return Response({"message": "Already connected"}, status=status.HTTP_200_OK)

    # ✅ Check if target already sent a request → Accept it
    existing_request = ConnectionRequest.objects.filter(from_user=target_user, to_user=user, status="pending").first()
    if existing_request:
        existing_request.status = "accepted"
        existing_request.save()

        # Create mutual connection
        Connection.objects.get_or_create(user=user, connected_user=target_user)
        Connection.objects.get_or_create(user=target_user, connected_user=user)

        return Response({"message": "Connection accepted"}, status=status.HTTP_200_OK)

    # ✅ Otherwise create a new request
    request_obj, created = ConnectionRequest.objects.get_or_create(
        from_user=user,
        to_user=target_user,
        defaults={"status": "pending"},
    )
    if not created:
        return Response({"message": f"Request already {request_obj.status}"}, status=status.HTTP_200_OK)

    serializer = ConnectionRequestSerializer(request_obj)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
def accept(request):
    access_token = request.data.get("access_token")
    to_user_id = request.data.get("to_user_id")
    to_username = request.data.get("to_username")

    if not access_token or (not to_user_id and not to_username):
        return Response({"error": "Missing fields"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_user_from_token(access_token)  # ✅ current logged-in user
    if not user:
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        # find the sender of the request (who originally sent to current user)
        if to_user_id:
            from_user = Users.objects.get(id=to_user_id)
        else:
            from_user = Users.objects.get(username=to_username)
    except Users.DoesNotExist:
        return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    try:
        # find request where from_user → user
        conn_request = ConnectionRequest.objects.get(
            from_user=from_user, to_user=user, status="pending"
        )
    except ConnectionRequest.DoesNotExist:
        return Response({"error": "No pending request found"}, status=status.HTTP_404_NOT_FOUND)

    # ✅ update status
    conn_request.status = "accepted"
    conn_request.save()

    # ✅ create mutual connection
    Connection.objects.get_or_create(user=user, connected_user=from_user)
    Connection.objects.get_or_create(user=from_user, connected_user=user)

    from Chat.utils import get_or_create_thread
    get_or_create_thread(conn_request.from_user, conn_request.to_user)
    
    serializer = ConnectionRequestSerializer(conn_request)
    return Response(
        {"message": "Request accepted", "request": serializer.data},
        status=status.HTTP_200_OK,
    )
