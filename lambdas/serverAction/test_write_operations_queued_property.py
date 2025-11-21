#!/usr/bin/env python3
"""
Property-based test for write operations always being queued
Tests that all write operations are sent to SQS queue when authorization succeeds

**Feature: async-server-actions, Property 4: Write operations always queued**
**Validates: Requirements 1.1**
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
        # Return True if user is in admin group
        return ('admin' in cognito_groups, 'admin_group' if 'admin' in cognito_groups else None)

mock_util_helper = MagicMock()
mock_util_helper.Utils = MockUtils
sys.modules['utilHelper'] = mock_util_helper

sys.modules['authHelper'] = MagicMock()
sys.modules['ec2Helper'] = MagicMock()

# Add parent directory to path to import the Lambda function
sys.path.insert(0, os.path.dirname(__file__))
import index

# Define write operations that should always be queued
WRITE_OPERATIONS = [
    'start',
    'stop', 
    'restart',
    'fixServerRole',
    'putServerConfig',
    'updateServerConfig',
    'startServer',
    'stopServer',
    'restartServer',
]

# Define read operations that should NOT be queued
READ_OPERATIONS = [
    'getServerConfig',
    'getServerUsers',
]


class TestWriteOperationsQueuedProperty(unittest.TestCase):
    """
    Property-based test suite for write operations queueing
    
    **Feature: async-server-actions, Property 4: Write operations always queued**
    **Validates: Requirements 1.1**
    """
    
    @given(
        action=st.sampled_from(WRITE_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_write_operations_always_queued(self, action, instance_id, user_email):
        """
        Property Test: Write Operations Always Queued
        
        For any write operation (start, stop, restart, fixServerRole, 
        putServerConfig, updateServerConfig), when authorization succeeds,
        the ServerAction Lambda should queue the request to SQS and return
        a 202 status.
        
        **Feature: async-server-actions, Property 4: Write operations always queued**
        **Validates: Requirements 1.1**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Create event with write operation
                event = {
                    'request': {
                        'headers': {
                            'authorization': 'Bearer test-token'
                        }
                    },
                    'arguments': {
                        'instanceId': instance_id,
                        'input': {
                            'id': instance_id,
                            'shutdownMethod': 'cpu',
                            'alarmThreshold': 5.0,
                        }
                    },
                    'identity': {
                        'groups': ['admin']
                    },
                    'info': {
                        'fieldName': action
                    }
                }
                
                # Mock auth helper
                with patch.object(index.auth, 'process_token') as mock_token:
                    mock_token.return_value = {
                        'email': user_email,
                        'sub': 'test-user-id'
                    }
                    
                    # Mock authorization check to succeed
                    with patch.object(index, 'check_authorization') as mock_auth:
                        mock_auth.return_value = True
                        
                        # Call the handler
                        response = index.handler(event, {})
                        
                        # Verify the response is 202 (queued)
                        self.assertEqual(
                            response['statusCode'], 202,
                            f"Write operation '{action}' should return 202 status when queued"
                        )
                        
                        # Verify SQS send_message was called
                        mock_sqs.send_message.assert_called_once()
                        
                        # Verify the message was sent to the correct queue
                        call_args = mock_sqs.send_message.call_args
                        self.assertEqual(
                            call_args[1]['QueueUrl'],
                            os.environ['SERVER_ACTION_QUEUE_URL'],
                            f"Write operation '{action}' should be sent to the configured queue"
                        )
                        
                        # Verify the message body contains required fields
                        message_body = json.loads(call_args[1]['MessageBody'])
                        self.assertIn('action', message_body, "Queued message must contain 'action' field")
                        self.assertIn('instanceId', message_body, "Queued message must contain 'instanceId' field")
                        self.assertIn('timestamp', message_body, "Queued message must contain 'timestamp' field")
                        
                        # Verify the action in the message matches the requested action
                        self.assertEqual(
                            message_body['action'], action,
                            f"Queued message action should match requested action '{action}'"
                        )
                        
                        # Verify the instance ID in the message matches
                        self.assertEqual(
                            message_body['instanceId'], instance_id,
                            f"Queued message instanceId should match '{instance_id}'"
                        )
                        
                        # Verify PROCESSING status was sent to AppSync
                        mock_appsync.assert_called_once()
                        appsync_call_args = mock_appsync.call_args
                        self.assertEqual(
                            appsync_call_args[1]['status'], 'PROCESSING',
                            f"Write operation '{action}' should send PROCESSING status to AppSync"
                        )
    
    @given(
        action=st.sampled_from(WRITE_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_write_operations_not_processed_directly(self, action, instance_id, user_email):
        """
        Property Test: Write Operations Not Processed Directly
        
        For any write operation, the ServerAction Lambda should NOT execute
        the operation directly (e.g., calling EC2 APIs). It should only queue
        the request.
        
        **Feature: async-server-actions, Property 4: Write operations always queued**
        **Validates: Requirements 1.1, 6.1**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the AppSync status update
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
                # Mock EC2 client to track if it's called
                with patch.object(index, 'ec2_client') as mock_ec2:
                    mock_ec2.start_instances = Mock()
                    mock_ec2.stop_instances = Mock()
                    mock_ec2.reboot_instances = Mock()
                    
                    # Create event with write operation
                    event = {
                        'request': {
                            'headers': {
                                'authorization': 'Bearer test-token'
                            }
                        },
                        'arguments': {
                            'instanceId': instance_id,
                        },
                        'identity': {
                            'groups': ['admin']
                        },
                        'info': {
                            'fieldName': action
                        }
                    }
                    
                    # Mock auth helper
                    with patch.object(index.auth, 'process_token') as mock_token:
                        mock_token.return_value = {
                            'email': user_email,
                            'sub': 'test-user-id'
                        }
                        
                        # Mock authorization check to succeed
                        with patch.object(index, 'check_authorization') as mock_auth:
                            mock_auth.return_value = True
                            
                            # Call the handler
                            response = index.handler(event, {})
                            
                            # Verify EC2 operations were NOT called
                            mock_ec2.start_instances.assert_not_called()
                            mock_ec2.stop_instances.assert_not_called()
                            mock_ec2.reboot_instances.assert_not_called()
                            
                            # Verify the operation was queued instead
                            mock_sqs.send_message.assert_called_once()
    
    @given(
        action=st.sampled_from(WRITE_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_unauthorized_write_operations_not_queued(self, action, instance_id, user_email):
        """
        Property Test: Unauthorized Write Operations Not Queued
        
        For any write operation, when authorization fails, the ServerAction
        Lambda should return 401 and NOT queue the request to SQS.
        
        **Feature: async-server-actions, Property 4: Write operations always queued**
        **Validates: Requirements 1.1, 7.2**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Create event with write operation
            event = {
                'request': {
                    'headers': {
                        'authorization': 'Bearer test-token'
                    }
                },
                'arguments': {
                    'instanceId': instance_id,
                },
                'identity': {
                    'groups': []  # No groups = not authorized
                },
                'info': {
                    'fieldName': action
                }
            }
            
            # Mock auth helper
            with patch.object(index.auth, 'process_token') as mock_token:
                mock_token.return_value = {
                    'email': user_email,
                    'sub': 'test-user-id'
                }
                
                # Mock authorization check to fail
                with patch.object(index, 'check_authorization') as mock_auth:
                    mock_auth.return_value = False
                    
                    # Call the handler
                    response = index.handler(event, {})
                    
                    # Verify the response is 401 (unauthorized)
                    self.assertEqual(
                        response['statusCode'], 401,
                        f"Unauthorized write operation '{action}' should return 401 status"
                    )
                    
                    # Verify SQS send_message was NOT called
                    mock_sqs.send_message.assert_not_called()
    
    @given(
        action=st.sampled_from(READ_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=50)
    def test_read_operations_not_queued(self, action, instance_id, user_email):
        """
        Property Test: Read Operations Not Queued
        
        For any read operation (getServerConfig, getServerUsers), the
        ServerAction Lambda should process it synchronously and NOT queue
        it to SQS.
        
        This test verifies the inverse property: read operations should
        bypass the queue.
        
        **Feature: async-server-actions, Property 4: Write operations always queued**
        **Validates: Requirements 1.4**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the read operation handlers
            with patch.object(index, 'handle_get_server_config') as mock_get_config:
                mock_get_config.return_value = {'config': 'test'}
                
                with patch.object(index, 'handle_get_server_users') as mock_get_users:
                    mock_get_users.return_value = ['user1', 'user2']
                    
                    # Create event with read operation
                    event = {
                        'request': {
                            'headers': {
                                'authorization': 'Bearer test-token'
                            }
                        },
                        'arguments': {
                            'instanceId': instance_id,
                        },
                        'identity': {
                            'groups': ['admin']
                        },
                        'info': {
                            'fieldName': action
                        }
                    }
                    
                    # Mock auth helper
                    with patch.object(index.auth, 'process_token') as mock_token:
                        mock_token.return_value = {
                            'email': user_email,
                            'sub': 'test-user-id'
                        }
                        
                        # Mock authorization check to succeed
                        with patch.object(index, 'check_authorization') as mock_auth:
                            mock_auth.return_value = True
                            
                            # Call the handler
                            response = index.handler(event, {})
                            
                            # Verify SQS send_message was NOT called for read operations
                            mock_sqs.send_message.assert_not_called()
                            
                            # Verify the appropriate handler was called
                            if action.lower() == 'getserverconfig':
                                mock_get_config.assert_called_once()
                            elif action.lower() == 'getserverusers':
                                mock_get_users.assert_called_once()


if __name__ == '__main__':
    unittest.main()
