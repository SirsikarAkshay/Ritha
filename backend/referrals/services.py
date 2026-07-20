from .models import ReferralCode, ReferralSignup, normalize_code


def resolve_code(code_str: str):
    """Return the active ReferralCode for a raw code string, or None."""
    code_str = normalize_code(code_str)
    if not code_str:
        return None
    return ReferralCode.objects.filter(code=code_str, is_active=True).first()


def attribute_signup(user, code_str: str):
    """Attach a newly registered user to an active referral code.

    Idempotent per user (OneToOne) — the first code a user arrives with wins,
    later ones are ignored. Returns the ReferralSignup, or None if the code was
    blank/unknown/inactive.
    """
    rc = resolve_code(code_str)
    if rc is None:
        return None
    signup, _ = ReferralSignup.objects.get_or_create(user=user, defaults={"code": rc})
    return signup
