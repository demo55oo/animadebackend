import math, random

from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from django.http import HttpResponse
from django.core.mail import send_mail

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, throttle_classes, permission_classes
from .serializers import UserSerializer
from knox.models import AuthToken
from knox.views import LoginView as KnoxLoginView
from rest_framework.authtoken.models import Token

from django.contrib.auth import login
from django.contrib.auth.models import User

from .models import Profile, CreatedDesign, SavedDesign
from .serializers import UserSerializer, RegisterSerializer, ChangePasswordSerializer, ProfileSerializer, \
    CreatedDesignSerializer, SavedDesignSerializer
from .permissions import OwnerPermission

import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import timedelta
from django.utils import timezone
@csrf_exempt
def text_to_image(request):
    if request.method == 'POST':
        data = json.loads(request.body)  # Convert the JSON data to a Python dictionary

        # Check the user's authentication status
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required."}, status=401)

        # Print or log the user object for debugging
        print("Authenticated User:", request.user)

        # Check the user's design remaining
        user = request.user  # Assuming the user is authenticated
        profile = user.profile  # Assuming the user's profile is accessible through the user object

        # Print or log the designs_remaining value for debugging
        print("Designs Remaining:", profile.designs_remaining)

        if profile.designs_remaining > 0:
            # Replace YOUR_STABLE_DIFFUSION_API_KEY with your actual API key
            headers = {
                "Content-Type": "application/json",
                "Authorization": "YOUR_STABLE_DIFFUSION_API_KEY",
            }

            # Make the request to the Stable Diffusion API using the data received from the frontend
            try:
                response = requests.post('https://stablediffusionapi.com/api/v3/text2img', json=data, headers=headers)
                return JsonResponse(response.json())
            except requests.exceptions.RequestException as e:
                return JsonResponse({"error": str(e)}, status=500)
        else:
            # User's design remaining is zero or less, return an error message
            return JsonResponse({"You need to upgrade your plan to use this feature."})

    return JsonResponse({"error": "Invalid request method."}, status=400)

@csrf_exempt
def image_to_image(request):
    if request.method == 'POST':
        data = json.loads(request.body)  # Convert the JSON data to a Python dictionary

        # Check the user's design remaining
        user = request.user  # Assuming the user is authenticated
        profile = user.profile  # Assuming the user's profile is accessible through the user object

        if profile.designs_remaining > 0:
            # Replace YOUR_STABLE_DIFFUSION_API_KEY with your actual API key
            headers = {
                "Content-Type": "application/json",
                "Authorization": "YOUR_STABLE_DIFFUSION_API_KEY",
            }

            # Make the request to the Stable Diffusion API using the data received from the frontend
            try:
                response = requests.post('https://stablediffusionapi.com/api/v3/img2img', json=data, headers=headers)
                return JsonResponse(response.json())
            except requests.exceptions.RequestException as e:
                return JsonResponse({"error": str(e)}, status=500)
        else:
            # User's design remaining is zero or less, return an error message
            return JsonResponse({"error": "You need to upgrade your plan to use this feature."}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=400)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_subscription_plan(request):
    user = request.user
    data = request.data

    new_subscription_plan = data.get('subscription_plan')
    profile = user.profile

    if new_subscription_plan in dict(Profile.SUBSCRIPTION_CHOICES).keys():
        profile.subscription_plan = new_subscription_plan
        profile.plan_start_date = timezone.now().date()

        if new_subscription_plan == 'Free':
            profile.designs_remaining = 30  # Set the designs_remaining for the Free plan
        elif new_subscription_plan == 'Basic':
            profile.designs_remaining = 50  # Set the designs_remaining for the Basic plan
        elif new_subscription_plan == 'Booster':
            profile.designs_remaining = 100  # Set the designs_remaining for the Booster plan
        elif new_subscription_plan == 'Accelerate':
            profile.designs_remaining = 250  # Set the designs_remaining for the Accelerate plan
        elif new_subscription_plan == 'Professional':
            profile.designs_remaining = 2000  # Set the designs_remaining for the Professional plan
        elif new_subscription_plan == 'Unlimited':
            profile.designs_remaining = 20000  # Unlimited designs for the Unlimited plan

        if profile.subscription_plan != 'Free':
            # Calculate the plan_end_date based on the subscription plan
            plan_duration = 30 if profile.subscription_plan == 'Basic' else 365  # You can adjust the duration as needed
            profile.plan_end_date = profile.plan_start_date + timedelta(days=plan_duration)

        profile.save()

        return Response({"message": "Subscription plan updated successfully!"}, status=status.HTTP_200_OK)
    else:
        return Response({"error": "Invalid subscription plan."}, status=status.HTTP_400_BAD_REQUEST)
