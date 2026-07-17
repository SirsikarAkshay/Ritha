from django.contrib import admin
from django.db.models import Count, Q

from .models import ReferralCode, ReferralSignup


@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "is_active", "signups_col", "verified_col", "share_path", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["code", "name", "note"]
    readonly_fields = ["created_at", "share_path"]
    ordering = ["-created_at"]
    fields = ["code", "name", "note", "is_active", "share_path", "created_at"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(
                _signups=Count("signups", distinct=True),
                _verified=Count(
                    "signups", filter=Q(signups__user__is_email_verified=True), distinct=True
                ),
            )
        )

    @admin.display(description="Signups", ordering="_signups")
    def signups_col(self, obj):
        return obj._signups

    @admin.display(description="Verified", ordering="_verified")
    def verified_col(self, obj):
        return obj._verified


@admin.register(ReferralSignup)
class ReferralSignupAdmin(admin.ModelAdmin):
    list_display = ["user", "code", "created_at"]
    list_filter = ["code", "created_at"]
    search_fields = ["user__email", "code__code", "code__name"]
    ordering = ["-created_at"]
    autocomplete_fields = ["user", "code"]
