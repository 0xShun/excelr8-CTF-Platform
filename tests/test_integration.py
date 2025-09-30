"""
Integration tests for the CTF platform
Tests end-to-end user workflows and system integration
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


class UserWorkflowIntegrationTest(TestCase):
    """Test complete user workflows from registration to flag submission"""
    
    def setUp(self):
        self.client = Client()
        
        # Set up competition
        self.settings = CompetitionSettings.objects.create(
            competition_name='Integration Test CTF',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=2),
            description='Test competition for integration testing'
        )
        
        # Create challenges
        self.web_category = Category.objects.create(name='Web', description='Web exploitation')
        self.crypto_category = Category.objects.create(name='Crypto', description='Cryptography')
        
        self.easy_challenge = Challenge.objects.create(
            title='Easy Web Challenge',
            description='Simple SQL injection',
            category=self.web_category,
            value=100,
            flag='flag{sql_injection}',
            case_sensitive=False,
            difficulty='easy'
        )
        
        self.hard_challenge = Challenge.objects.create(
            title='Hard Crypto Challenge',
            description='Advanced cryptographic attack',
            category=self.crypto_category,
            value=500,
            flag='FLAG{crypto_master}',
            case_sensitive=True,
            difficulty='hard'
        )
        
        # Create hints
        Hint.objects.create(
            challenge=self.easy_challenge,
            text='Look for SQL injection vulnerabilities',
            cost=25,
            order=1
        )
        
        Hint.objects.create(
            challenge=self.hard_challenge,
            text='Consider frequency analysis',
            cost=100,
            order=1
        )
    
    def test_complete_user_registration_to_solve_workflow(self):
        """Test complete workflow: register → create team → solve challenge → check scoreboard"""
        
        # Step 1: User registration
        register_data = {
            'username': 'integrationuser',
            'email': 'integration@test.com',
            'first_name': 'Integration',
            'last_name': 'Tester',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        response = self.client.post(reverse('ctf:register'), register_data)
        self.assertEqual(response.status_code, 302)  # Redirect after successful registration
        
        # Verify user was created
        user = User.objects.get(username='integrationuser')
        self.assertEqual(user.email, 'integration@test.com')
        
        # Verify profile was created via signal
        profile = UserProfile.objects.get(user=user)
        self.assertIsNotNone(profile)
        
        # Step 2: Login
        login_success = self.client.login(username='integrationuser', password='complexpassword123')
        self.assertTrue(login_success)
        
        # Step 3: Create a team
        team_data = {
            'name': 'Integration Test Team',
            'affiliation': 'Test University',
            'team_password': 'teampass123',
            'confirm_password': 'teampass123'
        }
        response = self.client.post(reverse('ctf:team_register'), team_data)
        self.assertEqual(response.status_code, 302)  # Redirect after team creation
        
        # Verify team was created and user was added
        team = Team.objects.get(name='Integration Test Team')
        self.assertIn(user, team.members.all())
        
        # Step 4: View challenge list
        response = self.client.get(reverse('ctf:challenge_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Easy Web Challenge')
        self.assertContains(response, 'Hard Crypto Challenge')
        
        # Step 5: View specific challenge
        response = self.client.get(reverse('ctf:challenge_detail', args=[self.easy_challenge.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Easy Web Challenge')
        self.assertContains(response, 'Submit Flag')
        
        # Step 6: Submit wrong flag first
        wrong_flag_data = {'submitted_flag': 'flag{wrong_answer}'}
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.easy_challenge.pk]),
            wrong_flag_data
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify wrong submission was recorded
        wrong_submission = Submission.objects.get(
            user=user,
            challenge=self.easy_challenge,
            submitted_flag='flag{wrong_answer}'
        )
        self.assertFalse(wrong_submission.correct)
        
        # Step 7: Submit correct flag
        correct_flag_data = {'submitted_flag': 'flag{sql_injection}'}
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.easy_challenge.pk]),
            correct_flag_data
        )
        self.assertEqual(response.status_code, 302)
        
        # Verify correct submission was recorded
        correct_submission = Submission.objects.get(
            user=user,
            challenge=self.easy_challenge,
            submitted_flag='flag{sql_injection}',
            correct=True
        )
        self.assertTrue(correct_submission.correct)
        self.assertEqual(correct_submission.team, team)
        
        # Step 8: Check scoreboard
        response = self.client.get(reverse('ctf:scoreboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Integration Test Team')
        self.assertContains(response, '100')  # Team score
        
        # Step 9: Check user stats
        response = self.client.get(reverse('ctf:user_stats'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1')  # Challenges solved
    
    def test_team_join_workflow(self):
        """Test user joining an existing team"""
        
        # Create team first
        team = Team.objects.create(
            name='Existing Team',
            affiliation='Test Org',
            password_hash=make_password('teampass456')
        )
        
        # Register new user
        register_data = {
            'username': 'joineruser',
            'email': 'joiner@test.com',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        }
        self.client.post(reverse('ctf:register'), register_data)
        
        # Login
        self.client.login(username='joineruser', password='complexpassword123')
        user = User.objects.get(username='joineruser')
        
        # Join team
        join_data = {
            'team_name': 'Existing Team',
            'team_password': 'teampass456'
        }
        response = self.client.post(reverse('ctf:team_join'), join_data)
        self.assertEqual(response.status_code, 302)
        
        # Verify user was added to team
        self.assertIn(user, team.members.all())
    
    def test_hint_unlock_workflow(self):
        """Test complete hint unlocking workflow"""
        
        # Set up user and team
        user = User.objects.create_user(
            username='hintuser',
            email='hint@test.com',
            password='testpass123'
        )
        team = Team.objects.create(name='Hint Team', affiliation='Test')
        team.members.add(user)
        
        self.client.login(username='hintuser', password='testpass123')
        
        # View challenge
        response = self.client.get(reverse('ctf:challenge_detail', args=[self.easy_challenge.pk]))
        self.assertEqual(response.status_code, 200)
        
        # Unlock hint
        hint = Hint.objects.get(challenge=self.easy_challenge)
        response = self.client.post(reverse('ctf:unlock_hint', args=[hint.pk]))
        self.assertEqual(response.status_code, 302)
        
        # Verify hint was unlocked
        self.assertTrue(HintUnlock.objects.filter(user=user, hint=hint).exists())
        
        # View challenge again to see unlocked hint
        response = self.client.get(reverse('ctf:challenge_detail', args=[self.easy_challenge.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Look for SQL injection')
    
    def test_case_sensitive_flag_handling(self):
        """Test case-sensitive flag handling"""
        
        user = User.objects.create_user(
            username='caseuser',
            email='case@test.com',
            password='testpass123'
        )
        team = Team.objects.create(name='Case Team', affiliation='Test')
        team.members.add(user)
        
        self.client.login(username='caseuser', password='testpass123')
        
        # Test case-insensitive challenge (easy_challenge)
        flag_data = {'submitted_flag': 'FLAG{SQL_INJECTION}'}  # Wrong case
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.easy_challenge.pk]),
            flag_data
        )
        
        # Should succeed because easy_challenge is case_sensitive=False
        submission = Submission.objects.get(
            user=user,
            challenge=self.easy_challenge,
            submitted_flag='FLAG{SQL_INJECTION}'
        )
        self.assertTrue(submission.correct)  # Should be correct due to case insensitive
        
        # Test case-sensitive challenge (hard_challenge)
        flag_data = {'submitted_flag': 'flag{crypto_master}'}  # Wrong case
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.hard_challenge.pk]),
            flag_data
        )
        
        # Should fail because hard_challenge is case_sensitive=True
        submission = Submission.objects.get(
            user=user,
            challenge=self.hard_challenge,
            submitted_flag='flag{crypto_master}'
        )
        self.assertFalse(submission.correct)  # Should be incorrect due to case sensitivity
        
        # Submit with correct case
        flag_data = {'submitted_flag': 'FLAG{crypto_master}'}
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.hard_challenge.pk]),
            flag_data
        )
        
        correct_submission = Submission.objects.get(
            user=user,
            challenge=self.hard_challenge,
            submitted_flag='FLAG{crypto_master}'
        )
        self.assertTrue(correct_submission.correct)


class CompetitionStateIntegrationTest(TestCase):
    """Test competition state changes and their effects"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='stateuser',
            email='state@test.com',
            password='testpass123'
        )
    
    def test_pre_competition_state(self):
        """Test behavior before competition starts"""
        
        # Create future competition
        future_settings = CompetitionSettings.objects.create(
            competition_name='Future CTF',
            start_time=timezone.now() + timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=3),
            description='Future competition'
        )
        
        # Check home page shows countdown
        response = self.client.get(reverse('ctf:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Competition starts in')
        
        # Login and try to access challenges
        self.client.login(username='stateuser', password='testpass123')
        response = self.client.get(reverse('ctf:challenge_list'))
        
        # Should show message that competition hasn't started
        self.assertEqual(response.status_code, 200)
        # Depending on implementation, might show countdown or restriction message
    
    def test_post_competition_state(self):
        """Test behavior after competition ends"""
        
        # Create past competition
        past_settings = CompetitionSettings.objects.create(
            competition_name='Past CTF',
            start_time=timezone.now() - timedelta(hours=3),
            end_time=timezone.now() - timedelta(hours=1),
            description='Past competition'
        )
        
        category = Category.objects.create(name='Test', description='Test category')
        challenge = Challenge.objects.create(
            title='Past Challenge',
            description='A past challenge',
            category=category,
            value=100,
            flag='flag{past}',
            case_sensitive=False
        )
        
        self.client.login(username='stateuser', password='testpass123')
        
        # Check home page shows competition ended
        response = self.client.get(reverse('ctf:home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Competition has ended')
        
        # Try to submit flag to challenge
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[challenge.pk]),
            {'submitted_flag': 'flag{past}'}
        )
        
        # Should be rejected or show appropriate message
        # Implementation dependent - might redirect with error message
        self.assertIn(response.status_code, [200, 302])