class ChangePasswordView(generics.UpdateAPIView):
    """
    An endpoint for changing password.
    """
    serializer_class = ChangePasswordSerializer
    model = User
    permission_classes = (IsAuthenticated,)

    def get_object(self, queryset=None):
        obj = self.request.user
        return obj

    def update(self, request, *args, **kwargs):
        self.object = self.get_object()
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            # Check old password
            if not self.object.check_password(serializer.data.get("old_password")):
                return Response({"old_password": ["Wrong password."]}, status=status.HTTP_400_BAD_REQUEST)
            # set_password also hashes the password that the user will get
            self.object.set_password(serializer.data.get("new_password"))
            self.object.save()
            response = {
                'status': 'success',
                'code': status.HTTP_200_OK,
                'message': 'Password updated successfully',
                'data': []
            }

            return Response(response)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_created_design(request):
    user = request.user
    data = request.data

    serializer = CreatedDesignSerializer(data=data)
    if serializer.is_valid():
        serializer.save(user=user)

        # Update user's remaining designs and plan dates
        profile = user.profile
        if profile.subscription_plan != 'Free':
            profile.designs_remaining -= 1
            profile.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_created_designs(request):
    user = request.user
    created_designs = CreatedDesign.objects.filter(user=user)
    serializer = CreatedDesignSerializer(created_designs, many=True)
    return Response(serializer.data)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_plan_details(request):
    user = request.user
    profile = user.profile

    current_date = date.today()

    # Update the plan_end_date if the current date is beyond the plan's end date
    if profile.plan_end_date and profile.plan_end_date < current_date:
        profile.subscription_plan = 'Free'
        profile.designs_remaining = 30
        profile.plan_start_date = None
        profile.plan_end_date = None
        profile.save()

    data = {
        'subscription_plan': profile.subscription_plan,
        'designs_remaining': profile.designs_remaining,
        'used_designs': F('numberdesigns') - F('designs_remaining')
    }

    return Response(data)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_created_design(request, pk):
    user = request.user
    created_design = get_object_or_404(CreatedDesign, pk=pk, user=user)
    created_design.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# When a new user signs up, create a profile with the default subscription_plan 'Free'
