# Adds the required student ID number to Info. The one-off default only
# backfills pre-existing rows (none in practice); it is not preserved.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('info', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='info',
            name='id_number',
            field=models.CharField(default='UNKNOWN', max_length=50, unique=True),
            preserve_default=False,
        ),
    ]