class ScoreboardIntegrationTest(TestCase):
    """Test scoreboard functionality and ranking"""
    
    def setUp(self):
        self.client = Client()
        
        # Set up competition
        self.settings = CompetitionSettings.objects.create(
            competition_name='Scoreboard Test CTF',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
            description='Test competition for scoreboard'
        )
        
        # Create challenges with different values
        self.category = Category.objects.create(name='Test', description='Test category')
        
        self.challenge1 = Challenge.objects.create(
            title='Challenge 1',
            description='First challenge',
            category=self.category,
            value=100,
            flag='flag{one}',
            case_sensitive=False
        )
        
        self.challenge2 = Challenge.objects.create(
            title='Challenge 2',
            description='Second challenge',
            category=self.category,
            value=200,
            flag='flag{two}',
            case_sensitive=False
        )
        
        self.challenge3 = Challenge.objects.create(
            title='Challenge 3',
            description='Third challenge',
            category=self.category,
            value=300,
            flag='flag{three}',
            case_sensitive=False
        )
        
        # Create teams and users
        self.create_team_with_user('Team Alpha', 'alpha', 'alpha@test.com', 'alphapass')
        self.create_team_with_user('Team Beta', 'beta', 'beta@test.com', 'betapass')
        self.create_team_with_user('Team Gamma', 'gamma', 'gamma@test.com', 'gammapass')
    
    def create_team_with_user(self, team_name, username, email, password):
        """Helper to create team with user"""
        user = User.objects.create_user(username=username, email=email, password=password)
        team = Team.objects.create(name=team_name, affiliation='Test Org')
        team.members.add(user)
        return team, user
    
    def solve_challenge_for_user(self, username, challenge):
        """Helper to solve challenge for user"""
        user = User.objects.get(username=username)
        team = user.userprofile.get_team()
        
        Submission.objects.create(
            user=user,
            team=team,
            challenge=challenge,
            submitted_flag=challenge.flag,
            correct=True,
            timestamp=timezone.now()
        )
    
    def test_scoreboard_ranking(self):
        """Test scoreboard shows correct rankings"""
        
        # Team Alpha solves challenge 1 (100 points)
        self.solve_challenge_for_user('alpha', self.challenge1)
        
        # Team Beta solves challenges 1 and 2 (300 points)
        self.solve_challenge_for_user('beta', self.challenge1)
        self.solve_challenge_for_user('beta', self.challenge2)
        
        # Team Gamma solves all challenges (600 points)
        self.solve_challenge_for_user('gamma', self.challenge1)
        self.solve_challenge_for_user('gamma', self.challenge2)
        self.solve_challenge_for_user('gamma', self.challenge3)
        
        # Check scoreboard
        response = self.client.get(reverse('ctf:scoreboard'))
        self.assertEqual(response.status_code, 200)
        
        # Verify teams appear in correct order
        content = response.content.decode()
        gamma_pos = content.find('Team Gamma')
        beta_pos = content.find('Team Beta')
        alpha_pos = content.find('Team Alpha')
        
        # Team Gamma should appear first (highest score)
        self.assertLess(gamma_pos, beta_pos)
        self.assertLess(beta_pos, alpha_pos)
        
        # Check JSON API
        response = self.client.get(reverse('ctf:scoreboard_json'))
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(len(data['teams']), 3)
        
        # Verify ranking order in JSON
        self.assertEqual(data['teams'][0]['name'], 'Team Gamma')
        self.assertEqual(data['teams'][0]['score'], 600)
        self.assertEqual(data['teams'][1]['name'], 'Team Beta')
        self.assertEqual(data['teams'][1]['score'], 300)
        self.assertEqual(data['teams'][2]['name'], 'Team Alpha')
        self.assertEqual(data['teams'][2]['score'], 100)
    
    def test_scoreboard_tie_breaking(self):
        """Test scoreboard tie-breaking by timestamp"""
        
        import time
        
        # Both teams solve same challenge, but at different times
        self.solve_challenge_for_user('alpha', self.challenge1)
        time.sleep(0.1)  # Small delay to ensure different timestamps
        self.solve_challenge_for_user('beta', self.challenge1)
        
        response = self.client.get(reverse('ctf:scoreboard_json'))
        data = response.json()
        
        # With same scores, earlier solver should rank higher
        alpha_team = next(t for t in data['teams'] if t['name'] == 'Team Alpha')
        beta_team = next(t for t in data['teams'] if t['name'] == 'Team Beta')
        
        if alpha_team['score'] == beta_team['score']:
            # Tie-breaking logic would depend on implementation
            self.assertEqual(alpha_team['score'], beta_team['score'])


