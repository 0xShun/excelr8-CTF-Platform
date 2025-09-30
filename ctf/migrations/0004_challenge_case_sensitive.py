from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('ctf', '0003_team_password_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='challenge',
            name='case_sensitive',
            field=models.BooleanField(default=False, help_text='Require exact case when matching the flag'),
        ),
    ]
