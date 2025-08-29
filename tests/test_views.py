"""
Test views for the CTF platform
Tests all user-facing views including authentication, team management, challenges, etc.
"""
import unittest
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password

from ctf.models import (
    CompetitionSettings, Category, Challenge, Team, UserProfile,
    Submission, Hint, HintUnlock
)


class BaseViewTest(TestCase):
    """Base test class with common setup"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )
        
        # Create competition settings
        self.settings = CompetitionSettings.objects.create(
            competition_name='Test CTF',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
            description='Test competition'
        )
        
        # Create categories and challenges
        self.category = Category.objects.create(name='Web', description='Web challenges')
        self.challenge = Challenge.objects.create(
            title='Test Challenge',
            description='A test web challenge',
            category=self.category,
            value=100,
            flag='flag{test_flag}',
            case_sensitive=False,
            difficulty='medium'
        )
        
        # Create team
        self.team = Team.objects.create(
            name='Test Team',
            affiliation='Test Org',
            password_hash=make_password('teampass')
        )


class HomeViewTest(BaseViewTest):
    """Test home view"""
    
    def test_home_view_anonymous(self):
        """Test home view for anonymous users"""
        response = self.client.get(reverse('ctf:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Get Started')
        self.assertContains(response, 'Login')
        self.assertContains(response, 'Test CTF')
    
    def test_home_view_authenticated(self):
        """Test home view for authenticated users"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your Progress')
        self.assertNotContains(response, 'Get Started')
    
    def test_home_view_statistics(self):
        """Test that home view shows correct statistics"""
        response = self.client.get(reverse('ctf:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1')  # One challenge
        self.assertContains(response, '0')  # No teams yet


class AuthenticationViewTest(BaseViewTest):
    """Test authentication views"""
    
    def test_register_get(self):
        """Test GET register view"""
        response = self.client.get(reverse('ctf:register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Register')
    
    def test_register_post_valid(self):
        """Test POST register with valid data"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password1': 'complexpass123',
            'password2': 'complexpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(reverse('ctf:register'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check user was created
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Check user profile was created
        user = User.objects.get(username='newuser')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
    
    def test_register_post_invalid(self):
        """Test POST register with invalid data"""
        data = {
            'username': 'newuser',
            'email': 'invalid-email',
            'password1': 'pass',
            'password2': 'different'
        }
        response = self.client.post(reverse('ctf:register'), data)
        self.assertEqual(response.status_code, 200)  # Form has errors
        self.assertFalse(User.objects.filter(username='newuser').exists())
    
    def test_login_view(self):
        """Test login view"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Login')
    
    def test_login_post_valid(self):
        """Test login with valid credentials"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'testpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect after success
    
    def test_login_post_invalid(self):
        """Test login with invalid credentials"""
        response = self.client.post(reverse('login'), {
            'username': 'testuser',
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 200)  # Form has errors


class ProfileViewTest(BaseViewTest):
    """Test profile views"""
    
    def test_profile_view_requires_login(self):
        """Test profile view requires authentication"""
        response = self.client.get(reverse('ctf:profile'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_profile_view_authenticated(self):
        """Test profile view for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'testuser')
    
    def test_edit_profile_get(self):
        """Test GET edit profile"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:edit_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Edit Profile')
    
    def test_edit_profile_post(self):
        """Test POST edit profile"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'display_name': 'Test User',
            'bio': 'I am a test user',
            'website': 'https://example.com'
        }
        response = self.client.post(reverse('ctf:edit_profile'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check profile was updated
        profile = UserProfile.objects.get(user=self.user)
        self.assertEqual(profile.display_name, 'Test User')
        self.assertEqual(profile.bio, 'I am a test user')


class TeamViewTest(BaseViewTest):
    """Test team management views"""
    
    def test_team_register_get(self):
        """Test GET team registration"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:team_register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create a New Team')
    
    def test_team_register_post_valid(self):
        """Test POST team registration with valid data"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'name': 'New Test Team',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        response = self.client.post(reverse('ctf:team_register'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check team was created
        team = Team.objects.get(name='New Test Team')
        self.assertEqual(team.affiliation, 'Test University')
        self.assertIn(self.user, team.members.all())
    
    def test_team_register_already_in_team(self):
        """Test team registration when user already in team"""
        self.team.members.add(self.user)
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('ctf:team_register'))
        self.assertEqual(response.status_code, 302)  # Redirect to profile
    
    def test_team_join_get(self):
        """Test GET team join"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:team_join'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Join a Team')
    
    def test_team_join_post_valid(self):
        """Test POST team join with valid data"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'team_name': 'Test Team',
            'team_password': 'teampass'
        }
        response = self.client.post(reverse('ctf:team_join'), data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Check user was added to team
        self.assertIn(self.user, self.team.members.all())
    
    def test_team_join_invalid_password(self):
        """Test team join with invalid password"""
        self.client.login(username='testuser', password='testpass123')
        data = {
            'team_name': 'Test Team',
            'team_password': 'wrongpass'
        }
        response = self.client.post(reverse('ctf:team_join'), data)
        self.assertEqual(response.status_code, 200)  # Form has errors
        self.assertNotIn(self.user, self.team.members.all())
    
    def test_leave_team(self):
        """Test leaving a team"""
        self.team.members.add(self.user)
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('ctf:leave_team'))
        self.assertEqual(response.status_code, 302)  # Redirect to profile
        
        # Check user was removed from team
        self.assertNotIn(self.user, self.team.members.all())


