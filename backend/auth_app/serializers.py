from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={"min_length": "Password must be at least 8 characters."},
    )
    # Optional influencer/referral code from a ?ref=CODE share link. Not a User
    # field — resolved to a ReferralSignup after the account is created.
    referral_code = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=32
    )

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "timezone", "referral_code"]
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
            "timezone": {"required": False, "allow_blank": True},
        }

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email address already exists. "
                'Try logging in, or use "Forgot password?" to reset your password.'
            )
        return value

    def create(self, validated_data):
        referral_code = validated_data.pop("referral_code", "")
        validated_data["email"] = validated_data["email"].lower()
        # Don't auto-verify — user must verify via email link
        user = User.objects.create_user(**validated_data)
        user.is_email_verified = False
        user.save()
        if referral_code:
            # Best-effort attribution — never block signup on a bad code.
            from referrals.services import attribute_signup

            try:
                attribute_signup(user, referral_code)
            except Exception:
                pass
        return user


class UserSerializer(serializers.ModelSerializer):
    has_completed_onboarding = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "timezone",
            "gender",
            "location_name",
            "location_lat",
            "location_lon",
            "push_notifications",
            "google_calendar_connected",
            "apple_calendar_connected",
            "outlook_calendar_connected",
            "style_profile",
            "is_email_verified",
            "has_completed_onboarding",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "email",
            "is_email_verified",
            "created_at",
            "has_completed_onboarding",
            "google_calendar_connected",
            "apple_calendar_connected",
            "outlook_calendar_connected",
        ]

    def get_has_completed_onboarding(self, obj) -> bool:
        return hasattr(obj, "starter_pack_application")


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_current_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate_new_password(self, value):
        from django.contrib.auth.password_validation import validate_password

        validate_password(value)
        return value
