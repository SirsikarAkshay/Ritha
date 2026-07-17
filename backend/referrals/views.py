from django.db.models import Count, Q
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ReferralCode
from .services import resolve_code


class ReferralValidateView(APIView):
    """Public: does ``?ref=CODE`` point at a live influencer? Lets the signup
    page show "Referred by <name>" before the account exists."""

    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    @extend_schema(summary="Validate a referral code (public)")
    def get(self, request):
        rc = resolve_code(request.query_params.get("code", ""))
        if rc is None:
            return Response({"valid": False})
        return Response({"valid": True, "code": rc.code, "name": rc.name})


class ReferralStatsView(APIView):
    """Owner-only: signups generated per influencer code."""

    permission_classes = [permissions.IsAdminUser]

    @extend_schema(summary="Referral signup counts per code (admin only)")
    def get(self, request):
        codes = ReferralCode.objects.annotate(
            _signups=Count("signups", distinct=True),
            _verified=Count(
                "signups",
                filter=Q(signups__user__is_email_verified=True),
                distinct=True,
            ),
        ).order_by("-_signups", "-created_at")

        results = [
            {
                "code": c.code,
                "name": c.name,
                "is_active": c.is_active,
                "signups": c._signups,
                "verified": c._verified,
                "share_path": c.share_path,
                "created_at": c.created_at,
            }
            for c in codes
        ]
        return Response(
            {
                "results": results,
                "total_codes": len(results),
                "total_signups": sum(r["signups"] for r in results),
            }
        )
