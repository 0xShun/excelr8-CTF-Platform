from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('ctf', '0002_competitionsettings_challenge_author_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='password_hash',
            field=models.CharField(blank=True, help_text='Hashed team password', max_length=128),
        ),
    ]
