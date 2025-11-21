#!/usr/bin/env python3
"""
Unit tests for SQS message validation
Tests the validate_queue_message function
"""
import sys
import os
import unittest

# Mock environment variables before importing
os.environ['TAG_APP_VALUE'] = 'minecraft-dashboard'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_test123'
os.environ['SERVER_ACTION_QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'

# Mock the Lambda layers before importing index
from unittest.mock import MagicMock
sys.modules['utilHelper'] = MagicMock()
sys.modules['authHelper'] = MagicMock()
sys.modules['ec2Helper'] = MagicMock()

# Add parent directory to path to import the Lambda function
sys.path.insert(0, os.path.dirname(__file__))
import index


class TestMessageValidation(unittest.TestCase):
    """Unit tests for message validation"""
    
    def test_valid_message_with_all_fields(self):
        """Test validation passes with all fields provided"""
        is_valid, error = index.validate_queue_message(
            action='start',
            instance_id='i-1234567890abcdef0',
            arguments={'shutdownMethod': 'cpu'},
            user_email='test@example.com'
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_valid_message_with_required_fields_only(self):
        """Test validation passes with only required fields"""
        is_valid, error = index.validate_queue_message(
            action='stop',
            instance_id='i-1234567890abcdef0'
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_missing_action(self):
        """Test validation fails when action is missing"""
        is_valid, error = index.validate_queue_message(
            action=None,
            instance_id='i-1234567890abcdef0'
        )
        self.assertFalse(is_valid)
        self.assertIn('Action is required', error)
    
    def test_empty_action(self):
        """Test validation fails when action is empty string"""
        is_valid, error = index.validate_queue_message(
            action='',
            instance_id='i-1234567890abcdef0'
        )
        self.assertFalse(is_valid)
        self.assertIn('Action is required', error)
    
    def test_missing_instance_id(self):
        """Test validation fails when instance_id is missing"""
        is_valid, error = index.validate_queue_message(
            action='start',
            instance_id=None
        )
        self.assertFalse(is_valid)
        self.assertIn('Instance ID is required', error)
    
    def test_empty_instance_id(self):
        """Test validation fails when instance_id is empty string"""
        is_valid, error = index.validate_queue_message(
            action='start',
            instance_id=''
        )
        self.assertFalse(is_valid)
        self.assertIn('Instance ID is required', error)
    
    def test_invalid_action_type(self):
        """Test validation fails for invalid action"""
        is_valid, error = index.validate_queue_message(
            action='invalidAction',
            instance_id='i-1234567890abcdef0'
        )
        self.assertFalse(is_valid)
        self.assertIn('Invalid action', error)
    
    def test_valid_action_variations(self):
        """Test all valid action variations"""
        valid_actions = [
            'start', 'stop', 'restart',
            'startServer', 'stopServer', 'restartServer',
            'fixServerRole', 'putServerConfig', 'updateServerConfig'
        ]
        
        for action in valid_actions:
            is_valid, error = index.validate_queue_message(
                action=action,
                instance_id='i-1234567890abcdef0'
            )
            self.assertTrue(is_valid, f"Action '{action}' should be valid")
            self.assertIsNone(error)
    
    def test_case_insensitive_action_validation(self):
        """Test action validation is case-insensitive"""
        is_valid, error = index.validate_queue_message(
            action='START',
            instance_id='i-1234567890abcdef0'
        )
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_invalid_arguments_type(self):
        """Test validation fails when arguments is not a dict"""
        is_valid, error = index.validate_queue_message(
            action='start',
            instance_id='i-1234567890abcdef0',
            arguments='not a dict'
        )
        self.assertFalse(is_valid)
        self.assertIn('Arguments must be a dictionary', error)
    
    def test_invalid_user_email_type(self):
        """Test validation fails when user_email is not a string"""
        is_valid, error = index.validate_queue_message(
            action='start',
            instance_id='i-1234567890abcdef0',
            user_email=123
        )
        self.assertFalse(is_valid)
        self.assertIn('User email must be a non-empty string', error)
    
    def test_empty_user_email(self):
        """Test validation fails when user_email is empty string"""
        is_valid, error = index.validate_queue_message(
            action='start',
            instance_id='i-1234567890abcdef0',
            user_email=''
        )
        self.assertFalse(is_valid)
        self.assertIn('User email must be a non-empty string', error)


if __name__ == '__main__':
    unittest.main()
