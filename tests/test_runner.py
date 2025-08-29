"""
Test runner configuration and management commands for CTF platform tests
"""
import os
import sys
import unittest
from io import StringIO
from django.test.utils import get_runner
from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.test import TestCase


class Command(BaseCommand):
    """Custom management command to run test suite with enhanced reporting"""
    
    help = 'Run the CTF platform test suite with detailed reporting'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--pattern',
            type=str,
            help='Test file pattern to run (e.g., test_models, test_views)',
            default='test_*.py'
        )
        parser.add_argument(
            '--verbosity',
            type=int,
            choices=[0, 1, 2, 3],
            default=2,
            help='Verbosity level (0-3)'
        )
        parser.add_argument(
            '--failfast',
            action='store_true',
            help='Stop on first test failure'
        )
        parser.add_argument(
            '--keepdb',
            action='store_true',
            help='Keep test database after test run'
        )
        parser.add_argument(
            '--coverage',
            action='store_true',
            help='Generate coverage report'
        )
        parser.add_argument(
            '--performance',
            action='store_true',
            help='Run performance tests'
        )
    
    def handle(self, *args, **options):
        """Execute the test command"""
        
        self.stdout.write(
            self.style.SUCCESS('Starting CTF Platform Test Suite')
        )
        
        # Set test environment
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ctfd_clone.settings')
        
        # Configure test runner
        test_runner_class = get_runner(settings)
        test_runner = test_runner_class(
            verbosity=options['verbosity'],
            interactive=False,
            failfast=options['failfast'],
            keepdb=options['keepdb']
        )
        
        # Determine which tests to run
        if options['pattern'] == 'test_*.py':
            test_labels = ['tests']
        else:
            test_labels = [f'tests.{options["pattern"].replace(".py", "")}']
        
        self.stdout.write(f'Running tests: {", ".join(test_labels)}')
        
        # Run coverage if requested
        if options['coverage']:
            try:
                import coverage
                cov = coverage.Coverage()
                cov.start()
                self.stdout.write('Coverage tracking enabled')
            except ImportError:
                self.stdout.write(
                    self.style.WARNING('Coverage package not installed. Install with: pip install coverage')
                )
                options['coverage'] = False
        
        # Run tests
        try:
            failures = test_runner.run_tests(test_labels)
            
            # Generate coverage report
            if options['coverage'] and 'cov' in locals():
                cov.stop()
                cov.save()
                
                self.stdout.write('\n' + '='*50)
                self.stdout.write('COVERAGE REPORT')
                self.stdout.write('='*50)
                
                # Console report
                output = StringIO()
                cov.report(file=output)
                self.stdout.write(output.getvalue())
                
                # HTML report
                cov.html_report(directory='htmlcov')
                self.stdout.write(
                    self.style.SUCCESS('\nHTML coverage report generated in htmlcov/')
                )
            
            # Performance tests
            if options['performance']:
                self.stdout.write('\n' + '='*50)
                self.stdout.write('RUNNING PERFORMANCE TESTS')
                self.stdout.write('='*50)
                self._run_performance_tests()
            
            # Summary
            if failures:
                self.stdout.write(
                    self.style.ERROR(f'\nTest suite completed with {failures} failures')
                )
                sys.exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS('\nAll tests passed successfully!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error running tests: {str(e)}')
            )
            sys.exit(1)
    
    def _run_performance_tests(self):
        """Run performance benchmarks"""
        from django.test import Client
        from django.contrib.auth.models import User
        from ctf.models import Challenge, Category
        import time
        
        # Create test data
        category = Category.objects.create(name='Perf Test', description='Performance testing')
        challenge = Challenge.objects.create(
            title='Performance Challenge',
            description='Test challenge',
            category=category,
            value=100,
            flag='flag{perf}',
            case_sensitive=False
        )
        
        user = User.objects.create_user(
            username='perfuser',
            email='perf@test.com',
            password='perfpass123'
        )
        
        client = Client()
        client.login(username='perfuser', password='perfpass123')
        
        # Test page load times
        performance_tests = [
            ('Home Page', '/'),
            ('Challenge List', '/challenges/'),
            ('Scoreboard', '/scoreboard/'),
        ]
        
        for test_name, url in performance_tests:
            start_time = time.time()
            response = client.get(url)
            end_time = time.time()
            
            load_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            status = 'PASS' if load_time < 1000 else 'SLOW'  # < 1 second
            if response.status_code != 200:
                status = 'FAIL'
            
            self.stdout.write(
                f'{test_name}: {load_time:.2f}ms [{status}]'
            )


