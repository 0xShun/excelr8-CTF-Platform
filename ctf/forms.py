from django import forms
from django.contrib.auth.models import User
from .models import Team, Submission, HintUnlock

class TeamRegistrationForm(forms.ModelForm):
    # For simplicity, only team name and affiliation; add member emails and password as needed
    class Meta:
        model = Team
        fields = ['name', 'affiliation']

class ChallengeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['submitted_flag']
        widgets = {
            'submitted_flag': forms.TextInput(attrs={'placeholder': 'Enter flag here'})
        }

class HintUnlockForm(forms.ModelForm):
    class Meta:
        model = HintUnlock
        fields = []  # No user input needed, just a button/action 