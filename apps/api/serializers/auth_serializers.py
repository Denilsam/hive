from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from apps.accounts.models import EmailOTP
from apps.accounts.views import send_verification_otp

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    headline = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'username',
            'account_type',
            'is_verified',
            'profile_completed',
            'avatar_url',
            'headline',
            'created_at',
        ]
        read_only_fields = fields

    def get_full_name(self, obj):
        full_name = f"{obj.first_name} {obj.last_name}".strip()
        return full_name if full_name else (obj.username or obj.email)

    def get_avatar_url(self, obj):
        request = self.context.get('request')
        if hasattr(obj, 'profile') and obj.profile and obj.profile.profile_image:
            try:
                image_url = obj.profile.profile_image.url
                if request is not None and not image_url.startswith(('http://', 'https://')):
                    return request.build_absolute_uri(image_url)
                return image_url
            except Exception:
                return None
        return None

    def get_headline(self, obj):
        if hasattr(obj, 'profile') and obj.profile and obj.profile.headline:
            return obj.profile.headline
        return None


class MobileRegisterSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=30, required=True)
    last_name = serializers.CharField(max_length=30, required=True)
    email = serializers.EmailField(required=True)
    account_type = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        normalized_email = value.strip().lower()
        if User.objects.filter(email__iexact=normalized_email).exists():
            raise serializers.ValidationError("A user with this email address already exists.")
        return normalized_email

    def validate_account_type(self, value):
        val = value.strip().lower()
        if val in ['organization', 'admin']:
            raise serializers.ValidationError("Organization registration is not available on public signup.")
        
        canonical_map = {
            'student': User.AccountType.STUDENT,
            'creator': User.AccountType.CREATOR,
            'freelancer': User.AccountType.FREELANCER,
        }
        if val not in canonical_map:
            raise serializers.ValidationError("Select a valid account type choice (student, creator, freelancer).")
        return canonical_map[val]

    def validate(self, attrs):
        password = attrs.get('password')
        confirm_password = attrs.get('confirm_password')

        if password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        email = validated_data['email']
        password = validated_data['password']
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        account_type = validated_data['account_type']

        enable_otp = getattr(settings, 'ENABLE_EMAIL_OTP', False)

        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            account_type=account_type,
            is_active=not enable_otp,
            is_verified=not enable_otp,
        )
        return user


class MobileLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password')
        request = self.context.get('request')

        user = authenticate(request=request, username=email, password=password)

        if user is None:
            raise serializers.ValidationError({"non_field_errors": ["Invalid email or password."]})

        if not user.is_active and user.is_verified:
            raise serializers.ValidationError({"non_field_errors": ["Your account has been deactivated. Please contact support."]})

        enable_otp = getattr(settings, 'ENABLE_EMAIL_OTP', False)
        if not user.is_verified:
            if enable_otp:
                send_verification_otp(request, user)
                raise serializers.ValidationError({
                    "detail": "Please verify your email with the 6-digit code before continuing.",
                    "requires_otp": True,
                    "email": email
                })
            else:
                user.is_verified = True
                user.is_active = True
                user.save(update_fields=['is_verified', 'is_active'])

        attrs['user'] = user
        return attrs


class MobileOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_otp(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP code must be a 6-digit numeric string.")
        return value

    def validate(self, attrs):
        email = attrs.get('email')
        input_otp = attrs.get('otp')

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": ["No user found with this email address."]})

        if user.is_verified:
            raise serializers.ValidationError({"detail": "Account is already verified. Please log in."})

        active_otp = EmailOTP.objects.filter(user=user, is_used=False).first()
        if not active_otp:
            raise serializers.ValidationError({"otp": ["No active verification code found. Please request a new code."]})

        is_valid, reason = active_otp.verify_otp(input_otp)
        if not is_valid:
            if reason == "TOO_MANY_ATTEMPTS":
                raise serializers.ValidationError({"otp": ["Too many incorrect attempts. Please request a new verification code."]})
            elif reason == "EXPIRED_OR_LIMITED":
                raise serializers.ValidationError({"otp": ["This verification code has expired. Please request a new code."]})
            else:
                raise serializers.ValidationError({"otp": ["Incorrect verification code."]})

        user.is_verified = True
        user.is_active = True
        user.save(update_fields=['is_verified', 'is_active'])

        attrs['user'] = user
        return attrs
