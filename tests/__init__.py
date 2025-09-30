"""
Tests package for the CTF platform

This package contains comprehensive tests for all components of the CTF platform:

- test_models.py: Unit tests for all Django models
- test_views.py: Tests for all views and HTTP endpoints  
- test_forms.py: Form validation and processing tests
- test_integration.py: End-to-end workflow and integration tests
- test_utils.py: Test utilities, factories, and helper functions
- test_runner.py: Custom test runner with enhanced reporting

Usage:
    # Run all tests
    python manage.py test

    # Run specific test module
    python manage.py test tests.test_models

    # Run with coverage
    python manage.py test --coverage

    # Run custom test runner
    python manage.py run_ctf_tests --coverage --performance
"""

# Import test utilities for easy access
from .test_utils import TestDataFactory, ScenarioBuilder, AssertionHelpers, MockData

__all__ = [
    'TestDataFactory',
    'ScenarioBuilder', 
    'AssertionHelpers',
    'MockData'
]
