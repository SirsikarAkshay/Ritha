from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('outfits', '0004_add_liked_to_outfititem'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserStyleProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_pair_weights',  models.JSONField(blank=True, default=dict)),
                ('item_pair_negatives',    models.JSONField(blank=True, default=list)),
                ('color_affinities',       models.JSONField(blank=True, default=dict)),
                ('formality_distribution', models.JSONField(blank=True, default=dict)),
                ('feedback_count',         models.PositiveIntegerField(default=0)),
                ('last_rebuilt',           models.DateTimeField(blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=models.deletion.CASCADE,
                                              related_name='learned_style',
                                              to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
