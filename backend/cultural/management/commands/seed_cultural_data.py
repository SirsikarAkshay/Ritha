"""
Management command: python manage.py seed_cultural_data
Seeds the database with a starter set of cultural etiquette rules and local events.
"""
from django.core.management.base import BaseCommand
from cultural.models import CulturalRule, LocalEvent


RULES = [
    # Turkey
    dict(country='Turkey', city='Istanbul', place_name='Blue Mosque',
         rule_type='cover_head', description='Women must cover their hair with a scarf. Scarves are available at the entrance.', severity='required'),
    dict(country='Turkey', city='Istanbul', place_name='Blue Mosque',
         rule_type='cover_knees', description='Knees and shoulders must be covered for all visitors.', severity='required'),
    dict(country='Turkey', city='Istanbul', place_name='Blue Mosque',
         rule_type='remove_shoes', description='Shoes must be removed before entering. Bags are provided.', severity='required'),

    # Italy
    dict(country='Italy', city='Rome', place_name='Vatican / St. Peter\'s Basilica',
         rule_type='cover_shoulders', description='Bare shoulders are not permitted. A scarf or shawl is sufficient.', severity='required'),
    dict(country='Italy', city='Rome', place_name='Vatican / St. Peter\'s Basilica',
         rule_type='cover_knees', description='Shorts and skirts above the knee are not allowed.', severity='required'),

    # Japan
    dict(country='Japan', city='', place_name='Traditional temples & ryokan',
         rule_type='remove_shoes', description='Remove shoes before entering temples, ryokan, and many traditional restaurants. Look for a step up (\'agari-kamachi\').', severity='required'),
    dict(country='Japan', city='', place_name='Onsen / public bath',
         rule_type='general', description='No swimwear in traditional onsen. Tattoos may be prohibited — check in advance.', severity='warning'),

    # India
    dict(country='India', city='', place_name='Hindu & Sikh temples',
         rule_type='cover_head', description='Head covering required at Sikh Gurdwaras. Scarves available at entrance.', severity='required'),
    dict(country='India', city='', place_name='Hindu & Sikh temples',
         rule_type='remove_shoes', description='Shoes must be removed before entering places of worship.', severity='required'),
    dict(country='India', city='', place_name='Golden Temple, Amritsar',
         rule_type='cover_head', description='All visitors must cover their head. Free cloth is provided.', severity='required'),

    # Thailand
    dict(country='Thailand', city='Bangkok', place_name='Wat Phra Kaew (Temple of Emerald Buddha)',
         rule_type='cover_knees', description='Knees and shoulders must be covered. Sarongs available for rent at the gate.', severity='required'),
    dict(country='Thailand', city='Bangkok', place_name='Grand Palace',
         rule_type='modest_dress', description='Modest dress required: no sleeveless tops, shorts, or flip-flops.', severity='required'),

    # Saudi Arabia
    dict(country='Saudi Arabia', city='', place_name='Public spaces',
         rule_type='modest_dress', description='Women should wear an abaya in public. Men should avoid shorts.', severity='required'),

    # France
    dict(country='France', city='Paris', place_name='General',
         rule_type='general', description='Parisians dress smartly — overly casual attire (flip-flops, sportswear) in upscale restaurants may be frowned upon.', severity='info'),

    # Morocco
    dict(country='Morocco', city='', place_name='Mosques',
         rule_type='cover_head', description='Non-Muslims are generally not permitted inside mosques. Where allowed, modest dress and head covering required.', severity='required'),
    dict(country='Morocco', city='Marrakech', place_name='Medina & souks',
         rule_type='modest_dress', description='Loose, covering clothing is respectful and practical. Avoid sleeveless tops and very short skirts.', severity='info'),
]


