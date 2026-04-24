import factory
import datetime
from django.contrib.auth import get_user_model
from wardrobe.models import ClothingItem
from itinerary.models import CalendarEvent, Trip
from outfits.models import OutfitRecommendation
from cultural.models import CulturalRule, LocalEvent
from sustainability.models import SustainabilityLog, UserSustainabilityProfile

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email             = factory.Sequence(lambda n: f'user{n}@ritha.com')
    first_name         = factory.Faker('first_name')
    last_name          = factory.Faker('last_name')
    is_active          = True
    is_email_verified  = True   # verified by default so existing tests still work

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        kwargs.pop('password', None)   # remove if accidentally passed
        user = model_class.objects.create_user(password='testpass99', **kwargs)
        return user


class ClothingItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ClothingItem

    user      = factory.SubFactory(UserFactory)
    name      = factory.Faker('word')
    category  = 'top'
    formality = 'casual'
    season    = 'all'
    colors    = ['white']
    is_active = True


class CalendarEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CalendarEvent

    user       = factory.SubFactory(UserFactory)
    title      = factory.Faker('sentence', nb_words=3)
    event_type = 'internal_meeting'
    start_time = factory.LazyFunction(lambda: datetime.datetime(2026, 3, 14, 10, 0, tzinfo=datetime.timezone.utc))
    end_time   = factory.LazyFunction(lambda: datetime.datetime(2026, 3, 14, 11, 0, tzinfo=datetime.timezone.utc))
    source     = 'manual'


class TripFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trip

    user        = factory.SubFactory(UserFactory)
    name        = factory.Sequence(lambda n: f'Trip {n}')
    destination = 'Paris'
    start_date  = datetime.date(2026, 4, 1)
    end_date    = datetime.date(2026, 4, 7)


class CulturalRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CulturalRule

    country     = 'Turkey'
    city        = 'Istanbul'
    rule_type   = 'cover_head'
    description = 'Headscarf required inside mosques'
    severity    = 'required'


class LocalEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = LocalEvent

    country       = 'India'
    name          = 'Holi Festival'
    description   = 'Festival of colours'
    clothing_note = "Pack clothes you don't mind getting stained"
    start_month   = 3
    end_month     = 3
