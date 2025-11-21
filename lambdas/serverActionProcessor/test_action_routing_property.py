#!/usr/bin/env python3
"""
Property-based test for action routing correctness in ServerActionProcessor
Tests that messages are routed to the correct handler based on action type

**Feature: async-server-actions, Property 8: Action routing correctness**
**Validates: Requirements 4.2, 4.3, 4.4**
"""
import sys
import os
import unittest
import json
from unittest.mock import Mock, patch, MagicMock, call
from hypothesis import given, strategies as st, settings, assume

# Mock environment variables before importing
os.environ['TAG_APP_VALUE'] = 'minecraft-dashboard'
os.environ['APP_NAME'] = 'minecraft-dashboard'
os.environ['ENVIRONMENT_NAME'] = 'test'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['APPSYNC_URL'] = 'https://test.appsync-api.us-east-1.amazonaws.com/graphql'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'

# Mock boto3 before importing index
mock_boto3 = MagicMock()
mock_session = MagicMock()
mock_credentials = MagicMock()
mock_frozen_credentials = MagicMock()
mock_frozen_credentials.access_key = 'test-access-key'
mock_frozen_credentials.secret_key = 'test-secret-key'
mock_frozen_credentials.token = 'test-token'
mock_credentials.get_frozen_credentials.return_value = mock_frozen_credentials
mock_session.get_credentials.return_value = mock_credentials
mock_session.region_name = 'us-east-1'
mock_boto3.Session.return_value = mock_session
mock_boto3.client.return_value = MagicMock()
sys.modules['boto3'] = mock_boto3

# Mock the Lambda layers before importing index
sys.modules['ec2Helper'] = MagicMock()
sys.modules['utilHelper'] = MagicMock()

# Mock requests_aws4auth
sys.modules['requests_aws4auth'] = MagicMock()

# Mock requests
sys.modules['requests'] = MagicMock()

# Add parent directory to path to import the Lambda function
sys.path.insert(0, os.path.dirname(__file__))
import index

# Define action types and their expected handlers
SERVER_ACTIONS = ['start', 'stop', 'restart', 'startserver', 'stopserver', 'restartserver']
FIX_ROLE_ACTIONS = ['fixserverrole', 'fixrole']
CONFIG_ACTIONS = ['putserverconfig', 'updateserverconfig']


