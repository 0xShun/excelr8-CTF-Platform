from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
import os

class CompetitionSettings(models.Model):
    """Singleton model for competition settings"""
    competition_name = models.CharField(max_length=200, default="CTF Competition")
    description = models.TextField(blank=True, help_text="Competition description shown on homepage")
    
    # Competition timing
    start_time = models.DateTimeField(help_text="When the competition starts")
    end_time = models.DateTimeField(help_text="When the competition ends")
    
    # Registration settings
    registration_enabled = models.BooleanField(default=True, help_text="Allow new user registration")
    team_registration_enabled = models.BooleanField(default=True, help_text="Allow team creation")
    max_team_size = models.PositiveIntegerField(default=4, help_text="Maximum members per team")
    
    # Competition settings
    freeze_scoreboard = models.BooleanField(default=False, help_text="Freeze scoreboard before competition ends")
    freeze_time = models.DateTimeField(null=True, blank=True, help_text="When to freeze scoreboard (optional)")
    show_scoreboard = models.BooleanField(default=True, help_text="Show scoreboard to participants")
    
    # Scoring settings
    enable_hints = models.BooleanField(default=True, help_text="Allow hint system")
    dynamic_scoring = models.BooleanField(default=False, help_text="Enable dynamic scoring (experimental)")
    
    # Contact and branding
    contact_info = models.TextField(blank=True, help_text="Contact information for support")
    logo_url = models.URLField(blank=True, help_text="URL to competition logo")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Competition Settings"
        verbose_name_plural = "Competition Settings"
    
    def save(self, *args, **kwargs):
        # Ensure only one instance exists
        if CompetitionSettings.objects.exists() and not self.pk:
            raise ValidationError('Competition Settings already exist. Please edit the existing settings.')
        return super().save(*args, **kwargs)
    
    def clean(self):
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError('End time must be after start time.')
        
        if self.freeze_time and self.end_time:
            if self.freeze_time >= self.end_time:
                raise ValidationError('Freeze time must be before end time.')
    
    @classmethod
    def get_settings(cls):
        """Get or create competition settings"""
        settings, created = cls.objects.get_or_create(
            pk=1,
            defaults={
                'competition_name': 'EXCELR8 CTF',
                'start_time': timezone.now(),
                'end_time': timezone.now() + timezone.timedelta(days=1),
            }
        )
        return settings
    
    @property
    def is_active(self):
        """Check if competition is currently active"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time
    
    @property
    def is_upcoming(self):
        """Check if competition hasn't started yet"""
        return timezone.now() < self.start_time
    
    @property
    def is_finished(self):
        """Check if competition has ended"""
        return timezone.now() > self.end_time
    
    def __str__(self):
        return self.competition_name

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

