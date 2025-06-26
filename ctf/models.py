from django.db import models
from django.contrib.auth.models import User

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class Challenge(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='challenges')
    value = models.IntegerField(default=100)
    hidden = models.BooleanField(default=False)
    file_upload = models.FileField(upload_to='challenges/files/', blank=True, null=True)
    flag = models.CharField(max_length=255)

    def __str__(self):
        return self.title

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(User, related_name='teams', blank=True)
    affiliation = models.CharField(max_length=100, blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Add more fields as needed (e.g., display_name, avatar, etc.)

    def __str__(self):
        return self.user.username

class ChallengeFile(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='challenges/files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.challenge.title} - {self.file.name}"

class Hint(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='hints')
    text = models.TextField()
    cost = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"Hint for {self.challenge.title} (Cost: {self.cost})"

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='submissions')
    submitted_flag = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} - {'Correct' if self.correct else 'Incorrect'}"

class HintUnlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hint_unlocks')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='hint_unlocks', null=True, blank=True)
    hint = models.ForeignKey(Hint, on_delete=models.CASCADE, related_name='unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} unlocked hint for {self.hint.challenge.title} at {self.unlocked_at}"
