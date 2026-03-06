from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework.permissions import AllowAny  
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
import random

from .serializers import (
    UserSignupSerializer, VerifyOTPSerializer, ResendOTPSerializer, 
    LoginSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from .models import OneTimePassword, Profile

User = get_user_model()

# --- NEW IMPORTS FOR GOOGLE AUTH ---
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView

# ==========================================
# HELPER FUNCTIONS
# ==========================================

# Helper: Generate Tokens manually (FIXED for missing Profiles)
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    
    # Safely check if the user has a profile to prevent 500 crashes
    if hasattr(user, 'profile') and user.profile is not None:
        role = user.profile.role
    else:
        role = 'student'  # Fallback role if no profile exists
        
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'role': role,
        'email': user.email
    }

# ==========================================
# AUTHENTICATION VIEWS
# ==========================================

# --- 1. Signup View (FIXED DB Timeout) ---
class SignupView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)

        # 1. Pre-check for existing user
        email = request.data.get('email')
        if email and User.objects.filter(email=email).exists():
            return Response({
                "error": "This email is already registered. Please login.",
                "status_code": 400
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if serializer.is_valid():
            try:
                # --- DATABASE BLOCK (Fast & Locked) ---
                with transaction.atomic():
                    # Save user
                    user = serializer.save()

                    # Generate OTP
                    otp_code = str(random.randint(100000, 999999))
                    OneTimePassword.objects.update_or_create(
                        user=user, 
                        defaults={'code': otp_code}
                    )
                # --- TRANSACTION ENDS HERE ---

                # --- EMAIL BLOCK (Safe from DB timeouts) ---
                email_subject = "Verify your Aurikrex Account"
                email_body = f"Hello,\n\nYour verification code is: {otp_code}\n\nThis code expires in 5 minutes."
                
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=True,  # Prevents 10060 error crash
                )

                return Response({
                    "message": "Account created. Check your email for the OTP.",
                    "email": user.email
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                # If anything inside transaction.atomic fails, the user is NOT created
                return Response({
                    "error": "Failed to complete signup. Please try again later.",
                    "details": str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# --- 2. Verify OTP View ---
class VerifyOTPView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']

            try:
                user = User.objects.get(email=email)
                otp_record = OneTimePassword.objects.get(user=user)

                if otp_record.code == otp and otp_record.is_valid():
                    user.is_active = True
                    user.save()
                    otp_record.delete()
                    return Response({"message": "Email verified! You can now login."}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

            except (User.DoesNotExist, OneTimePassword.DoesNotExist):
                return Response({"error": "Invalid User or OTP"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 3. Resend OTP View ---
class ResendOTPView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResendOTPSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']

            try:
                user = User.objects.get(email=email)

                if user.is_active:
                    return Response({"message": "Account is already verified. Please login."}, status=status.HTTP_200_OK)

                # Generate NEW OTP
                otp_code = str(random.randint(100000, 999999))
                
                OneTimePassword.objects.update_or_create(
                    user=user, 
                    defaults={'code': otp_code, 'created_at': timezone.now()} 
                )

                # Send Email
                print(f"\n RESEND DEBUG OTP FOR {user.email}: {otp_code} \n") 
                
                email_subject = "Resend: Verify your Aurikrex Account"
                email_body = f"Hello,\n\nYour new verification code is: {otp_code}\n\nThis code expires in 5 minutes."
                
                try:
                    send_mail(
                        subject=email_subject,
                        message=email_body,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=True, 
                    )
                except Exception as e:
                    print(f"Resend email failed: {e}")

                return Response({"message": "New OTP sent to your email."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"message": "If an account exists, a new OTP was sent."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
# --- 4. Login View (FIXED Email Auth) ---
class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            try:
                # 1. Find the user by their email
                user = User.objects.get(email=email)
                
                # 2. Check if the password matches the hashed one in the DB
                if user.check_password(password):
                    
                    # 3. Check if they have verified their OTP
                    if not user.is_active:
                        return Response({"error": "Account not verified. Please verify OTP first."}, status=status.HTTP_403_FORBIDDEN)
                    
                    # 4. Success! Generate tokens
                    tokens = get_tokens_for_user(user)
                    return Response(tokens, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)
                    
            except User.DoesNotExist:
                # If the email isn't in the database at all
                return Response({"error": "Invalid email or password"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 6. Request Password Reset View ---
class PasswordResetRequestView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                
                otp_code = str(random.randint(100000, 999999))
                OneTimePassword.objects.update_or_create(
                    user=user, 
                    defaults={'code': otp_code, 'created_at': timezone.now()}
                )

                print(f"\n PASSWORD RESET OTP FOR {user.email}: {otp_code} \n")
                
                email_subject = "Reset your Aurikrex Password"
                email_body = f"Hello,\n\nYour password reset code is: {otp_code}\n\nIf you did not request this, please ignore this email. This code expires in 5 minutes."
                
                try:
                    send_mail(
                        subject=email_subject,
                        message=email_body,
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Password reset email failed: {e}")

                return Response({"message": "If an account exists, a reset code was sent."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"message": "If an account exists, a reset code was sent."}, status=status.HTTP_200_OK)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 7. Confirm Password Reset View ---
class PasswordResetConfirmView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(email=email)
                otp_record = OneTimePassword.objects.get(user=user)

                if otp_record.code == otp and otp_record.is_valid():
                    user.set_password(new_password)
                    user.save()
                    otp_record.delete()
                    return Response({"message": "Password has been reset successfully. You can now log in."}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": "Invalid or expired OTP"}, status=status.HTTP_400_BAD_REQUEST)

            except (User.DoesNotExist, OneTimePassword.DoesNotExist):
                return Response({"error": "Invalid User or OTP"}, status=status.HTTP_404_NOT_FOUND)
                
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 

# --- 8. Google Login View ---
class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    permission_classes = [AllowAny]
    
    def get_response(self):
        """
        Customizing the response to return our custom token format and role.
        """
        response = super().get_response()
        user = self.user
        
        # Ensure a Profile exists for users created via Google
        Profile.objects.get_or_create(user=user, defaults={'role': 'student'})
        
        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)