"""
Seed a fully-populated demo account for screenshots, demos, and influencer
first-impressions — so the app shows a vibrant wardrobe/trip/history instead of
empty states.

Usage:
    python manage.py seed_demo_user                         # idempotent upsert
    python manage.py seed_demo_user --reset                 # wipe the demo user's data and rebuild
    python manage.py seed_demo_user --email me@x.com --password secret123

Creates: a verified, onboarding-complete user with ~12 wardrobe items, an
upcoming trip + packing checklist, a week of accepted daily-look history, and
sustainability stats. Safe to re-run; keyed by email.
"""

import datetime
import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from itinerary.models import PackingChecklistItem, Trip
from outfits.models import OutfitItem, OutfitRecommendation
from sustainability.models import SustainabilityLog, UserSustainabilityProfile

from wardrobe.models import ClothingItem, RegionCluster, StarterPackApplication

User = get_user_model()

# (name, category, formality, season, colors, material, weight_grams, brand, tags)
DEMO_WARDROBE = [
    ("White Oxford Shirt", "top", "smart", "all", ["white"], "cotton", 180, "Uniqlo", ["office", "travel"]),
    ("Navy Merino Sweater", "top", "casual_smart", "winter", ["navy"], "merino", 300, "Everlane", ["office"]),
    ("Grey Cotton Tee", "top", "casual", "summer", ["grey"], "cotton", 150, "COS", ["casual", "travel"]),
    ("Charcoal Wool Trousers", "bottom", "smart", "all", ["charcoal"], "wool", 420, "SuitSupply", ["office"]),
    ("Indigo Slim Jeans", "bottom", "casual", "all", ["indigo"], "denim", 600, "Levi's", ["casual", "travel"]),
    ("Beige Chino Shorts", "bottom", "casual", "summer", ["beige"], "cotton", 250, "Uniqlo", ["travel"]),
    ("Navy Blazer", "formal", "formal", "all", ["navy"], "wool", 650, "SuitSupply", ["office"]),
    ("Olive Field Jacket", "outerwear", "casual_smart", "autumn", ["olive"], "cotton", 780, "Barbour", ["travel"]),
    (
        "White Leather Sneakers",
        "footwear",
        "casual_smart",
        "all",
        ["white"],
        "leather",
        820,
        "Common Proj",
        ["casual", "travel"],
    ),
    ("Brown Derby Shoes", "footwear", "formal", "all", ["brown"], "leather", 900, "Loake", ["office"]),
    ("Linen Scarf", "accessory", "casual", "summer", ["sand"], "linen", 90, "Acne", ["travel"]),
    ("Running Set", "activewear", "activewear", "all", ["black"], "polyester", 320, "Nike", ["gym"]),
]