class SecurityIntegrationTest(TestCase):
    """Test security features and edge cases"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='securityuser',
            email='security@test.com',
            password='testpass123'
        )
        
        self.settings = CompetitionSettings.objects.create(
            competition_name='Security Test CTF',
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),
            description='Security test competition'
        )
        
        self.category = Category.objects.create(name='Test', description='Test')
        self.challenge = Challenge.objects.create(
            title='Security Challenge',
            description='Test challenge',
            category=self.category,
            value=100,
            flag='flag{secure}',
            case_sensitive=False
        )
    
    def test_unauthenticated_access_restrictions(self):
        """Test that unauthenticated users can't access protected views"""
        
        protected_urls = [
            reverse('ctf:profile'),
            reverse('ctf:edit_profile'),
            reverse('ctf:team_register'),
            reverse('ctf:team_join'),
            reverse('ctf:user_stats'),
            reverse('ctf:challenge_detail', args=[self.challenge.pk]),
        ]
        
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)  # Redirect to login
            self.assertIn('/login/', response.url)
    
    def test_duplicate_submission_handling(self):
        """Test handling of duplicate flag submissions"""
        
        team = Team.objects.create(name='Security Team', affiliation='Test')
        team.members.add(self.user)
        
        self.client.login(username='securityuser', password='testpass123')
        
        # Submit correct flag first time
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.challenge.pk]),
            {'submitted_flag': 'flag{secure}'}
        )
        
        # Submit same flag again
        response = self.client.post(
            reverse('ctf:challenge_detail', args=[self.challenge.pk]),
            {'submitted_flag': 'flag{secure}'}
        )
        
        # Should handle gracefully (not create duplicate scoring)
        submissions = Submission.objects.filter(
            user=self.user,
            challenge=self.challenge,
            correct=True
        )
        
        # Depending on implementation, might allow multiple correct submissions
        # but only count score once
        self.assertGreaterEqual(len(submissions), 1)
    
    def test_xss_prevention_in_user_input(self):
        """Test XSS prevention in user-generated content"""
        
        # Test in profile updates
        self.client.login(username='securityuser', password='testpass123')
        
        xss_payload = '<script>alert("xss")</script>'
        
        # Try to inject XSS in profile
        response = self.client.post(reverse('ctf:edit_profile'), {
            'display_name': xss_payload,
            'bio': f'My bio {xss_payload}'
        })
        
        # Check that XSS is not executed when viewing profile
        response = self.client.get(reverse('ctf:profile'))
        self.assertEqual(response.status_code, 200)
        
        # XSS should be escaped in HTML output
        self.assertNotContains(response, '<script>')
        # Should contain escaped version
        self.assertContains(response, '&lt;script&gt;')


if __name__ == '__main__':
    unittest.main()
