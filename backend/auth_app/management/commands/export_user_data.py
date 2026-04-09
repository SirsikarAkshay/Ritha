"""
GDPR data export management command.
Usage: python manage.py export_user_data --email user@example.com --output /tmp/export.json
"""
import json
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.core import serializers as django_serializers

User = get_user_model()


class Command(BaseCommand):
    help = 'Export all data for a user (GDPR Article 20 — data portability)'

    def add_arguments(self, parser):
        parser.add_argument('--email',  required=True, help='User email address')
        parser.add_argument('--output', default=None,  help='Output JSON file path (default: stdout)')

    def handle(self, *args, **options):
        email = options['email']
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise CommandError(f'No user with email: {email}')

        from wardrobe.models import ClothingItem
        from itinerary.models import CalendarEvent, Trip
        from outfits.models import OutfitRecommendation
        from sustainability.models import SustainabilityLog, UserSustainabilityProfile
        from agents.models import AgentJob

        export = {
            'user': {
                'email':      user.email,
                'first_name': user.first_name,
                'last_name':  user.last_name,
                'timezone':   user.timezone,
                'created_at': user.created_at.isoformat(),
                'style_profile': user.style_profile,
            },
            'wardrobe': list(
                ClothingItem.objects.filter(user=user).values(
                    'id','name','category','formality','season','colors',
                    'material','brand','weight_grams','tags','times_worn','last_worn','created_at'
                )
            ),
            'calendar_events': list(
                CalendarEvent.objects.filter(user=user).values(
                    'id','title','description','location','event_type',
                    'formality','start_time','end_time','source','created_at'
                )
            ),
            'trips': list(
                Trip.objects.filter(user=user).values(
                    'id','name','destination','start_date','end_date','notes','created_at'
                )
            ),
            'outfit_recommendations': list(
                OutfitRecommendation.objects.filter(user=user).values(
                    'id','date','source','notes','accepted','created_at'
                )
            ),
            'sustainability_logs': list(
                SustainabilityLog.objects.filter(user=user).values(
                    'id','action','co2_saved_kg','points','notes','created_at'
                )
            ),
            'sustainability_profile': None,
            'agent_jobs': list(
                AgentJob.objects.filter(user=user).values(
                    'id','agent_type','status','created_at','completed_at'
                )
            ),
        }

        # Sustainability profile
        try:
            from sustainability.models import UserSustainabilityProfile
            p = UserSustainabilityProfile.objects.get(user=user)
            export['sustainability_profile'] = {
                'total_points':       p.total_points,
                'total_co2_saved_kg': str(p.total_co2_saved_kg),
                'wear_again_streak':  p.wear_again_streak,
            }
        except UserSustainabilityProfile.DoesNotExist:
            pass

        # Serialise dates to strings
        output_str = json.dumps(export, indent=2, default=str)

        if options['output']:
            with open(options['output'], 'w') as f:
                f.write(output_str)
            self.stdout.write(self.style.SUCCESS(f'✅  Exported data for {email} → {options["output"]}'))
        else:
            self.stdout.write(output_str)
