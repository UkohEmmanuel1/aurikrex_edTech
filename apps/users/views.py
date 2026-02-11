from rest_framework import status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from .serializers import (
    UserSignupSerializer, VerifyOTPSerializer, ResendOTPSerializer, 
    LoginSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)
from .models import OneTimePassword, Profile
import random
from django.utils import timezone
from rest_framework.permissions import AllowAny  

# --- NEW IMPORTS FOR GOOGLE AUTH ---
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

# Helper: Generate Tokens manually
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'role': user.profile.role,
        'email': user.email
    }

# --- 1. Signup View ---
class SignupView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate OTP
            otp_code = str(random.randint(100000, 999999))
            OneTimePassword.objects.update_or_create(user=user, defaults={'code': otp_code})

            # Send Email
            email_subject = "Verify your Aurikrex Account"
            email_body = f"Hello,\n\nYour verification code is: {otp_code}\n\nThis code expires in 5 minutes."
            
            try:
                send_mail(
                    subject=email_subject,
                    message=email_body,
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
            except Exception as e:
                user.delete()
                return Response({"error": "Failed to send email. Please check your address."}, status=500)

            return Response({
                "message": "Account created. Check your email for the OTP.",
                "email": user.email
            }, status=status.HTTP_201_CREATED)
        
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
                        fail_silently=False, 
                    )
                except Exception as e:
                    print(f"Resend email failed: {e}")

                return Response({"message": "New OTP sent to your email."}, status=status.HTTP_200_OK)

            except User.DoesNotExist:
                return Response({"message": "If an account exists, a new OTP was sent."}, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 4. Login View ---
class LoginView(views.APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            user = authenticate(username=email, password=password)

            if user:
                if not user.is_active:
                    return Response({"error": "Account not verified. Please verify OTP first."}, status=status.HTTP_403_FORBIDDEN)
                
                tokens = get_tokens_for_user(user)
                return Response(tokens, status=status.HTTP_200_OK)
            else:
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
                        fail_silently=False,
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
    # client_class = OAuth2Client  # Uncomment if your frontend uses auth code instead of access token
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