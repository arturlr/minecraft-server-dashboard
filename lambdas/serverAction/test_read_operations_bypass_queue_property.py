#!/usr/bin/env python3
"""
Property-based test for read operations bypassing the queue
Tests that read operations are processed synchronously without queueing to SQS

**Feature: async-server-actions, Property 3: Read operations bypass queue**
**Validates: Requirements 1.4**
"""
import sys
import os
import unittest
import json
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings

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

# Define read operations that should bypass the queue
READ_OPERATIONS = [
    'getServerConfig',
    'getServerUsers',
]


class TestReadOperationsBypassQueueProperty(unittest.TestCase):
    """
    Property-based test suite for read operations bypassing the queue
    
    **Feature: async-server-actions, Property 3: Read operations bypass queue**
    **Validates: Requirements 1.4**
    """
    
    @given(
        action=st.sampled_from(READ_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_read_operations_bypass_queue(self, action, instance_id, user_email):
        """
        Property Test: Read Operations Bypass Queue
        
        For any read operation (getServerConfig, getServerUsers), the ServerAction
        Lambda should process it synchronously and return results immediately
        without queueing to SQS.
        
        **Feature: async-server-actions, Property 3: Read operations bypass queue**
        **Validates: Requirements 1.4**
        """
        # Mock the SQS client to track if it's called
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock(return_value={'MessageId': 'test-message-id'})
            
            # Mock the read operation handlers to return test data
            with patch.object(index, 'handle_get_server_config') as mock_get_config:
                test_config = {
                    'shutdownMethod': 'cpu',
                    'alarmThreshold': 5.0,
                    'runCommand': '/opt/minecraft/start.sh'
                }
                mock_get_config.return_value = test_config
                
                with patch.object(index, 'handle_get_server_users') as mock_get_users:
                    test_users = [
                        {'email': 'user1@example.com'},
                        {'email': 'user2@example.com'}
                    ]
                    mock_get_users.return_value = test_users
                    
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
                            
                            # Verify SQS send_message was NOT called
                            mock_sqs.send_message.assert_not_called()
                            
                            # Verify the appropriate handler was called synchronously
                            if action.lower() == 'getserverconfig':
                                mock_get_config.assert_called_once_with(instance_id)
                                # Verify response contains the config data
                                self.assertEqual(
                                    response, test_config,
                                    f"Read operation '{action}' should return data immediately"
                                )
                            elif action.lower() == 'getserverusers':
                                mock_get_users.assert_called_once_with(instance_id)
                                # Verify response contains the users data
                                self.assertEqual(
                                    response, test_users,
                                    f"Read operation '{action}' should return data immediately"
                                )
    
    @given(
        action=st.sampled_from(READ_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_read_operations_no_processing_status(self, action, instance_id, user_email):
        """
        Property Test: Read Operations Don't Send PROCESSING Status
        
        For any read operation, the ServerAction Lambda should NOT send a
        PROCESSING status to AppSync since the operation completes immediately.
        
        **Feature: async-server-actions, Property 3: Read operations bypass queue**
        **Validates: Requirements 1.4**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock()
            
            # Mock the AppSync status update to track if it's called
            with patch.object(index, 'send_status_to_appsync') as mock_appsync:
                mock_appsync.return_value = True
                
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
                                
                                # Verify AppSync status update was NOT called
                                mock_appsync.assert_not_called()
                                
                                # Verify SQS was not called
                                mock_sqs.send_message.assert_not_called()
    
    @given(
        action=st.sampled_from(READ_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_read_operations_return_immediately(self, action, instance_id, user_email):
        """
        Property Test: Read Operations Return Immediately
        
        For any read operation, the ServerAction Lambda should return the
        result directly without a 202 status code (which indicates async processing).
        
        **Feature: async-server-actions, Property 3: Read operations bypass queue**
        **Validates: Requirements 1.4**
        """
        # Mock the SQS client
        with patch.object(index, 'sqs_client') as mock_sqs:
            mock_sqs.send_message = Mock()
            
            # Mock the read operation handlers
            with patch.object(index, 'handle_get_server_config') as mock_get_config:
                test_config = {'shutdownMethod': 'cpu', 'alarmThreshold': 5.0}
                mock_get_config.return_value = test_config
                
                with patch.object(index, 'handle_get_server_users') as mock_get_users:
                    test_users = [{'email': 'user1@example.com'}]
                    mock_get_users.return_value = test_users
                    
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
                            
                            # Verify response is NOT a 202 status (async processing)
                            if isinstance(response, dict) and 'statusCode' in response:
                                self.assertNotEqual(
                                    response['statusCode'], 202,
                                    f"Read operation '{action}' should not return 202 (async) status"
                                )
                            
                            # Verify response contains actual data, not just a queued message
                            if action.lower() == 'getserverconfig':
                                self.assertEqual(response, test_config)
                            elif action.lower() == 'getserverusers':
                                self.assertEqual(response, test_users)
    
    @given(
        action=st.sampled_from(READ_OPERATIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_read_operations_call_correct_handler(self, action, instance_id, user_email):
        """
        Property Test: Read Operations Call Correct Handler
        
        For any read operation, the ServerAction Lambda should route to the
        correct synchronous handler function (handle_get_server_config or
        handle_get_server_users).
        
        **Feature: async-server-actions, Property 3: Read operations bypass queue**
        **Validates: Requirements 1.4**
        """
        # Mock the read operation handlers
        with patch.object(index, 'handle_get_server_config') as mock_get_config:
            mock_get_config.return_value = {'config': 'test'}
            
            with patch.object(index, 'handle_get_server_users') as mock_get_users:
                mock_get_users.return_value = ['user1']
                
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
                        
                        # Verify the correct handler was called based on action
                        if action.lower() == 'getserverconfig':
                            mock_get_config.assert_called_once_with(instance_id)
                            mock_get_users.assert_not_called()
                        elif action.lower() == 'getserverusers':
                            mock_get_users.assert_called_once_with(instance_id)
                            mock_get_config.assert_not_called()


if __name__ == '__main__':
    unittest.main()
