"""
Test models for the CTF platform
Tests all model functionality including validation, properties, and business logic
"""
import unittest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import check_password

from ctf.models import (
    CompetitionSettings, Category, Challenge, Team, UserProfile, 
    ChallengeFile, Hint, Submission, HintUnlock
)


class CompetitionSettingsModelTest(TestCase):
    """Test CompetitionSettings model"""
    
    def setUp(self):
        self.settings_data = {
            'competition_name': 'Test CTF',
            'start_time': timezone.now(),
            'end_time': timezone.now() + timedelta(days=1),
            'description': 'Test competition',
            'max_team_size': 4
        }
    
    def test_singleton_creation(self):
        """Test that only one CompetitionSettings instance can exist"""
        settings1 = CompetitionSettings.objects.create(**self.settings_data)
        
        with self.assertRaises(ValidationError):
            settings2 = CompetitionSettings(**self.settings_data)
            settings2.save()
    
    def test_get_settings_creates_default(self):
        """Test get_settings creates default settings if none exist"""
        self.assertEqual(CompetitionSettings.objects.count(), 0)
        settings = CompetitionSettings.get_settings()
        self.assertEqual(CompetitionSettings.objects.count(), 1)
        self.assertEqual(settings.competition_name, 'EXCELR8 CTF')
    
    def test_time_validation(self):
        """Test that end_time must be after start_time"""
        invalid_data = self.settings_data.copy()
        invalid_data['end_time'] = timezone.now() - timedelta(days=1)
        
        settings = CompetitionSettings(**invalid_data)
        with self.assertRaises(ValidationError):
            settings.clean()
    
    def test_competition_status_properties(self):
        """Test is_active, is_upcoming, is_finished properties"""
        now = timezone.now()
        
        # Future competition
        future_settings = CompetitionSettings.objects.create(
            competition_name='Future CTF',
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(days=1)
        )
        self.assertTrue(future_settings.is_upcoming)
        self.assertFalse(future_settings.is_active)
        self.assertFalse(future_settings.is_finished)
        
        # Active competition
        active_settings = CompetitionSettings.objects.create(
            competition_name='Active CTF',
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1)
        )
        self.assertFalse(active_settings.is_upcoming)
        self.assertTrue(active_settings.is_active)
        self.assertFalse(active_settings.is_finished)


class CategoryModelTest(TestCase):
    """Test Category model"""
    
    def test_category_creation(self):
        """Test category creation and string representation"""
        category = Category.objects.create(
            name='Web',
            description='Web exploitation challenges'
        )
        self.assertEqual(str(category), 'Web')
        self.assertEqual(category.name, 'Web')
    
    def test_unique_name_constraint(self):
        """Test that category names must be unique"""
        Category.objects.create(name='Crypto')
        
        with self.assertRaises(Exception):  # IntegrityError
            Category.objects.create(name='Crypto')


class ChallengeModelTest(TestCase):
    """Test Challenge model"""
    
    def setUp(self):
        self.category = Category.objects.create(name='Web')
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        
    def test_challenge_creation(self):
        """Test challenge creation with all fields"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            description='A test challenge',
            category=self.category,
            value=100,
            flag='flag{test}',
            case_sensitive=False,
            difficulty='medium',
            author='tester'
        )
        self.assertEqual(str(challenge), 'Test Challenge')
        self.assertEqual(challenge.value, 100)
        self.assertFalse(challenge.case_sensitive)
    
    def test_solve_and_attempt_counts(self):
        """Test solve_count and attempt_count properties"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}'
        )
        
        self.assertEqual(challenge.solve_count, 0)
        self.assertEqual(challenge.attempt_count, 0)
        
        # Add incorrect submission
        Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='wrong'
        )
        
        self.assertEqual(challenge.solve_count, 0)
        self.assertEqual(challenge.attempt_count, 1)
        
        # Add correct submission
        Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='flag{test}'
        )
        
        self.assertEqual(challenge.solve_count, 1)
        self.assertEqual(challenge.attempt_count, 2)
    
    def test_is_solved_by_user(self):
        """Test is_solved_by_user method"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}'
        )
        
        self.assertFalse(challenge.is_solved_by_user(self.user))
        
        Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='flag{test}'
        )
        
        self.assertTrue(challenge.is_solved_by_user(self.user))
    
    def test_current_value_dynamic_scoring(self):
        """Test current_value property with dynamic scoring"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}',
            initial_value=500,
            minimum_value=100,
            decay_factor=0.8
        )
        
        # Without dynamic scoring enabled (default)
        self.assertEqual(challenge.current_value, challenge.value)


