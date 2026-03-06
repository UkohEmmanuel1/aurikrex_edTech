from rest_framework import serializers
# FIX 1: Changed 'vaildators' to 'validators'
from rest_framework.validators import UniqueValidator 
from django.contrib.auth.models import User
from .models import OneTimePassword, Profile
from django.contrib.auth import authenticate

# --- 1. Signup: Handles User + Role ---
class UserSignupSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        # FIX 2: Changed 'validatiors' to 'validators'
        validators=[UniqueValidator(queryset=User.objects.all(), message="This email is already registered.")]
    )
    password = serializers.CharField(write_only=True, min_length=6)
    role = serializers.CharField(write_only=True, required=False)  # 'student' or 'teacher'

    class Meta:
        model = User
        fields = ['email', 'password', 'role']

    def create(self, validated_data):
        role = validated_data.pop('role', 'student') # Default to student if not sent
        email = validated_data['email']
        password = validated_data['password']

        # Since we use UniqueValidator above, we technically don't need this check here,
        # but it doesn't hurt as a backup!
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError({"email": "This email is already registered."})
            
        # Create User (Inactive until verified)
        # Using email as username is standard for email-based login
        user = User.objects.create_user(username=email, email=email, password=password)
        user.is_active = False 
        user.save()

        # Create Profile
        Profile.objects.create(user=user, role=role)

        return user


# --- 2. Verify OTP ---
class VerifyOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

#------3. Resend OTP -----
class ResendOTPSerializer(serializers.Serializer):
    email = serializers.EmailField()

# --- 4. Login ---
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

# --- 5. Password Reset Request Serializer ---
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

# --- 6. Password Reset Confirm Serializer ---
class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True, min_length=8)