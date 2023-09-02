from rest_framework import serializers
from rest_framework import status
from django.contrib.auth.models import User
from django import forms
from .models import Profile, CreatedDesign, SavedDesign

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for password change endpoint.
    """
    model = User
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)



class UserSerializer(serializers.ModelSerializer):
  class Meta:
    model = User
    fields = ["id", "username", "email"]

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = "__all__"

class CreatedDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreatedDesign
        fields = "__all__"

class SavedDesignSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedDesign
        fields = "__all__"

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(validated_data['username'], validated_data['email'], validated_data['password'])
        return user