class TestActionRoutingProperty(unittest.TestCase):
    """
    Property-based test suite for action routing correctness
    
    **Feature: async-server-actions, Property 8: Action routing correctness**
    **Validates: Requirements 4.2, 4.3, 4.4**
    """
    
    @given(
        action=st.sampled_from(SERVER_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_server_actions_route_to_handle_server_action(self, action, instance_id, user_email):
        """
        Property Test: Server Actions Route to handle_server_action
        
        For any action in ['start', 'stop', 'restart', 'startServer', 'stopServer', 
        'restartServer'], the ServerActionProcessor should route it to the 
        handle_server_action function.
        
        **Feature: async-server-actions, Property 8: Action routing correctness**
        **Validates: Requirements 4.2**
        """
        # Create SQS message
        message_body = json.dumps({
            'action': action,
            'instanceId': instance_id,
            'userEmail': user_email,
            'timestamp': 1700000000
        })
        
        # Mock the handler functions
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = True
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = True
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = True
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync') as mock_appsync:
                        mock_appsync.return_value = True
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify handle_server_action was called
                        mock_handle_server.assert_called_once()
                        
                        # Verify the correct action was passed (normalized to lowercase)
                        call_args = mock_handle_server.call_args
                        expected_action = 'start' if action.lower() in ['start', 'startserver'] else \
                                        'stop' if action.lower() in ['stop', 'stopserver'] else \
                                        'restart'
                        self.assertEqual(
                            call_args[0][0], expected_action,
                            f"Action '{action}' should be normalized to '{expected_action}'"
                        )
                        
                        # Verify the instance ID was passed
                        self.assertEqual(
                            call_args[0][1], instance_id,
                            f"Instance ID should be passed to handler"
                        )
                        
                        # Verify other handlers were NOT called
                        mock_handle_fix.assert_not_called()
                        mock_handle_config.assert_not_called()
                        
                        # Verify the operation succeeded
                        self.assertTrue(result, f"Action '{action}' should succeed")
    
    @given(
        action=st.sampled_from(FIX_ROLE_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_fix_role_actions_route_to_handle_fix_role(self, action, instance_id, user_email):
        """
        Property Test: Fix Role Actions Route to handle_fix_role
        
        For any action in ['fixServerRole', 'fixRole'], the ServerActionProcessor 
        should route it to the handle_fix_role function.
        
        **Feature: async-server-actions, Property 8: Action routing correctness**
        **Validates: Requirements 4.3**
        """
        # Create SQS message
        message_body = json.dumps({
            'action': action,
            'instanceId': instance_id,
            'userEmail': user_email,
            'timestamp': 1700000000
        })
        
        # Mock the handler functions
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = True
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = True
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = True
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync') as mock_appsync:
                        mock_appsync.return_value = True
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify handle_fix_role was called
                        mock_handle_fix.assert_called_once()
                        
                        # Verify the instance ID was passed
                        call_args = mock_handle_fix.call_args
                        self.assertEqual(
                            call_args[0][0], instance_id,
                            f"Instance ID should be passed to handle_fix_role"
                        )
                        
                        # Verify other handlers were NOT called
                        mock_handle_server.assert_not_called()
                        mock_handle_config.assert_not_called()
                        
                        # Verify the operation succeeded
                        self.assertTrue(result, f"Action '{action}' should succeed")
    
    @given(
        action=st.sampled_from(CONFIG_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
        shutdown_method=st.sampled_from(['CPUUtilization', 'Connections', 'Schedule']),
    )
    @settings(max_examples=100)
    def test_config_actions_route_to_handle_update_server_config(self, action, instance_id, user_email, shutdown_method):
        """
        Property Test: Config Actions Route to handle_update_server_config
        
        For any action in ['putServerConfig', 'updateServerConfig'], the 
        ServerActionProcessor should route it to the handle_update_server_config 
        function with the provided arguments.
        
        **Feature: async-server-actions, Property 8: Action routing correctness**
        **Validates: Requirements 4.4**
        """
        # Create arguments for config update
        arguments = {
            'shutdownMethod': shutdown_method,
            'alarmThreshold': 5.0,
            'alarmEvaluationPeriod': 30,
        }
        
        # Create SQS message
        message_body = json.dumps({
            'action': action,
            'instanceId': instance_id,
            'arguments': arguments,
            'userEmail': user_email,
            'timestamp': 1700000000
        })
        
        # Mock the handler functions
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = True
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = True
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = True
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync') as mock_appsync:
                        mock_appsync.return_value = True
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify handle_update_server_config was called
                        mock_handle_config.assert_called_once()
                        
                        # Verify the instance ID and arguments were passed
                        call_args = mock_handle_config.call_args
                        self.assertEqual(
                            call_args[0][0], instance_id,
                            f"Instance ID should be passed to handle_update_server_config"
                        )
                        self.assertEqual(
                            call_args[0][1], arguments,
                            f"Arguments should be passed to handle_update_server_config"
                        )
                        
                        # Verify other handlers were NOT called
                        mock_handle_server.assert_not_called()
                        mock_handle_fix.assert_not_called()
                        
                        # Verify the operation succeeded
                        self.assertTrue(result, f"Action '{action}' should succeed")
    
    @given(
        action=st.text(min_size=1, max_size=50).filter(
            lambda x: x.lower().strip() not in 
            [a.lower() for a in SERVER_ACTIONS + FIX_ROLE_ACTIONS + CONFIG_ACTIONS]
        ),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_unknown_actions_fail_gracefully(self, action, instance_id, user_email):
        """
        Property Test: Unknown Actions Fail Gracefully
        
        For any action that is not recognized, the ServerActionProcessor should
        return False and send a FAILED status to AppSync without calling any
        handler functions.
        
        **Feature: async-server-actions, Property 8: Action routing correctness**
        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        # Create SQS message with unknown action
        message_body = json.dumps({
            'action': action,
            'instanceId': instance_id,
            'userEmail': user_email,
            'timestamp': 1700000000
        })
        
        # Mock the handler functions
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = True
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = True
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = True
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync') as mock_appsync:
                        mock_appsync.return_value = True
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify the operation failed
                        self.assertFalse(result, f"Unknown action '{action}' should fail")
                        
                        # Verify no handlers were called
                        mock_handle_server.assert_not_called()
                        mock_handle_fix.assert_not_called()
                        mock_handle_config.assert_not_called()
                        
                        # Verify FAILED status was sent to AppSync
                        failed_calls = [
                            call_obj for call_obj in mock_appsync.call_args_list
                            if len(call_obj[0]) >= 3 and call_obj[0][2] == 'FAILED'
                        ]
                        self.assertGreater(
                            len(failed_calls), 0,
                            f"Unknown action '{action}' should send FAILED status to AppSync"
                        )
    
    @given(
        action=st.sampled_from(SERVER_ACTIONS + FIX_ROLE_ACTIONS + CONFIG_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_all_actions_send_processing_status(self, action, instance_id, user_email):
        """
        Property Test: All Actions Send PROCESSING Status
        
        For any valid action, the ServerActionProcessor should send a PROCESSING
        status to AppSync before routing to the handler.
        
        **Feature: async-server-actions, Property 8: Action routing correctness**
        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        # Create arguments for config actions
        arguments = None
        if action.lower() in [a.lower() for a in CONFIG_ACTIONS]:
            arguments = {
                'shutdownMethod': 'CPUUtilization',
                'alarmThreshold': 5.0,
            }
        
        # Create SQS message
        message_body = json.dumps({
            'action': action,
            'instanceId': instance_id,
            'arguments': arguments,
            'userEmail': user_email,
            'timestamp': 1700000000
        })
        
        # Mock the handler functions
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = True
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = True
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = True
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync') as mock_appsync:
                        mock_appsync.return_value = True
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify PROCESSING status was sent
                        processing_calls = [
                            call_obj for call_obj in mock_appsync.call_args_list
                            if len(call_obj[0]) >= 3 and call_obj[0][2] == 'PROCESSING'
                        ]
                        self.assertGreater(
                            len(processing_calls), 0,
                            f"Action '{action}' should send PROCESSING status to AppSync"
                        )
                        
                        # Verify COMPLETED status was sent (since handlers return True)
                        completed_calls = [
                            call_obj for call_obj in mock_appsync.call_args_list
                            if len(call_obj[0]) >= 3 and call_obj[0][2] == 'COMPLETED'
                        ]
                        self.assertGreater(
                            len(completed_calls), 0,
                            f"Action '{action}' should send COMPLETED status to AppSync"
                        )
    
    @given(
        action=st.sampled_from(SERVER_ACTIONS + FIX_ROLE_ACTIONS + CONFIG_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_handler_failure_sends_failed_status(self, action, instance_id, user_email):
        """
        Property Test: Handler Failure Sends FAILED Status
        
        For any valid action, when the handler returns False, the 
        ServerActionProcessor should send a FAILED status to AppSync.
        
        **Feature: async-server-actions, Property 8: Action routing correctness**
        **Validates: Requirements 4.2, 4.3, 4.4**
        """
        # Create arguments for config actions
        arguments = None
        if action.lower() in [a.lower() for a in CONFIG_ACTIONS]:
            arguments = {
                'shutdownMethod': 'CPUUtilization',
                'alarmThreshold': 5.0,
            }
        
        # Create SQS message
        message_body = json.dumps({
            'action': action,
            'instanceId': instance_id,
            'arguments': arguments,
            'userEmail': user_email,
            'timestamp': 1700000000
        })
        
        # Mock the handler functions to return False (failure)
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = False
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = False
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = False
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync') as mock_appsync:
                        mock_appsync.return_value = True
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify the operation failed
                        self.assertFalse(result, f"Action '{action}' should fail when handler returns False")
                        
                        # Verify FAILED status was sent to AppSync
                        failed_calls = [
                            call_obj for call_obj in mock_appsync.call_args_list
                            if len(call_obj[0]) >= 3 and call_obj[0][2] == 'FAILED'
                        ]
                        self.assertGreater(
                            len(failed_calls), 0,
                            f"Action '{action}' should send FAILED status to AppSync when handler fails"
                        )


if __name__ == '__main__':
    unittest.main()