class TestDatabaseManager:
    """Utility class for managing test databases"""
    
    @staticmethod
    def create_test_data():
        """Create comprehensive test data for manual testing"""
        from tests.test_utils import TestDataFactory, ScenarioBuilder
        
        print('Creating test competition scenario...')
        scenario = ScenarioBuilder.build_competition_with_scoreboard_data()
        
        print('Test data created successfully!')
        print(f'Competition: {scenario["settings"].competition_name}')
        print(f'Categories: {len(scenario["categories"])}')
        print(f'Challenges: {len(scenario["challenges"])}')
        print(f'Teams: {len(scenario["teams"])}')
        
        return scenario
    
    @staticmethod
    def cleanup_test_data():
        """Clean up test data from database"""
        from ctf.models import (
            CompetitionSettings, Category, Challenge, Team,
            UserProfile, Submission, Hint, HintUnlock
        )
        from django.contrib.auth.models import User
        
        print('Cleaning up test data...')
        
        # Delete in reverse order of dependencies
        HintUnlock.objects.all().delete()
        Submission.objects.all().delete()
        Hint.objects.all().delete()
        Challenge.objects.all().delete()
        Category.objects.all().delete()
        Team.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        CompetitionSettings.objects.all().delete()
        
        print('Test data cleaned up successfully!')


class CTFTestSuite(TestCase):
    """Main test suite runner class"""
    
    @classmethod
    def get_test_suite(cls):
        """Get complete test suite"""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        # Add all test modules
        test_modules = [
            'tests.test_models',
            'tests.test_views',
            'tests.test_forms',
            'tests.test_integration',
        ]
        
        for module in test_modules:
            try:
                tests = loader.loadTestsFromName(module)
                suite.addTests(tests)
            except ImportError as e:
                print(f'Warning: Could not import {module}: {e}')
        
        return suite
    
    @classmethod
    def run_test_suite(cls, verbosity=2):
        """Run the complete test suite"""
        suite = cls.get_test_suite()
        runner = unittest.TextTestRunner(verbosity=verbosity)
        result = runner.run(suite)
        
        return result.wasSuccessful()


# Custom test discovery for pytest compatibility
def pytest_configure(config):
    """Configure pytest for Django testing"""
    import django
    from django.conf import settings
    
    if not settings.configured:
        settings.configure(
            DEBUG=True,
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:'
                }
            },
            INSTALLED_APPS=[
                'django.contrib.admin',
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.sessions',
                'django.contrib.messages',
                'django.contrib.staticfiles',
                'ctf',
            ],
            SECRET_KEY='test-secret-key-for-testing-only',
            USE_TZ=True,
        )
    
    django.setup()


# Test configuration for continuous integration
class CITestRunner:
    """Test runner optimized for CI/CD environments"""
    
    @staticmethod
    def run_ci_tests():
        """Run tests with CI-optimized settings"""
        import subprocess
        import sys
        
        # Run tests with specific CI settings
        cmd = [
            sys.executable, 
            'manage.py', 
            'test',
            '--verbosity=1',
            '--failfast',
            '--keepdb'
        ]
        
        # Add coverage for CI
        if os.environ.get('CI_COVERAGE', 'false').lower() == 'true':
            cmd.extend(['--coverage'])
        
        try:
            result = subprocess.run(cmd, check=True)
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            print(f'CI Tests failed with return code: {e.returncode}')
            return False


if __name__ == '__main__':
    # Allow running this file directly for quick testing
    if len(sys.argv) > 1 and sys.argv[1] == 'create_data':
        TestDatabaseManager.create_test_data()
    elif len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        TestDatabaseManager.cleanup_test_data()
    elif len(sys.argv) > 1 and sys.argv[1] == 'ci':
        success = CITestRunner.run_ci_tests()
        sys.exit(0 if success else 1)
    else:
        # Run the test suite
        success = CTFTestSuite.run_test_suite()
        sys.exit(0 if success else 1)