EVENTS = [
    dict(country='India', name='Holi', description='Hindu festival of colours celebrated in March.',
         clothing_note="Pack old clothes you don't mind ruining — coloured powder and water will stain permanently.",
         start_month=3, end_month=3),
    dict(country='India', name='Diwali', description='Festival of lights, usually October–November.',
         clothing_note='Traditional Indian attire is appreciated and festive. Expect crowds at markets.',
         start_month=10, end_month=11),
    dict(country='Brazil', name='Rio Carnival', description='World-famous carnival in Rio de Janeiro, February.',
         clothing_note='Elaborate, colourful, minimal clothing is the norm for street parties (blocos). Bring a spare outfit — you will get wet.',
         start_month=2, end_month=2),
    dict(country='Spain', name='La Tomatina', description='Annual tomato-throwing festival in Buñol, last Wednesday of August.',
         clothing_note="Wear old clothes and shoes you are willing to discard. White is traditional. Don't wear contact lenses.",
         start_month=8, end_month=8),
    dict(country='Spain', name='Running of the Bulls (San Fermín)', description='Festival in Pamplona, July 6–14.',
         clothing_note='Traditional dress is white clothes with a red sash and red neckerchief (pañuelo).',
         start_month=7, end_month=7),
    dict(country='Japan', name='Obon Festival', description='Japanese Buddhist festival honouring ancestors, mid-August.',
         clothing_note='Wearing a yukata (casual summer kimono) to Bon Odori dances is welcome and appreciated.',
         start_month=8, end_month=8),
    dict(country='Japan', name='Hanami (Cherry Blossom Viewing)', description='Cherry blossom season, late March to April.',
         clothing_note='Casual and comfortable. Layers are essential — weather can be unpredictable. A light jacket is recommended for evening picnics.',
         start_month=3, end_month=4),
    dict(country='Germany', name='Oktoberfest', description='Munich beer festival, mid-September to first weekend of October.',
         clothing_note='Traditional Bavarian dress (Dirndl for women, Lederhosen for men) is widely worn and hugely appreciated. Renting is easy and affordable in Munich.',
         start_month=9, end_month=10),
    dict(country='Thailand', name='Songkran (Thai New Year)', description='Thai New Year water festival, April 13–15.',
         clothing_note='Wear clothes you are happy to get soaked. Light, quick-dry fabrics work best. Leave valuables and electronics at the hotel.',
         start_month=4, end_month=4),
    dict(country='Netherlands', name="King's Day (Koningsdag)", description='Dutch national holiday, April 27.',
         clothing_note="Everything orange — the entire country wears orange. Even a small orange accessory is a fun way to join in.",
         start_month=4, end_month=4),
    dict(country='United States', name='Mardi Gras (New Orleans)', description='Carnival season culminating on Fat Tuesday, February.',
         clothing_note='Elaborate costumes and purple, green, and gold are traditional. Comfortable shoes are essential for walking the French Quarter.',
         start_month=2, end_month=2),
    dict(country='Scotland', name='Edinburgh Fringe Festival', description='World\'s largest arts festival, August.',
         clothing_note='Layers are essential — Scottish summer weather is unpredictable. A packable waterproof jacket is a must.',
         start_month=8, end_month=8),
]


class Command(BaseCommand):
    help = 'Seed the database with starter cultural etiquette rules and local events'

    def add_arguments(self, parser):
        parser.add_argument('--flush', action='store_true',
                            help='Delete all existing rules and events before seeding')

    def handle(self, *args, **options):
        if options['flush']:
            CulturalRule.objects.all().delete()
            LocalEvent.objects.all().delete()
            self.stdout.write(self.style.WARNING('Existing data flushed.'))

        rules_created = 0
        for rule_data in RULES:
            _, created = CulturalRule.objects.get_or_create(
                country=rule_data['country'],
                place_name=rule_data['place_name'],
                rule_type=rule_data['rule_type'],
                defaults=rule_data,
            )
            if created:
                rules_created += 1

        events_created = 0
        for event_data in EVENTS:
            _, created = LocalEvent.objects.get_or_create(
                country=event_data['country'],
                name=event_data['name'],
                defaults=event_data,
            )
            if created:
                events_created += 1

        self.stdout.write(self.style.SUCCESS(
            f'✅  Seeded {rules_created} cultural rules and {events_created} local events.'
        ))
