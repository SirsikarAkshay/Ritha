"""
Project-wide Django signals.
Registered in ArokahConfig.ready().
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='auth_app.User')
def create_sustainability_profile(sender, instance, created, **kwargs):
    """Auto-create a UserSustainabilityProfile whenever a new User is saved."""
    if created:
        from sustainability.models import UserSustainabilityProfile
        UserSustainabilityProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender='outfits.OutfitRecommendation')
def handle_outfit_feedback(sender, instance, created, **kwargs):
    """
    When an OutfitRecommendation is accepted:
      - Increment times_worn on each linked ClothingItem
      - Award 'wear_again' sustainability points (10 pts per item)
      - Update the UserSustainabilityProfile totals
    """
    # Guard: only award points once per recommendation acceptance
    if instance.accepted is not True:
        return
    # Re-read from DB to get the authoritative points_awarded value
    fresh = type(instance).objects.values_list('points_awarded', flat=True).get(pk=instance.pk)
    if fresh:
        return

    from outfits.models import OutfitItem
    from sustainability.models import SustainabilityLog, UserSustainabilityProfile
    import datetime

    items = OutfitItem.objects.filter(outfit=instance).select_related('clothing_item')

    for oi in items:
        item = oi.clothing_item
        item.times_worn += 1
        item.last_worn   = datetime.date.today()
        item.save(update_fields=['times_worn', 'last_worn'])

        SustainabilityLog.objects.create(
            user=instance.user,
            action='wear_again',
            co2_saved_kg=0.050,   # rough estimate: ~50g CO2 saved per re-wear vs. new garment
            points=10,
            notes=f'Re-wore: {item.name}',
        )

    # Recalculate totals
    profile, _ = UserSustainabilityProfile.objects.get_or_create(user=instance.user)
    from django.db.models import Sum
    agg = SustainabilityLog.objects.filter(user=instance.user).aggregate(
        total_pts=Sum('points'),
        total_co2=Sum('co2_saved_kg'),
    )
    profile.total_points       = agg['total_pts'] or 0
    profile.total_co2_saved_kg = agg['total_co2'] or 0
    # Wear-again streak: consecutive days with at least one re-wear
    import datetime
    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    wore_yesterday = SustainabilityLog.objects.filter(
        user=instance.user,
        action='wear_again',
        created_at__date=yesterday,
    ).exists()
    if wore_yesterday:
        profile.wear_again_streak += 1
    else:
        # Check if already logged today (first wear of the day resets/starts streak)
        wore_today_before = SustainabilityLog.objects.filter(
            user=instance.user,
            action='wear_again',
            created_at__date=datetime.date.today(),
        ).count()
        if wore_today_before <= len(items):  # just created, so count the ones we just made
            profile.wear_again_streak = max(1, profile.wear_again_streak)
    profile.save()

    # Update style profile with accepted item preferences
    from outfits.models import OutfitItem
    accepted_categories = list(
        OutfitItem.objects.filter(outfit=instance)
        .values_list('clothing_item__category', flat=True)
    )
    accepted_formalities = list(
        OutfitItem.objects.filter(outfit=instance)
        .values_list('clothing_item__formality', flat=True)
    )
    if accepted_categories:
        style = instance.user.style_profile or {}
        cat_counts  = style.get('accepted_categories', {})
        form_counts = style.get('accepted_formalities', {})
        for cat in accepted_categories:
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
        for form in accepted_formalities:
            form_counts[form] = form_counts.get(form, 0) + 1
        style['accepted_categories']  = cat_counts
        style['accepted_formalities'] = form_counts
        style['total_accepted']       = style.get('total_accepted', 0) + 1
        type(instance.user).objects.filter(pk=instance.user.pk).update(style_profile=style)

    # Mark as processed — update() skips post_save signal, preventing recursion
    type(instance).objects.filter(pk=instance.pk).update(points_awarded=True)
    # Also update in-memory instance so subsequent saves in the same request are guarded
    instance.points_awarded = True
