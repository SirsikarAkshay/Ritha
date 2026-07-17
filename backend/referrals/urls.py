from django.urls import path

from .views import ReferralStatsView, ReferralValidateView

urlpatterns = [
    path("validate/", ReferralValidateView.as_view(), name="referral-validate"),
    path("stats/", ReferralStatsView.as_view(), name="referral-stats"),
]
