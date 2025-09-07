import random
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from .models import *
from .serializers import *
from .sendOTPS import sendSMS
import jwt
import datetime
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

def get_user_from_token(token):
    
    print("11111111111")
    jwt_auth = JWTAuthentication()
    validated_token = jwt_auth.get_validated_token(token)  # Validate and decode
    user = jwt_auth.get_user(validated_token)  # Get user instance
    return user

# JWT token generator
def get_tokens_for_user(user):
      # Set desired lifetimes
    access_lifetime = timedelta(days=365*100)
    refresh_lifetime = timedelta(days=365*110)

    refresh = RefreshToken.for_user(user)
    refresh.access_token.set_exp(from_time=None, lifetime=access_lifetime)
    refresh.set_exp(from_time=None, lifetime=refresh_lifetime)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }


@api_view(['POST'])
def generateOTP(request):
    """Step 1: Generate OTP for signup"""
    phone = request.data.get('phone_number')

    # if Users.objects.filter(phone_number=phone).exists():
    #     return Response(
    #         {"status": "failed", "message": "Number already registered"},
    #         status=status.HTTP_400_BAD_REQUEST
    #     )

    otp = random.randint(100000, 999999)
    print(otp)
    # Save OTP in DB (delete old if exists)
    OTP.objects.filter(phone_number=phone).delete()
    OTP.objects.create(phone_number=phone, otp=str(otp))

    sendSMS("+" + str(phone), f'Your OTP is {otp}')
    return Response({"status": "success", "otp": otp}, status=status.HTTP_200_OK)


@api_view(['POST'])
def verifyOTP(request):
    """Step 2: Verify OTP"""
    phone = request.data.get('phone_number')
    otp = request.data.get('otp')

    try:
        otp_entry = OTP.objects.get(phone_number=phone)
    except OTP.DoesNotExist:
        return Response({"status": "failed", "message": "OTP not found"}, status=status.HTTP_404_NOT_FOUND)

    # Check expiry (5 minutes)
    if timezone.now() > otp_entry.created_at + timedelta(minutes=5):
        otp_entry.delete()
        return Response({"status": "failed", "message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

    if otp_entry.otp == str(otp):
        return Response({"status": "success", "message": "OTP verified"}, status=status.HTTP_200_OK)
    else:
        return Response({"status": "failed", "message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def createUser(request):
    """Step 3: Create user + profile after OTP verification"""
    phone = request.data.get('phone_number')
    username = request.data.get('username')   # ✅ required by Users model
    password = request.data.get('password')
    # username = request.data.get('username')
    # Profile fields
    full_name = request.data.get('name')
    gender = request.data.get('gender')
    birthdate = request.data.get('birthdate')  # Expecting "YYYY-MM-DD"

    if Users.objects.filter(phone_number=phone).exists():
        return Response({"status": "failed", "message": "User already exists"}, status=status.HTTP_400_BAD_REQUEST)

    if Users.objects.filter(username = username).exists():
        return Response({"status": "failed", "message": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

    # Check OTP
    try:
        otp_entry = OTP.objects.get(phone_number=phone)
    except OTP.DoesNotExist:
        return Response({"status": "failed", "message": "OTP not verified"}, status=status.HTTP_400_BAD_REQUEST)

    try :
        # ✅ Create user
        user = Users.objects.create_user(
            phone_number=phone,
            password=password,
            username = username,
        )

        # ✅ Create profile
        UserProfile.objects.create(
            user=user,
            full_name=full_name,
            gender=gender,
            birthdate=birthdate
        )

    except Exception as e:
        print(e)
        return Response({"status": "failed", "message": "error"}, status=status.HTTP_400_BAD_REQUEST)


    # Delete OTP entry
    otp_entry.delete()

    # Generate JWT tokens
    tokens = get_tokens_for_user(user)
    print(tokens)
    return Response({
        "status": "success",
        "message": "User created successfully",
        "tokens": tokens
    }, status=status.HTTP_201_CREATED)

# @csrf_exempt
@api_view(['POST'])
def addInterests(request):
    try:
        accessToken = request.data.get('accessToken')
        if not accessToken:
            return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_from_token(accessToken)
        if not user:
            return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

        # Ensure names is a list of dicts
        names = request.data.get('name')
        if not names:
            return Response({"error": "No interests provided"}, status=status.HTTP_400_BAD_REQUEST)

        if isinstance(names, str):
            names = [names]

        # Convert to list of dicts for serializer
        data = [{"name": name} for name in names]

        serializer = AddInterestSerializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            # Add to user's profile
            profile = user.profile
            interests = Interest.objects.filter(name__in=names)
            profile.interests.add(*interests)
            return Response({
                "message": "Interests added successfully",
                "interests": serializer.data
            }, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        print("Error in addInterests:", e)
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
def getInterest(request):
    try:
        accessToken = request.data.get('accessToken')
        if not accessToken:
            return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_from_token(accessToken)
        if not user:
            return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

        # Get the user's profile
        try:
            profile = user.profile  # OneToOne relation
        except UserProfile.DoesNotExist:
            return Response({"error": "User profile not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get all interests for this user
        interests = profile.interests.all()
        serializer = InterestSerializer(interests, many=True)

        return Response({"interests": serializer.data}, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def login(request):
    try:
        accessToken = request.data.get('accessToken')
        if not accessToken:
            return Response({"error": "Access token required"}, status=status.HTTP_400_BAD_REQUEST)

        user = get_user_from_token(accessToken)
        if not user:
            return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

        print("valid session")
        return Response({"error": "Valid Session"}, status=status.HTTP_200_OK)

    except :
        return Response({"error": "Invalid or expired access token"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
def loginByMobile(request):
    """Step 4: Login with phone + password"""
    phone = request.data.get('phone_number')
    password = request.data.get('password')

    try:
        user = Users.objects.get(phone_number=phone)
    except Users.DoesNotExist:
        return Response({"status": "failed", "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    if check_password(password, user.password):
        tokens = get_tokens_for_user(user)
        return Response({
            "status": "success",
            "message": "Login successful",
            "tokens": tokens,
            "username" : user.username
        }, status=status.HTTP_200_OK)
    else:
        return Response({"status": "failed", "message": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def refreshToken(request):
    """Step 5: Refresh JWT access token"""
    refresh = request.data.get('refresh')
    try:
        refresh_token = RefreshToken(refresh)
        access_token = str(refresh_token.access_token)
        return Response({"status": "success", "access": access_token}, status=status.HTTP_200_OK)
    except Exception:
        return Response({"status": "failed", "message": "Invalid refresh token"}, status=status.HTTP_400_BAD_REQUEST)