class Command(BaseCommand):
    help = "Seed a fully-populated demo account for screenshots and demos."

    def add_arguments(self, parser):
        # Defaults fall back to env vars so the entrypoint can seed on deploy
        # (SEED_DEMO_USER=1) with a per-environment password, no CLI args needed.
        parser.add_argument("--email", default=os.getenv("DEMO_EMAIL", "demo@getritha.com"))
        parser.add_argument("--password", default=os.getenv("DEMO_PASSWORD", "RithaDemo2026!"))
        parser.add_argument(
            "--reset", action="store_true", help="Wipe the demo user's wardrobe/trips/history before reseeding."
        )
        parser.add_argument(
            "--region",
            default=os.getenv("DEMO_REGION", ""),
            help="Seed the wardrobe from this region's starter pack (with cached photos) "
            "instead of the default Western set. E.g. south_asian_north, south_asian_tropical.",
        )
        parser.add_argument(
            "--gender", default=os.getenv("DEMO_GENDER", "women"), help="Gender bucket for --region (default: women)."
        )

    @transaction.atomic
    def handle(self, *args, **opts):
        email = opts["email"].lower()
        today = datetime.date.today()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={"first_name": "Demo", "last_name": "Stylist", "timezone": "Europe/Zurich"},
        )
        user.set_password(opts["password"])
        user.is_email_verified = True
        user.save()
        self.stdout.write(f"{'Created' if created else 'Updated'} user {email}")

        if opts["reset"]:
            user.wardrobe.all().delete()
            user.trips.all().delete()
            user.outfit_recommendations.all().delete()
            user.sustainability_logs.all().delete()
            self.stdout.write("Reset existing demo data.")

        # Resolve the requested region (if any) — drives the onboarding record
        # and a photo-backed regional wardrobe below.
        region_code = opts["region"].strip()
        gender = opts["gender"].strip() or "women"
        region_obj = None
        if region_code:
            try:
                region_obj = RegionCluster.objects.get(code=region_code)
            except RegionCluster.DoesNotExist:
                known = (
                    ", ".join(RegionCluster.objects.values_list("code", flat=True)) or "(none — run seed_starter_packs)"
                )
                raise CommandError(f'Unknown region "{region_code}". Known: {known}') from None

        # Mark onboarding complete (the API derives this from an existing
        # StarterPackApplication, so the demo user skips the /onboarding gate).
        if not hasattr(user, "starter_pack_application"):
            region = (
                region_obj
                or RegionCluster.objects.first()
                or RegionCluster.objects.create(
                    code="demo-europe",
                    display_name="Demo (Western Europe)",
                    climate_zone="C",
                    cultural_cluster="nw_european",
                    country_codes=["CH", "DE", "FR"],
                )
            )
            StarterPackApplication.objects.create(
                user=user,
                region_cluster=region,
                gender=gender if region_obj else "unspecified",
                proposed_items=[],
                custom_added=[],
                opt_ins=[],
            )

        # ── Wardrobe ───────────────────────────────────────────────────────────
        if region_obj:
            items = self._seed_region_wardrobe(user, region_obj, gender, today)
            self.stdout.write(f"Wardrobe: {len(items)} {region_obj.code}/{gender} items (photos where cached)")
        else:
            items = self._seed_default_wardrobe(user, today)
            self.stdout.write(f"Wardrobe: {len(items)} items")

        def by_cat(c):
            return [it for it in items if it.category == c]

        # ── Upcoming trip + packing checklist ───────────────────────────────────
        trip, _ = Trip.objects.update_or_create(
            user=user,
            name="Lisbon Long Weekend",
            defaults={
                "destination": "Lisbon, Portugal",
                "country": "Portugal",
                "cities": ["Lisbon", "Sintra"],
                "start_date": today + datetime.timedelta(days=24),
                "end_date": today + datetime.timedelta(days=28),
                "notes": "Mix of sightseeing and one smart dinner.",
            },
        )
        trip.checklist_items.all().delete()
        for it in items[:7]:
            PackingChecklistItem.objects.create(trip=trip, clothing_item=it, is_packed=(it.category == "footwear"))
        self.stdout.write(f"Trip: {trip.name} (+{trip.checklist_items.count()} packing items)")

        # ── Accepted daily-look history (last 6 days) ───────────────────────────
        # Regenerated each run, so clear prior demo looks to stay idempotent.
        user.outfit_recommendations.filter(source="daily").delete()
        tops, bottoms, shoes = by_cat("top"), by_cat("bottom"), by_cat("footwear")
        for d in range(1, 7):
            rec = OutfitRecommendation.objects.create(
                user=user,
                date=today - datetime.timedelta(days=d),
                source="daily",
                notes="Smart-casual for the office, layered for the morning chill.",
                weather_snapshot={"temp_c": 17 + d % 5, "condition": "Partly cloudy", "source": "open-meteo"},
                accepted=True,
            )
            picks = [tops[d % len(tops)], bottoms[d % len(bottoms)], shoes[d % len(shoes)]]
            for j, it in enumerate(picks):
                OutfitItem.objects.create(
                    outfit=rec, clothing_item=it, role="main" if j == 0 else "secondary", liked=True
                )
        self.stdout.write("Outfit history: 6 accepted daily looks")

        # ── Sustainability ──────────────────────────────────────────────────────
        SustainabilityLog.objects.filter(user=user).delete()
        logs = [
            ("wear_again", Decimal("2.500"), 20),
            ("carry_on_only", Decimal("5.000"), 50),
            ("secondhand", Decimal("8.000"), 40),
            ("wear_again", Decimal("2.500"), 20),
        ]
        for action, co2, pts in logs:
            SustainabilityLog.objects.create(
                user=user, action=action, co2_saved_kg=co2, points=pts, notes="Demo activity"
            )
        profile, _ = UserSustainabilityProfile.objects.get_or_create(user=user)
        profile.total_points = sum(p for _, _, p in logs)
        profile.total_co2_saved_kg = sum((c for _, c, _ in logs), Decimal("0"))
        profile.wear_again_streak = 4
        profile.save()
        self.stdout.write(f"Sustainability: {profile.total_points} pts, {profile.total_co2_saved_kg}kg CO₂ saved")

        self.stdout.write(self.style.SUCCESS(f"\nDemo account ready → {email} / {opts['password']}"))

    def _seed_default_wardrobe(self, user, today):
        """The original hardcoded Western wardrobe (no photos)."""
        items = []
        for i, (name, cat, form, season, colors, mat, wt, brand, tags) in enumerate(DEMO_WARDROBE):
            item, _ = ClothingItem.objects.update_or_create(
                user=user,
                name=name,
                defaults={
                    "category": cat,
                    "formality": form,
                    "season": season,
                    "colors": colors,
                    "material": mat,
                    "weight_grams": wt,
                    "brand": brand,
                    "tags": tags,
                    "times_worn": (i * 3) % 11,
                    "last_worn": today - datetime.timedelta(days=i + 1),
                },
            )
            items.append(item)
        return items

    def _seed_region_wardrobe(self, user, region, gender, today):
        """Build the wardrobe from a region's default starter pack, attaching the
        cached CC0 flat-lay photo to each item where one is available."""
        from wardrobe.images import attach_seed_image
        from wardrobe.models import StarterPackItem

        sp_items = list(
            StarterPackItem.objects.filter(region_cluster=region, gender=gender, is_default=True).order_by("sort_order")
        )
        if not sp_items:
            raise CommandError(
                f'No starter items for region "{region.code}" / gender "{gender}". '
                "Run: python manage.py seed_starter_packs"
            )
        items = []
        for i, sp in enumerate(sp_items):
            item, _ = ClothingItem.objects.update_or_create(
                user=user,
                name=sp.display_name,
                defaults={
                    "category": sp.category,
                    "formality": sp.formality,
                    "season": sp.seasonality,
                    "colors": sp.default_colors,
                    "source": "starter_pack",
                    "tags": [sp.subcategory],
                    "times_worn": (i * 3) % 11,
                    "last_worn": today - datetime.timedelta(days=i + 1),
                },
            )
            if not item.image:
                attach_seed_image(item, region.code, gender, sp.subcategory)
            items.append(item)
        return items
