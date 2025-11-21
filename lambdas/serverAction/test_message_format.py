#!/usr/bin/env python3
"""
Unit tests for SQS message format
Tests that messages contain all required fields and optional fields when provided
"""
import sys
import os
import unittest
import json
from unittest.mock import Mock, patch

# Mock environment variables before importing
os.environ['TAG_APP_VALUE'] = 'minecraft-dashboard'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_test123'
os.environ['SERVER_ACTION_QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'

# Mock the Lambda layers before importing index
from unittest.mock import MagicMock

# Create proper mock for utilHelper with response method
class MockUtils:
    @staticmethod
    def response(status_code, body):
        """Mock response method that returns proper dict structure"""
        return {
            'statusCode': status_code,
            'body': json.dumps(body)
        }

mock_util_helper = MagicMock()
mock_util_helper.Utils = MockUtils
sys.modules['utilHelper'] = mock_util_helper
sys.modules['authHelper'] = MagicMock()
sys.modules['ec2Helper'] = MagicMock()

# Add parent directory to path to import the Lambda function
sys.path.insert(0, os.path.dirname(__file__))
import index


class TestMessageFormat(unittest.TestCase):
    """Unit tests for SQS message format"""
    
    @patch.object(index, 'sqs_client')
    @patch.object(index, 'send_status_to_appsync')
    def test_message_contains_required_fields(self, mock_appsync, mock_sqs):
        """Test that queued message contains all required fields"""
        mock_sqs.send_message = Mock(return_value={'MessageId': 'test-id'})
        mock_appsync.return_value = True
        
        # Call send_to_queue
        response = index.send_to_queue(
            action='start',
            instance_id='i-1234567890abcdef0'
        )
        
        # Verify SQS was called
        mock_sqs.send_message.assert_called_once()
        
        # Get the message body
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args[1]['MessageBody'])
        
        # Verify required fields are present
        self.assertIn('action', message_body)
        self.assertIn('instanceId', message_body)
        self.assertIn('timestamp', message_body)
        
        # Verify values are correct
        self.assertEqual(message_body['action'], 'start')
        self.assertEqual(message_body['instanceId'], 'i-1234567890abcdef0')
        self.assertIsInstance(message_body['timestamp'], int)
    
    @patch.object(index, 'sqs_client')
    @patch.object(index, 'send_status_to_appsync')
    def test_message_includes_optional_fields_when_provided(self, mock_appsync, mock_sqs):
        """Test that optional fields are included when provided"""
        mock_sqs.send_message = Mock(return_value={'MessageId': 'test-id'})
        mock_appsync.return_value = True
        
        arguments = {'shutdownMethod': 'cpu', 'alarmThreshold': 5.0}
        user_email = 'test@example.com'
        
        # Call send_to_queue with optional fields
        response = index.send_to_queue(
            action='start',
            instance_id='i-1234567890abcdef0',
            arguments=arguments,
            user_email=user_email
        )
        
        # Get the message body
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args[1]['MessageBody'])
        
        # Verify optional fields are present
        self.assertIn('arguments', message_body)
        self.assertIn('userEmail', message_body)
        
        # Verify values are correct
        self.assertEqual(message_body['arguments'], arguments)
        self.assertEqual(message_body['userEmail'], user_email)
    
    @patch.object(index, 'sqs_client')
    @patch.object(index, 'send_status_to_appsync')
    def test_message_excludes_optional_fields_when_not_provided(self, mock_appsync, mock_sqs):
        """Test that optional fields are excluded when not provided"""
        mock_sqs.send_message = Mock(return_value={'MessageId': 'test-id'})
        mock_appsync.return_value = True
        
        # Call send_to_queue without optional fields
        response = index.send_to_queue(
            action='start',
            instance_id='i-1234567890abcdef0'
        )
        
        # Get the message body
        call_args = mock_sqs.send_message.call_args
        message_body = json.loads(call_args[1]['MessageBody'])
        
        # Verify optional fields are NOT present
        self.assertNotIn('arguments', message_body)
        self.assertNotIn('userEmail', message_body)
    
    @patch.object(index, 'sqs_client')
    @patch.object(index, 'send_status_to_appsync')
    def test_validation_error_returns_400(self, mock_appsync, mock_sqs):
        """Test that validation errors return 400 status"""
        mock_sqs.send_message = Mock(return_value={'MessageId': 'test-id'})
        mock_appsync.return_value = True
        
        # Call send_to_queue with invalid action
        response = index.send_to_queue(
            action='invalidAction',
            instance_id='i-1234567890abcdef0'
        )
        
        # Verify response is 400
        self.assertEqual(response['statusCode'], 400)
        
        # Verify SQS was NOT called
        mock_sqs.send_message.assert_not_called()
    
    @patch.object(index, 'sqs_client')
    @patch.object(index, 'send_status_to_appsync')
    def test_successful_queue_returns_202(self, mock_appsync, mock_sqs):
        """Test that successful queueing returns 202 status"""
        mock_sqs.send_message = Mock(return_value={'MessageId': 'test-id'})
        mock_appsync.return_value = True
        
        # Call send_to_queue
        response = index.send_to_queue(
            action='start',
            instance_id='i-1234567890abcdef0'
        )
        
        # Verify response is 202
        self.assertEqual(response['statusCode'], 202)


if __name__ == '__main__':
    unittest.main()