class TeamModelTest(TestCase):
    """Test Team model"""
    
    def setUp(self):
        self.user1 = User.objects.create_user('user1', 'user1@test.com', 'pass')
        self.user2 = User.objects.create_user('user2', 'user2@test.com', 'pass')
        
    def test_team_creation(self):
        """Test team creation and string representation"""
        team = Team.objects.create(
            name='Test Team',
            affiliation='Test Org',
            password_hash='hashed_password'
        )
        self.assertEqual(str(team), 'Test Team')
        self.assertTrue(team.is_active)
    
    def test_team_members(self):
        """Test adding members to team"""
        team = Team.objects.create(name='Test Team')
        team.members.add(self.user1, self.user2)
        
        self.assertEqual(team.members.count(), 2)
        self.assertIn(self.user1, team.members.all())
        self.assertIn(self.user2, team.members.all())
    
    def test_total_score_calculation(self):
        """Test total_score property calculation"""
        team = Team.objects.create(name='Test Team')
        team.members.add(self.user1)
        
        category = Category.objects.create(name='Web')
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=category,
            flag='flag{test}',
            value=100
        )
        
        # Create correct submission
        Submission.objects.create(
            user=self.user1,
            team=team,
            challenge=challenge,
            submitted_flag='flag{test}',
            correct=True
        )
        
        self.assertEqual(team.total_score, 100)


class UserProfileModelTest(TestCase):
    """Test UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        
    def test_profile_creation(self):
        """Test user profile creation"""
        profile = UserProfile.objects.create(
            user=self.user,
            display_name='Test User',
            bio='A test user',
            website='https://example.com'
        )
        
        self.assertEqual(str(profile), "testuser's Profile")
        self.assertEqual(profile.get_display_name, 'Test User')
    
    def test_get_display_name_fallback(self):
        """Test get_display_name falls back to username"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(profile.get_display_name, 'testuser')


class SubmissionModelTest(TestCase):
    """Test Submission model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.category = Category.objects.create(name='Web')
        
    def test_submission_flag_checking_case_insensitive(self):
        """Test automatic flag checking for case-insensitive challenges"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}',
            case_sensitive=False
        )
        
        # Test correct flag (different case)
        submission = Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='FLAG{TEST}'
        )
        self.assertTrue(submission.correct)
        
        # Test incorrect flag
        submission2 = Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='flag{wrong}'
        )
        self.assertFalse(submission2.correct)
    
    def test_submission_flag_checking_case_sensitive(self):
        """Test automatic flag checking for case-sensitive challenges"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{TeSt}',
            case_sensitive=True
        )
        
        # Test correct flag (exact case)
        submission = Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='flag{TeSt}'
        )
        self.assertTrue(submission.correct)
        
        # Test wrong case
        submission2 = Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='flag{test}'
        )
        self.assertFalse(submission2.correct)
    
    def test_submission_string_representation(self):
        """Test submission string representation"""
        challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}'
        )
        
        submission = Submission.objects.create(
            user=self.user,
            challenge=challenge,
            submitted_flag='flag{test}'
        )
        
        expected = "testuser - Test Challenge - ✓"
        self.assertEqual(str(submission), expected)


class HintModelTest(TestCase):
    """Test Hint model"""
    
    def setUp(self):
        self.category = Category.objects.create(name='Web')
        self.challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}'
        )
        
    def test_hint_creation(self):
        """Test hint creation"""
        hint = Hint.objects.create(
            challenge=self.challenge,
            text='This is a hint',
            cost=50,
            order=1
        )
        
        self.assertEqual(hint.text, 'This is a hint')
        self.assertEqual(hint.cost, 50)
        self.assertEqual(str(hint), 'Hint for Test Challenge (Cost: 50)')


class HintUnlockModelTest(TestCase):
    """Test HintUnlock model"""
    
    def setUp(self):
        self.user = User.objects.create_user('testuser', 'test@test.com', 'pass')
        self.category = Category.objects.create(name='Web')
        self.challenge = Challenge.objects.create(
            title='Test Challenge',
            category=self.category,
            flag='flag{test}'
        )
        self.hint = Hint.objects.create(
            challenge=self.challenge,
            text='This is a hint',
            cost=50
        )
        
    def test_hint_unlock_creation(self):
        """Test hint unlock creation"""
        unlock = HintUnlock.objects.create(
            user=self.user,
            hint=self.hint
        )
        
        self.assertEqual(unlock.user, self.user)
        self.assertEqual(unlock.hint, self.hint)
        self.assertEqual(str(unlock), 'testuser unlocked hint for Test Challenge')
    
    def test_unique_constraint(self):
        """Test that user can't unlock same hint twice"""
        HintUnlock.objects.create(user=self.user, hint=self.hint)
        
        with self.assertRaises(Exception):  # IntegrityError
            HintUnlock.objects.create(user=self.user, hint=self.hint)


if __name__ == '__main__':
    unittest.main()