class RegisterAPI(generics.GenericAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Create a profile with default subscription_plan and designs_remaining
        # Profile.objects.create(user=user, subscription_plan='Free', designs_remaining=30)
        profile, created = Profile.objects.get_or_create(user=user, defaults={'subscription_plan': 'Free', 'designs_remaining': 30})

        return Response({
            "user": UserSerializer(user, context=self.get_serializer_context()).data,
            "token": AuthToken.objects.create(user)[1]
        })


class LoginAPI(KnoxLoginView):
    permission_classes = (permissions.AllowAny,)

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        return super(LoginAPI, self).post(request, format=None)


class MainUser(generics.RetrieveAPIView):
    permission_classes = [
        permissions.IsAuthenticated
    ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class CreateProfileAPIView(APIView):
    """
        View to Create User profile if it doesn't already exists
    """
    permission_classes = [
        permissions.IsAuthenticated
    ]

    def post(self, request, *args, **kwargs):
        user = self.request.user
        if not user.profile:
            Profile.objects.create(user=user)
            return Response(status=status.HTTP_201_CREATED)

        return Response(status=status.HTTP_304_NOT_MODIFIED)

from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Profile
from .serializers import ProfileSerializer

class ProfileAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        # Use the currently authenticated user
        return self.request.user.profile

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# class ProfileAPIView(APIView):
#     """
#         View for read, update and delete specific profile
#         get: for anyone
#         put, delete : for profile owners
#     """
#     permission_classes = [
#         permissions.IsAuthenticated, OwnerPermission
#     ]
#
#     def get(self, request, *args, **kwargs):
#         profile = Profile.objects.get(user__id=kwargs['user_id'])
#         profile_serializer = ProfileSerializer(profile)
#         return Response(profile_serializer.data)
#
#     def put(self, request, *args, **kwargs):
#         profile = Profile.objects.get(user__id=kwargs['user_id'])
#         self.check_object_permissions(self.request, profile)
#         serializer = ProfileSerializer(profile, data=request.data)
#         if serializer.is_valid():
#             serializer.save()
#             return Response(serializer.data)
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#
#     def delete(self, request, *args, **kwargs):
#         profile = Profile.objects.get(user__id=kwargs['user_id'])
#         self.check_object_permissions(self.request, profile)
#         profile.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)
#
class ProfileAPIView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        # Use the currently authenticated user
        return self.request.user.profile

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
class CreatedDesignAPIView(APIView):
    """
        View to create and list CreatedDesign
    """
    permission_classes = [
        permissions.IsAuthenticated, OwnerPermission
    ]

    def get(self, request, *args, **kwargs):
        profile = CreatedDesign.objects.all()
        design_serializer = CreatedDesignSerializer(profile)
        return Response(design_serializer.data)

    def post(self, request, *args, **kwargs):
        design_data = request.POST
        serializer = CreatedDesignSerializer(data=design_data)
        # return Response(status=status.HTTP_201_CREATED)
        if serializer.is_valid():
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        return Response(status=status.HTTP_304_NOT_MODIFIED)


class CreatedDesignRUDView(generics.RetrieveUpdateDestroyAPIView):
    """
        Created Design Detail, Update and Delete View
    """
    permission_classes = [
        permissions.IsAuthenticated, permissions.IsAdminUser
    ]
    queryset = CreatedDesign.objects.all()
    serializer_class = CreatedDesignSerializer


class SaveDesignAPIView(APIView):
    """
        View to save design
    """

    def get(self, request, *args, **kwargs):
        user = request.user
        design = CreatedDesign.objects.get(id=kwargs['pk'])
        try:
            saveddesign = get_object_or_404(SavedDesign, design=design)
            saveddesign.status = True
            saveddesign.save()
            return Response({"message": "Design saved successfully!"}, status=status.HTTP_201_CREATED)

        except:
            SavedDesign.objects.create(user=user, design=design, status=True)
            return Response({"message": "Design saved successfully!"}, status=status.HTTP_201_CREATED)


class UnsaveDesignAPIView(APIView):
    """
        View to save design
    """

    def get(self, request, *args, **kwargs):
        design = SavedDesign.objects.get(id=kwargs['pk'])
        design.status = False
        design.save()
        # User.objects.create(user = user, design = design, status = True)
        return Response({"message": "Design Unsaved successfully!"}, status=status.HTTP_201_CREATED)


class UserSavedDesignAPIView(APIView):
    """
        View to list saved designs of requesting user
    """
    permission_classes = [
        permissions.IsAuthenticated, OwnerPermission
    ]

    def get(self, request, *args, **kwargs):
        design = SavedDesign.objects.filter(user=request.user)
        design_serializer = SavedDesignSerializer(design)
        return Response(design_serializer.data)

# class SavedDesignRUDView(generics.RetrieveUpdateDestroyAPIView):
#     """
#         Saved Design Detail, Update and Delete View
#     """
#     permission_classes = [
#         permissions.IsAuthenticated, OwnerPermission
#     ]
#     queryset = SavedDesign.objects.all()
#     serializer_class = SavedDesignSerializer
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decrease_designs_remaining(request):
    # Get the user associated with the authenticated token
    try:
        user = Token.objects.get(key=request.auth.key).user
    except Token.DoesNotExist:
        return Response({"error": "Authentication token not found."}, status=status.HTTP_401_UNAUTHORIZED)

    try:
        user_profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Get the value to subtract from designs_remaining from the request data
    try:
        decrement_value = int(request.data.get('decrement_value'))
    except (ValueError, TypeError):
        return Response({"error": "Invalid decrement value."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the user has an unlimited subscription plan
    if user_profile.subscription_plan == 'Unlimited':
        return Response({"error": "Cannot decrease designs for unlimited plan."}, status=status.HTTP_400_BAD_REQUEST)

    # Calculate the new designs_remaining value
    new_designs_remaining = user_profile.designs_remaining - decrement_value

    # Ensure that the new value is not negative
    if new_designs_remaining < 0:
        return Response({"error": "New designs_remaining value cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)

    # Update the user's profile with the new designs_remaining value
    user_profile.designs_remaining = new_designs_remaining
    user_profile.save()

    # Serialize and return the updated profile
    serializer = ProfileSerializer(user_profile)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decrease_designs_remaining(request):
    # Get the authenticated user from the request
    user = request.user

    try:
        user_profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        return Response({"error": "User profile not found."}, status=status.HTTP_404_NOT_FOUND)

    # Get the value to subtract from designs_remaining from the request data
    try:
        decrement_value = int(request.data.get('decrement_value'))
    except (ValueError, TypeError):
        return Response({"error": "Invalid decrement value."}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the user has an unlimited subscription plan
    if user_profile.subscription_plan == 'Unlimited':
        return Response({"error": "Cannot decrease designs for unlimited plan."}, status=status.HTTP_400_BAD_REQUEST)

    # Calculate the new designs_remaining value
    new_designs_remaining = user_profile.designs_remaining - decrement_value

    # Ensure that the new value is not negative
    if new_designs_remaining < 0:
        return Response({"error": "New designs_remaining value cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)

    # Update the user's profile with the new designs_remaining value
    user_profile.designs_remaining = new_designs_remaining
    user_profile.save()

    # Serialize and return the updated profile
    serializer = ProfileSerializer(user_profile)
    return Response(serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_subscription_plan(request):
    user = request.user
    data = request.data

    new_subscription_plan = data.get('subscription_plan')
    profile = user.profile

    # Define the mapping of subscription plans to designs_remaining values
    subscription_plan_mapping = {
        'Free': 30,
        'Basic': 50,
        'Booster': 250,
        'Accelerate': 850,
        'Professional': 2000,
        'Unlimited': 2000,
    }

    if new_subscription_plan not in subscription_plan_mapping:
        return Response({"error": "Invalid subscription plan."}, status=status.HTTP_400_BAD_REQUEST)

    # Update the user's subscription plan
    profile.subscription_plan = new_subscription_plan
    profile.designs_remaining = subscription_plan_mapping[new_subscription_plan]

    if new_subscription_plan != 'Free':
        # Calculate the plan_end_date based on the subscription plan (adjust the duration as needed)
        plan_duration = 30 if new_subscription_plan == 'Basic' else 365
        profile.plan_start_date = timezone.now().date()
        profile.plan_end_date = profile.plan_start_date + timedelta(days=plan_duration)

    profile.save()

    # Serialize and return the updated profile
    serializer = ProfileSerializer(profile)
    return Response(serializer.data, status=status.HTTP_200_OK)

