#!/usr/bin/env python3
"""
Property-based test for queue message completeness
Tests that all queued messages contain required fields and preserve optional fields

**Feature: async-server-actions, Property 2: Queue message completeness**
**Validates: Requirements 1.2**
"""
import sys
import os
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume

# Mock environment variables before importing
os.environ['TAG_APP_VALUE'] = 'minecraft-dashboard'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['COGNITO_USER_POOL_ID'] = 'us-east-1_test123'
os.environ['SERVER_ACTION_QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/123456789012/test-queue'
os.environ['APPSYNC_URL'] = 'https://test.appsync-api.us-east-1.amazonaws.com/graphql'

# Mock the Lambda layers before importing index
# Create proper mock for utilHelper with response method
class MockUtils:
    @staticmethod
    def response(status_code, body):
        """Mock response method that returns proper dict structure"""
        return {
            'statusCode': status_code,
            'body': json.dumps(body)
        }
    
    @staticmethod
    def check_user_authorization(cognito_groups, instance_id, user_email, ec2_utils):
        """Mock authorization check"""
        return ('admin' in cognito_groups, 'admin_group' if 'admin' in cognito_groups else None)

mock_util_helper = MagicMock()
mock_util_helper.Utils = MockUtils
sys.modules['utilHelper'] = mock_util_helper

sys.modules['authHelper'] = MagicMock()
sys.modules['ec2Helper'] = MagicMock()

# Add parent directory to path to import the Lambda function
sys.path.insert(0, os.path.dirname(__file__))
import index

# Define valid actions for testing
VALID_ACTIONS = [
    'start', 'stop', 'restart',
    'startServer', 'stopServer', 'restartServer',
    'fixServerRole', 'putServerConfig', 'updateServerConfig'
]


class TestQueueMessageCompletenessProperty(unittest.TestCase):
    """
    Property-based test suite for queue message completeness
    
    **Feature: async-server-actions, Property 2: Queue message completeness**
    **Validates: Requirements 1.2**
    """
    
    @given(
        action=st.sampled_from(VALID_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
    )
    @settings(max_examples=100)
    def test_message_contains_all_required_fields(self, action, instance_id):
        """
        Property Test: Message Contains All Required Fields
        
        For any queued action message, the message should contain all required
        fields: action, instanceId, and timestamp.
        
        **Feature: async-server-actions, Property 2: Queue message completeness**
        **Validates: Requirements 1.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Call send_to_queue
                response = index.send_to_queue(
                    action=action,
                    instance_id=instance_id
                )
                
                # Verify the response is 202 (queued)
                self.assertEqual(
                    response['statusCode'], 202,
                    f"send_to_queue should return 202 status for action '{action}'"
                )
                
                # Verify SQS send_message was called
                mock_sqs.send_message.assert_called_once()
                
                # Get the message body
                call_args = mock_sqs.send_message.call_args
                message_body = json.loads(call_args[1]['MessageBody'])
                
                # Verify all required fields are present
                self.assertIn(
                    'action', message_body,
                    f"Message for action '{action}' must contain 'action' field"
                )
                self.assertIn(
                    'instanceId', message_body,
                    f"Message for action '{action}' must contain 'instanceId' field"
                )
                self.assertIn(
                    'timestamp', message_body,
                    f"Message for action '{action}' must contain 'timestamp' field"
                )
                
                # Verify the values are correct
                self.assertEqual(
                    message_body['action'], action,
                    f"Message 'action' field should match requested action '{action}'"
                )
                self.assertEqual(
                    message_body['instanceId'], instance_id,
                    f"Message 'instanceId' field should match '{instance_id}'"
                )
                self.assertIsInstance(
                    message_body['timestamp'], int,
                    "Message 'timestamp' field must be an integer"
                )
                self.assertGreater(
                    message_body['timestamp'], 0,
                    "Message 'timestamp' field must be positive"
                )
    
    @given(
        action=st.sampled_from(VALID_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_message_preserves_user_email_when_provided(self, action, instance_id, user_email):
        """
        Property Test: Message Preserves User Email When Provided
        
        For any queued action message with a user email, the message should
        include the userEmail field with the correct value.
        
        **Feature: async-server-actions, Property 2: Queue message completeness**
        **Validates: Requirements 1.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Call send_to_queue with user_email
                response = index.send_to_queue(
                    action=action,
                    instance_id=instance_id,
                    user_email=user_email
                )
                
                # Verify the response is 202 (queued)
                self.assertEqual(response['statusCode'], 202)
                
                # Get the message body
                call_args = mock_sqs.send_message.call_args
                message_body = json.loads(call_args[1]['MessageBody'])
                
                # Verify userEmail field is present and correct
                self.assertIn(
                    'userEmail', message_body,
                    f"Message with user_email should contain 'userEmail' field"
                )
                self.assertEqual(
                    message_body['userEmail'], user_email,
                    f"Message 'userEmail' field should match provided email '{user_email}'"
                )
    
    @given(
        action=st.sampled_from(VALID_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        shutdown_method=st.sampled_from(['cpu', 'connections', 'schedule']),
        alarm_threshold=st.floats(min_value=0.1, max_value=100.0),
        alarm_evaluation_period=st.integers(min_value=1, max_value=60),
        run_command=st.text(min_size=1, max_size=100),
        work_dir=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_message_preserves_arguments_when_provided(
        self, action, instance_id, shutdown_method, alarm_threshold, 
        alarm_evaluation_period, run_command, work_dir
    ):
        """
        Property Test: Message Preserves Arguments When Provided
        
        For any queued action message with arguments, the message should
        include the arguments field with all provided values preserved.
        
        **Feature: async-server-actions, Property 2: Queue message completeness**
        **Validates: Requirements 1.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Create arguments dict
                arguments = {
                    'shutdownMethod': shutdown_method,
                    'alarmThreshold': alarm_threshold,
                    'alarmEvaluationPeriod': alarm_evaluation_period,
                    'runCommand': run_command,
                    'workDir': work_dir
                }
                
                # Call send_to_queue with arguments
                response = index.send_to_queue(
                    action=action,
                    instance_id=instance_id,
                    arguments=arguments
                )
                
                # Verify the response is 202 (queued)
                self.assertEqual(response['statusCode'], 202)
                
                # Get the message body
                call_args = mock_sqs.send_message.call_args
                message_body = json.loads(call_args[1]['MessageBody'])
                
                # Verify arguments field is present
                self.assertIn(
                    'arguments', message_body,
                    f"Message with arguments should contain 'arguments' field"
                )
                
                # Verify all argument values are preserved
                self.assertEqual(
                    message_body['arguments'], arguments,
                    f"Message 'arguments' field should match provided arguments"
                )
    
    @given(
        action=st.sampled_from(VALID_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
        shutdown_method=st.sampled_from(['cpu', 'connections', 'schedule']),
        alarm_threshold=st.floats(min_value=0.1, max_value=100.0),
    )
    @settings(max_examples=100)
    def test_message_preserves_all_fields_when_all_provided(
        self, action, instance_id, user_email, shutdown_method, alarm_threshold
    ):
        """
        Property Test: Message Preserves All Fields When All Provided
        
        For any queued action message with all optional fields provided,
        the message should include all required fields (action, instanceId,
        timestamp) and all provided optional fields (arguments, userEmail).
        
        **Feature: async-server-actions, Property 2: Queue message completeness**
        **Validates: Requirements 1.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Create arguments dict
                arguments = {
                    'shutdownMethod': shutdown_method,
                    'alarmThreshold': alarm_threshold,
                }
                
                # Call send_to_queue with all fields
                response = index.send_to_queue(
                    action=action,
                    instance_id=instance_id,
                    arguments=arguments,
                    user_email=user_email
                )
                
                # Verify the response is 202 (queued)
                self.assertEqual(response['statusCode'], 202)
                
                # Get the message body
                call_args = mock_sqs.send_message.call_args
                message_body = json.loads(call_args[1]['MessageBody'])
                
                # Verify all required fields are present
                self.assertIn('action', message_body)
                self.assertIn('instanceId', message_body)
                self.assertIn('timestamp', message_body)
                
                # Verify all optional fields are present
                self.assertIn('arguments', message_body)
                self.assertIn('userEmail', message_body)
                
                # Verify all values are correct
                self.assertEqual(message_body['action'], action)
                self.assertEqual(message_body['instanceId'], instance_id)
                self.assertEqual(message_body['arguments'], arguments)
                self.assertEqual(message_body['userEmail'], user_email)
                self.assertIsInstance(message_body['timestamp'], int)
    
    @given(
        action=st.sampled_from(VALID_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
    )
    @settings(max_examples=100)
    def test_message_excludes_optional_fields_when_not_provided(self, action, instance_id):
        """
        Property Test: Message Excludes Optional Fields When Not Provided
        
        For any queued action message without optional fields, the message
        should only contain required fields and NOT include empty optional
        fields.
        
        **Feature: async-server-actions, Property 2: Queue message completeness**
        **Validates: Requirements 1.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Call send_to_queue without optional fields
                response = index.send_to_queue(
                    action=action,
                    instance_id=instance_id
                )
                
                # Verify the response is 202 (queued)
                self.assertEqual(response['statusCode'], 202)
                
                # Get the message body
                call_args = mock_sqs.send_message.call_args
                message_body = json.loads(call_args[1]['MessageBody'])
                
                # Verify required fields are present
                self.assertIn('action', message_body)
                self.assertIn('instanceId', message_body)
                self.assertIn('timestamp', message_body)
                
                # Verify optional fields are NOT present
                self.assertNotIn(
                    'arguments', message_body,
                    "Message without arguments should not contain 'arguments' field"
                )
                self.assertNotIn(
                    'userEmail', message_body,
                    "Message without user_email should not contain 'userEmail' field"
                )
    
    @given(
        action=st.sampled_from(VALID_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
    )
    @settings(max_examples=100)
    def test_message_has_valid_json_structure(self, action, instance_id):
        """
        Property Test: Message Has Valid JSON Structure
        
        For any queued action message, the message body should be valid JSON
        that can be parsed by the ServerActionProcessor.
        
        **Feature: async-server-actions, Property 2: Queue message completeness**
        **Validates: Requirements 1.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Call send_to_queue
                response = index.send_to_queue(
                    action=action,
                    instance_id=instance_id
                )
                
                # Verify the response is 202 (queued)
                self.assertEqual(response['statusCode'], 202)
                
                # Get the message body
                call_args = mock_sqs.send_message.call_args
                message_body_str = call_args[1]['MessageBody']
                
                # Verify it's valid JSON
                try:
                    message_body = json.loads(message_body_str)
                except json.JSONDecodeError as e:
                    self.fail(f"Message body is not valid JSON: {e}")
                
                # Verify it's a dictionary
                self.assertIsInstance(
                    message_body, dict,
                    "Message body should be a JSON object (dictionary)"
                )


if __name__ == '__main__':
    unittest.main()
