"""
Test utilities for the CTF platform test suite
Provides common test data, fixtures, and helper functions
"""
import random
import string
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

from ctf.models import (
    CompetitionSettings, Category, Challenge, Team, UserProfile,
    Submission, Hint, HintUnlock
)


class TestDataFactory:
    """Factory class for creating test data"""
    
    @staticmethod
    def create_user(username=None, email=None, password='testpass123', **kwargs):
        """Create a test user with optional parameters"""
        if username is None:
            username = f'testuser_{TestDataFactory._random_string(5)}'
        if email is None:
            email = f'{username}@test.com'
        
        user_data = {
            'username': username,
            'email': email,
            'password': password,
            **kwargs
        }
        
        return User.objects.create_user(**user_data)
    
    @staticmethod
    def create_superuser(username='admin', email='admin@test.com', password='adminpass123'):
        """Create a test superuser"""
        return User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
    
    @staticmethod
    def create_competition_settings(
        name='Test CTF',
        start_offset_hours=-1,
        end_offset_hours=2,
        **kwargs
    ):
        """Create competition settings with time offsets from now"""
        now = timezone.now()
        
        settings_data = {
            'competition_name': name,
            'start_time': now + timedelta(hours=start_offset_hours),
            'end_time': now + timedelta(hours=end_offset_hours),
            'description': f'Test competition: {name}',
            **kwargs
        }
        
        return CompetitionSettings.objects.create(**settings_data)
    
    @staticmethod
    def create_category(name=None, description=None):
        """Create a test category"""
        if name is None:
            name = f'Category_{TestDataFactory._random_string(5)}'
        if description is None:
            description = f'Test category: {name}'
        
        return Category.objects.create(name=name, description=description)
    
    @staticmethod
    def create_challenge(
        title=None,
        category=None,
        value=100,
        flag=None,
        case_sensitive=False,
        difficulty='medium',
        **kwargs
    ):
        """Create a test challenge"""
        if title is None:
            title = f'Challenge_{TestDataFactory._random_string(5)}'
        if category is None:
            category = TestDataFactory.create_category()
        if flag is None:
            flag = f'flag{{{TestDataFactory._random_string(10)}}}'
        
        challenge_data = {
            'title': title,
            'description': f'Test challenge: {title}',
            'category': category,
            'value': value,
            'flag': flag,
            'case_sensitive': case_sensitive,
            'difficulty': difficulty,
            **kwargs
        }
        
        return Challenge.objects.create(**challenge_data)
    
    @staticmethod
    def create_team(name=None, affiliation='Test Organization', password='teampass123'):
        """Create a test team"""
        if name is None:
            name = f'Team_{TestDataFactory._random_string(5)}'
        
        return Team.objects.create(
            name=name,
            affiliation=affiliation,
            password_hash=make_password(password)
        )
    
    @staticmethod
    def create_team_with_members(team_name=None, member_count=3, **team_kwargs):
        """Create a team with multiple members"""
        team = TestDataFactory.create_team(name=team_name, **team_kwargs)
        
        members = []
        for i in range(member_count):
            user = TestDataFactory.create_user(
                username=f'{team.name.lower().replace(" ", "_")}_member_{i+1}'
            )
            team.members.add(user)
            members.append(user)
        
        return team, members
    
    @staticmethod
    def create_submission(user, challenge, flag=None, correct=None, team=None):
        """Create a test submission"""
        if flag is None:
            flag = challenge.flag if correct is not False else f'wrong_{TestDataFactory._random_string(5)}'
        if correct is None:
            correct = (flag.lower() == challenge.flag.lower() if not challenge.case_sensitive 
                      else flag == challenge.flag)
        if team is None and hasattr(user, 'userprofile'):
            try:
                team = user.userprofile.get_team()
            except:
                pass
        
        return Submission.objects.create(
            user=user,
            team=team,
            challenge=challenge,
            submitted_flag=flag,
            correct=correct,
            timestamp=timezone.now()
        )
    
    @staticmethod
    def create_hint(challenge, text=None, cost=25, order=1):
        """Create a test hint"""
        if text is None:
            text = f'Hint for {challenge.title}: {TestDataFactory._random_string(20)}'
        
        return Hint.objects.create(
            challenge=challenge,
            text=text,
            cost=cost,
            order=order
        )
    
    @staticmethod
    def create_hint_unlock(user, hint):
        """Create a hint unlock"""
        return HintUnlock.objects.create(
            user=user,
            hint=hint,
            timestamp=timezone.now()
        )
    
    @staticmethod
    def _random_string(length=10):
        """Generate a random string of specified length"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


class ScenarioBuilder:
    """Builder class for creating complex test scenarios"""
    
    @staticmethod
    def build_active_competition_with_challenges():
        """Build an active competition with multiple categories and challenges"""
        # Competition settings
        settings = TestDataFactory.create_competition_settings(
            name='Active Test Competition',
            start_offset_hours=-2,
            end_offset_hours=4
        )
        
        # Categories
        web_category = TestDataFactory.create_category('Web Exploitation', 'Web security challenges')
        crypto_category = TestDataFactory.create_category('Cryptography', 'Cryptographic challenges')
        pwn_category = TestDataFactory.create_category('Binary Exploitation', 'Binary exploitation challenges')
        
        # Challenges
        challenges = {
            'web_easy': TestDataFactory.create_challenge(
                'SQL Injection 101',
                web_category,
                value=100,
                flag='flag{sql_injection_basic}',
                difficulty='easy'
            ),
            'web_hard': TestDataFactory.create_challenge(
                'Advanced XSS',
                web_category,
                value=400,
                flag='flag{xss_advanced_payload}',
                difficulty='hard'
            ),
            'crypto_medium': TestDataFactory.create_challenge(
                'Caesar Cipher',
                crypto_category,
                value=200,
                flag='flag{caesar_decoded}',
                difficulty='medium'
            ),
            'pwn_expert': TestDataFactory.create_challenge(
                'Stack Buffer Overflow',
                pwn_category,
                value=500,
                flag='FLAG{buffer_overflow_master}',
                case_sensitive=True,
                difficulty='expert'
            )
        }
        
        # Add hints
        TestDataFactory.create_hint(
            challenges['web_easy'],
            'Look for input fields that might not validate user input properly',
            cost=25
        )
        TestDataFactory.create_hint(
            challenges['crypto_medium'],
            'Try shifting letters by different amounts',
            cost=50
        )
        TestDataFactory.create_hint(
            challenges['pwn_expert'],
            'Consider the buffer size and return address location',
            cost=100
        )
        
        return {
            'settings': settings,
            'categories': {
                'web': web_category,
                'crypto': crypto_category,
                'pwn': pwn_category
            },
            'challenges': challenges
        }
    
    @staticmethod
    def build_competition_with_scoreboard_data():
        """Build competition with teams and submissions for scoreboard testing"""
        scenario = ScenarioBuilder.build_active_competition_with_challenges()
        
        # Create teams with different performance levels
        teams_data = []
        
        # Top performing team
        top_team, top_members = TestDataFactory.create_team_with_members(
            'Elite Hackers', member_count=4
        )
        # Solve most challenges
        for challenge_name in ['web_easy', 'web_hard', 'crypto_medium']:
            challenge = scenario['challenges'][challenge_name]
            TestDataFactory.create_submission(
                top_members[0], challenge, correct=True, team=top_team
            )
        teams_data.append(('top', top_team, top_members))
        
        # Medium performing team
        mid_team, mid_members = TestDataFactory.create_team_with_members(
            'Code Warriors', member_count=3
        )
        # Solve some challenges
        for challenge_name in ['web_easy', 'crypto_medium']:
            challenge = scenario['challenges'][challenge_name]
            TestDataFactory.create_submission(
                mid_members[0], challenge, correct=True, team=mid_team
            )
        teams_data.append(('mid', mid_team, mid_members))
        
        # Beginner team
        beginner_team, beginner_members = TestDataFactory.create_team_with_members(
            'Newbie Squad', member_count=2
        )
        # Solve easy challenge only
        challenge = scenario['challenges']['web_easy']
        TestDataFactory.create_submission(
            beginner_members[0], challenge, correct=True, team=beginner_team
        )
        # Also create some wrong submissions
        TestDataFactory.create_submission(
            beginner_members[0], scenario['challenges']['crypto_medium'],
            flag='flag{wrong_guess}', correct=False, team=beginner_team
        )
        teams_data.append(('beginner', beginner_team, beginner_members))
        
        scenario['teams'] = teams_data
        return scenario
    
    @staticmethod
    def build_user_journey_scenario():
        """Build scenario for testing complete user journey"""
        scenario = ScenarioBuilder.build_active_competition_with_challenges()
        
        # Create a new user (not part of any team yet)
        new_user = TestDataFactory.create_user(
            username='journeyuser',
            email='journey@test.com',
            first_name='Journey',
            last_name='Tester'
        )
        
        # Create some existing teams they could join
        existing_teams = []
        for i in range(3):
            team, members = TestDataFactory.create_team_with_members(
                f'Existing Team {i+1}',
                member_count=2
            )
            existing_teams.append((team, members))
        
        scenario['new_user'] = new_user
        scenario['existing_teams'] = existing_teams
        return scenario


class AssertionHelpers:
    """Helper methods for common test assertions"""
    
    @staticmethod
    def assert_user_in_team(test_case, user, team):
        """Assert that a user is a member of a team"""
        test_case.assertIn(user, team.members.all(),
                          f'User {user.username} should be in team {team.name}')
    
    @staticmethod
    def assert_user_not_in_team(test_case, user, team):
        """Assert that a user is not a member of a team"""
        test_case.assertNotIn(user, team.members.all(),
                             f'User {user.username} should not be in team {team.name}')
    
    @staticmethod
    def assert_submission_correct(test_case, user, challenge, expected=True):
        """Assert that a user has a correct submission for a challenge"""
        submission = Submission.objects.filter(
            user=user, challenge=challenge, correct=expected
        ).first()
        test_case.assertIsNotNone(submission,
                                 f'User {user.username} should have correct={expected} '
                                 f'submission for {challenge.title}')
        return submission
    
    @staticmethod
    def assert_team_score(test_case, team, expected_score):
        """Assert that a team has the expected total score"""
        actual_score = sum(
            s.challenge.value for s in Submission.objects.filter(
                team=team, correct=True
            )
        )
        test_case.assertEqual(actual_score, expected_score,
                             f'Team {team.name} should have score {expected_score}, '
                             f'but has {actual_score}')
    
    @staticmethod
    def assert_hint_unlocked(test_case, user, hint):
        """Assert that a user has unlocked a specific hint"""
        unlock = HintUnlock.objects.filter(user=user, hint=hint).first()
        test_case.assertIsNotNone(unlock,
                                 f'User {user.username} should have unlocked hint '
                                 f'for {hint.challenge.title}')
        return unlock
    
    @staticmethod
    def assert_profile_exists(test_case, user):
        """Assert that a user profile exists and is properly configured"""
        try:
            profile = UserProfile.objects.get(user=user)
            test_case.assertIsNotNone(profile.created_at,
                                     f'Profile for {user.username} should have created_at timestamp')
            return profile
        except UserProfile.DoesNotExist:
            test_case.fail(f'Profile should exist for user {user.username}')


class MockData:
    """Mock data generators for testing"""
    
    SAMPLE_FLAGS = [
        'flag{sample_web_flag}',
        'FLAG{CRYPTO_CHALLENGE}',
        'flag{binary_exploitation_101}',
        'FLAG{Reverse_Engineering}',
        'flag{forensics_investigation}',
        'FLAG{NETWORK_ANALYSIS}',
        'flag{social_engineering_awareness}',
        'FLAG{MOBILE_SECURITY}'
    ]
    
    CHALLENGE_DESCRIPTIONS = [
        'Find the vulnerability in this web application and exploit it to retrieve the flag.',
        'Decrypt the given ciphertext to reveal the hidden flag.',
        'Analyze the binary and find a way to execute your payload.',
        'Reverse engineer the application to understand its functionality.',
        'Examine the forensic image to find traces of malicious activity.',
        'Analyze the network traffic capture to identify the attack.',
        'Use social engineering techniques to gather information.',
        'Find security weaknesses in the mobile application.'
    ]
    
    TEAM_NAMES = [
        'Cyber Guardians',
        'Binary Exploiters',
        'Crypto Crackers',
        'Web Warriors',
        'Forensic Investigators',
        'Social Engineers',
        'Mobile Defenders',
        'Network Ninjas',
        'Reverse Engineers',
        'Malware Hunters'
    ]
    
    UNIVERSITY_AFFILIATIONS = [
        'MIT - Massachusetts Institute of Technology',
        'Stanford University',
        'UC Berkeley',
        'Carnegie Mellon University',
        'Georgia Tech',
        'University of Washington',
        'University of Texas at Austin',
        'Princeton University',
        'Harvard University',
        'Caltech'
    ]
    
    @staticmethod
    def get_random_flag():
        """Get a random sample flag"""
        return random.choice(MockData.SAMPLE_FLAGS)
    
    @staticmethod
    def get_random_challenge_description():
        """Get a random challenge description"""
        return random.choice(MockData.CHALLENGE_DESCRIPTIONS)
    
    @staticmethod
    def get_random_team_name():
        """Get a random team name"""
        return random.choice(MockData.TEAM_NAMES)
    
    @staticmethod
    def get_random_affiliation():
        """Get a random university affiliation"""
        return random.choice(MockData.UNIVERSITY_AFFILIATIONS)