class Challenge(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Easy'),
        ('medium', 'Medium'), 
        ('hard', 'Hard'),
        ('expert', 'Expert'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="Markdown supported")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='challenges')
    value = models.IntegerField(default=100, help_text="Points awarded for solving this challenge")
    hidden = models.BooleanField(default=False, help_text="Hide challenge from players")
    flag = models.CharField(max_length=255, help_text="The correct flag for this challenge")
    case_sensitive = models.BooleanField(default=False, help_text="Require exact case when matching the flag")
    
    # Additional CTFd-like fields
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='medium')
    author = models.CharField(max_length=100, blank=True, help_text="Challenge author")
    max_attempts = models.PositiveIntegerField(null=True, blank=True, help_text="Maximum attempts allowed (leave blank for unlimited)")
    
    # Prerequisites and dependencies
    requirements = models.ManyToManyField('self', blank=True, symmetrical=False, help_text="Challenges that must be solved first")
    
    # Dynamic scoring
    initial_value = models.IntegerField(default=100, help_text="Initial value for dynamic scoring")
    minimum_value = models.IntegerField(default=50, help_text="Minimum value for dynamic scoring")
    decay_factor = models.FloatField(default=0.9, help_text="Decay factor for dynamic scoring")
    
    # Connection info for services
    connection_info = models.TextField(blank=True, help_text="Connection details (host:port, etc)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'value', 'title']

    def __str__(self):
        return self.title

    @property
    def solve_count(self):
        """Return number of correct submissions for this challenge"""
        return self.submissions.filter(correct=True).count()

    @property
    def attempt_count(self):
        """Return total number of submissions for this challenge"""
        return self.submissions.count()

    def is_solved_by_user(self, user):
        """Check if challenge is solved by given user"""
        return self.submissions.filter(user=user, correct=True).exists()
    
    def can_attempt(self, user):
        """Check if user can attempt this challenge (considering max_attempts)"""
        if not self.max_attempts:
            return True
        attempts = self.submissions.filter(user=user).count()
        return attempts < self.max_attempts
    
    def is_available_to_user(self, user):
        """Check if challenge is available based on requirements"""
        if self.hidden:
            return False
        
        # Check if all required challenges are solved
        for req in self.requirements.all():
            if not req.is_solved_by_user(user):
                return False
        
        return True
    
    @property
    def current_value(self):
        """Calculate current value with dynamic scoring"""
        settings = CompetitionSettings.get_settings()
        if not settings.dynamic_scoring:
            return self.value
        
        solve_count = self.solve_count
        if solve_count == 0:
            return self.initial_value
        
        # Dynamic scoring formula: initial_value * (decay_factor ^ solve_count)
        current = int(self.initial_value * (self.decay_factor ** solve_count))
        return max(current, self.minimum_value)

class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    members = models.ManyToManyField(User, related_name='teams', blank=True)
    affiliation = models.CharField(max_length=100, blank=True)
    password_hash = models.CharField(max_length=128, blank=True, help_text="Hashed team password")
    registered_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def total_score(self):
        """Calculate total score from correct submissions"""
        total = 0
        for submission in self.submissions.filter(correct=True):
            total += submission.challenge.value
        # Deduct hint costs
        for unlock in self.hint_unlocks.all():
            total -= unlock.hint.cost
        return max(0, total)  # Ensure score doesn't go negative

    @property
    def solved_challenges(self):
        """Return queryset of challenges solved by this team"""
        solved_challenge_ids = self.submissions.filter(correct=True).values_list('challenge_id', flat=True)
        return Challenge.objects.filter(id__in=solved_challenge_ids)

    @property
    def last_solve_time(self):
        """Return timestamp of last correct submission"""
        last_submission = self.submissions.filter(correct=True).order_by('-timestamp').first()
        return last_submission.timestamp if last_submission else self.registered_at

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    @property
    def get_display_name(self):
        return self.display_name if self.display_name else self.user.username

class ChallengeFile(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='challenges/files/')
    filename = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.filename and self.file:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.challenge.title} - {self.filename or self.file.name}"

class Hint(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='hints')
    text = models.TextField()
    cost = models.PositiveIntegerField(default=0, help_text="Points deducted for using this hint")
    order = models.PositiveIntegerField(default=0, help_text="Order in which hints appear")

    class Meta:
        ordering = ['order', 'cost']

    def __str__(self):
        return f"Hint for {self.challenge.title} (Cost: {self.cost})"

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submissions')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='submissions', null=True, blank=True)
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='submissions')
    submitted_flag = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    correct = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        # Auto-check if flag is correct (case-insensitive)
        if self.submitted_flag and self.challenge:
            if getattr(self.challenge, 'case_sensitive', False):
                self.correct = self.submitted_flag.strip() == self.challenge.flag.strip()
            else:
                self.correct = self.submitted_flag.strip().lower() == self.challenge.flag.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} - {'✓' if self.correct else '✗'}"

class HintUnlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hint_unlocks')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='hint_unlocks', null=True, blank=True)
    hint = models.ForeignKey(Hint, on_delete=models.CASCADE, related_name='unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'hint']  # Prevent duplicate unlocks
        ordering = ['-unlocked_at']

    def __str__(self):
        return f"{self.user.username} unlocked hint for {self.hint.challenge.title}"