class ChallengeViewTest(BaseViewTest):
    """Test challenge views"""
    
    def test_challenge_list_anonymous(self):
        """Test challenge list for anonymous users"""
        response = self.client.get(reverse('ctf:challenge_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Challenge')
    
    def test_challenge_list_authenticated(self):
        """Test challenge list for authenticated users"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:challenge_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Challenge')
    
    def test_challenge_list_search(self):
        """Test challenge list with search"""
        response = self.client.get(reverse('ctf:challenge_list'), {'search': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Challenge')
        
        response = self.client.get(reverse('ctf:challenge_list'), {'search': 'nonexistent'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Test Challenge')
    
    def test_challenge_list_category_filter(self):
        """Test challenge list with category filter"""
        response = self.client.get(reverse('ctf:challenge_list'), {'category': self.category.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Challenge')
    
    def test_challenge_detail_anonymous(self):
        """Test challenge detail for anonymous users"""
        response = self.client.get(reverse('ctf:challenge_detail', args=[self.challenge.pk]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_challenge_detail_authenticated(self):
        """Test challenge detail for authenticated users"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:challenge_detail', args=[self.challenge.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Challenge')
        self.assertContains(response, 'Submit Flag')
    
    def test_challenge_submit_correct_flag(self):
        """Test submitting correct flag"""
        self.client.login(username='testuser', password='testpass123')
        data = {'submitted_flag': 'flag{test_flag}'}
        response = self.client.post(reverse('ctf:challenge_detail', args=[self.challenge.pk]), data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after submission
        
        # Check submission was recorded
        submission = Submission.objects.get(user=self.user, challenge=self.challenge)
        self.assertTrue(submission.correct)
    
    def test_challenge_submit_incorrect_flag(self):
        """Test submitting incorrect flag"""
        self.client.login(username='testuser', password='testpass123')
        data = {'submitted_flag': 'flag{wrong}'}
        response = self.client.post(reverse('ctf:challenge_detail', args=[self.challenge.pk]), data)
        
        self.assertEqual(response.status_code, 302)  # Redirect after submission
        
        # Check submission was recorded
        submission = Submission.objects.get(user=self.user, challenge=self.challenge)
        self.assertFalse(submission.correct)
    
    def test_challenge_already_solved(self):
        """Test challenge detail when already solved"""
        # Create correct submission
        Submission.objects.create(
            user=self.user,
            challenge=self.challenge,
            submitted_flag='flag{test_flag}',
            correct=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:challenge_detail', args=[self.challenge.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Already Solved')


class ScoreboardViewTest(BaseViewTest):
    """Test scoreboard views"""
    
    def test_scoreboard_view(self):
        """Test scoreboard view"""
        # Add team with score
        self.team.members.add(self.user)
        Submission.objects.create(
            user=self.user,
            team=self.team,
            challenge=self.challenge,
            submitted_flag='flag{test_flag}',
            correct=True
        )
        
        response = self.client.get(reverse('ctf:scoreboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SCOREBOARD')
        self.assertContains(response, 'Test Team')
    
    def test_scoreboard_json_api(self):
        """Test scoreboard JSON API"""
        self.team.members.add(self.user)
        Submission.objects.create(
            user=self.user,
            team=self.team,
            challenge=self.challenge,
            submitted_flag='flag{test_flag}',
            correct=True
        )
        
        response = self.client.get(reverse('ctf:scoreboard_json'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        data = response.json()
        self.assertIn('teams', data)
        self.assertEqual(len(data['teams']), 1)
        self.assertEqual(data['teams'][0]['name'], 'Test Team')


class UserStatsViewTest(BaseViewTest):
    """Test user stats view"""
    
    def test_user_stats_requires_login(self):
        """Test user stats requires authentication"""
        response = self.client.get(reverse('ctf:user_stats'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_user_stats_authenticated(self):
        """Test user stats for authenticated user"""
        # Create some submissions
        Submission.objects.create(
            user=self.user,
            challenge=self.challenge,
            submitted_flag='flag{test_flag}',
            correct=True
        )
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('ctf:user_stats'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Statistics')


class HintViewTest(BaseViewTest):
    """Test hint functionality"""
    
    def setUp(self):
        super().setUp()
        self.hint = Hint.objects.create(
            challenge=self.challenge,
            text='This is a helpful hint',
            cost=25,
            order=1
        )
    
    def test_unlock_hint_requires_login(self):
        """Test hint unlock requires authentication"""
        response = self.client.post(reverse('ctf:unlock_hint', args=[self.hint.pk]))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_unlock_hint_authenticated(self):
        """Test hint unlock for authenticated user"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('ctf:unlock_hint', args=[self.hint.pk]))
        self.assertEqual(response.status_code, 302)  # Redirect to challenge
        
        # Check hint was unlocked
        self.assertTrue(HintUnlock.objects.filter(user=self.user, hint=self.hint).exists())
    
    def test_unlock_hint_already_unlocked(self):
        """Test unlocking already unlocked hint"""
        HintUnlock.objects.create(user=self.user, hint=self.hint)
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('ctf:unlock_hint', args=[self.hint.pk]))
        self.assertEqual(response.status_code, 302)  # Redirect to challenge
        
        # Should still only have one unlock
        self.assertEqual(HintUnlock.objects.filter(user=self.user, hint=self.hint).count(), 1)


class AjaxViewTest(BaseViewTest):
    """Test AJAX endpoints"""
    
    def test_submit_flag_ajax_authenticated(self):
        """Test AJAX flag submission"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('ctf:submit_flag_ajax'), {
            'challenge_id': self.challenge.pk,
            'flag': 'flag{test_flag}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('Correct flag', data['message'])
    
    def test_submit_flag_ajax_incorrect(self):
        """Test AJAX flag submission with incorrect flag"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(reverse('ctf:submit_flag_ajax'), {
            'challenge_id': self.challenge.pk,
            'flag': 'flag{wrong}'
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Incorrect flag', data['message'])
    
    def test_challenge_stats_json(self):
        """Test challenge statistics JSON endpoint"""
        response = self.client.get(reverse('ctf:challenge_stats_json', args=[self.challenge.pk]))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data['title'], 'Test Challenge')
        self.assertEqual(data['value'], 100)


if __name__ == '__main__':
    unittest.main()
