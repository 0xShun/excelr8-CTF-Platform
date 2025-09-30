from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import Team, Submission, HintUnlock, UserProfile
from django.contrib.auth.hashers import check_password

class CustomUserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            # Create user profile
            UserProfile.objects.get_or_create(user=user)
        return user

class TeamRegistrationForm(forms.ModelForm):
    team_password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Set a password for your team (members will need this to join)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput,
        help_text="Confirm your team password"
    )
    
    class Meta:
        model = Team
        fields = ['name', 'affiliation']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your team name', 'class': 'form-control'}),
            'affiliation': forms.TextInput(attrs={'placeholder': 'School/Organization (optional)', 'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('team_password')
        confirm_password = cleaned_data.get('confirm_password')
        
        if password and confirm_password:
            if password != confirm_password:
                raise ValidationError("Passwords don't match")
        
        return cleaned_data

class TeamJoinForm(forms.Form):
    team_name = forms.CharField(
        max_length=100, 
        help_text="Enter the team name you want to join",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    team_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        help_text="Enter the team password"
    )
    
    def clean_team_name(self):
        team_name = self.cleaned_data['team_name']
        try:
            team = Team.objects.get(name=team_name)
            if not team.is_active:
                raise ValidationError("This team is not active")
        except Team.DoesNotExist:
            raise ValidationError("Team not found")
        return team_name

    def clean(self):
        cleaned = super().clean()
        team_name = cleaned.get('team_name')
        password = cleaned.get('team_password')
        if team_name and password:
            try:
                team = Team.objects.get(name=team_name)
                if team.password_hash and not check_password(password, team.password_hash):
                    raise ValidationError('Incorrect team password')
            except Team.DoesNotExist:
                pass
        return cleaned

class ChallengeSubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['submitted_flag']
        widgets = {
            'submitted_flag': forms.TextInput(attrs={
                'placeholder': 'Enter flag here (e.g., flag{example})',
                'class': 'form-control',
                'autocomplete': 'off'
            })
        }
        
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.challenge = kwargs.pop('challenge', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        submission = super().save(commit=False)
        if self.user:
            submission.user = self.user
        if self.challenge:
            submission.challenge = self.challenge
            # Auto-assign team if user belongs to one
            user_team = self.user.teams.filter(is_active=True).first()
            if user_team:
                submission.team = user_team
        if commit:
            submission.save()
        return submission

class HintUnlockForm(forms.Form):
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label="I understand this will deduct points from my score"
    )
    
    def __init__(self, *args, **kwargs):
        self.hint = kwargs.pop('hint', None)
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.hint:
            self.fields['confirm'].label = f"Unlock hint for {self.hint.cost} points?"

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['display_name', 'bio', 'website']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
        } 