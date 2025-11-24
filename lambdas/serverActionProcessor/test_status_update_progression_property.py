#!/usr/bin/env python3
"""
Property-based test for status update progression in async server actions
Tests that status updates follow the correct sequence: PROCESSING → COMPLETED/FAILED

**Feature: async-server-actions, Property 5: Status update progression**
**Validates: Requirements 2.1, 2.2, 2.3, 2.4**
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

# Define action types
SERVER_ACTIONS = ['start', 'stop', 'restart', 'startserver', 'stopserver', 'restartserver']
FIX_ROLE_ACTIONS = ['fixserverrole', 'fixrole']
CONFIG_ACTIONS = ['putserverconfig', 'updateserverconfig']
ALL_ACTIONS = SERVER_ACTIONS + FIX_ROLE_ACTIONS + CONFIG_ACTIONS


class TestStatusUpdateProgressionProperty(unittest.TestCase):
    """
    Property-based test suite for status update progression
    
    **Feature: async-server-actions, Property 5: Status update progression**
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """
    
    @given(
        action=st.sampled_from(ALL_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_successful_action_status_progression(self, action, instance_id, user_email):
        """
        Property Test: Successful Action Status Progression
        
        For any action that completes successfully in ServerActionProcessor, the
        system should send status updates in the correct sequence:
        1. PROCESSING (when processing starts)
        2. COMPLETED (when done)
        
        **Feature: async-server-actions, Property 5: Status update progression**
        **Validates: Requirements 2.2, 2.3**
        """
        # Track all status updates sent to AppSync
        status_updates = []
        
        def capture_status_update(action_name, inst_id, status, message=None, email=None):
            """Capture status updates for verification"""
            status_updates.append({
                'action': action_name,
                'instanceId': inst_id,
                'status': status,
                'message': message,
                'userEmail': email
            })
            return True
        
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
        
        # Mock the handler functions to succeed
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = True
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = True
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = True
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync', side_effect=capture_status_update):
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify the operation succeeded
                        self.assertTrue(result, f"Action '{action}' should succeed")
        
        # Verify status update progression
        self.assertGreaterEqual(len(status_updates), 2, 
                               f"Should have at least 2 status updates for action '{action}'")
        
        # Verify first status is PROCESSING (when processing starts)
        self.assertEqual(status_updates[0]['status'], 'PROCESSING',
                        f"First status update should be PROCESSING when processing starts")
        self.assertEqual(status_updates[0]['instanceId'], instance_id,
                        f"First status update should have correct instance ID")
        
        # Verify final status is COMPLETED
        self.assertEqual(status_updates[-1]['status'], 'COMPLETED',
                        f"Final status update should be COMPLETED for successful action")
        self.assertEqual(status_updates[-1]['instanceId'], instance_id,
                        f"Final status update should have correct instance ID")
        
        # Verify no FAILED status in the sequence
        failed_statuses = [u for u in status_updates if u['status'] == 'FAILED']
        self.assertEqual(len(failed_statuses), 0,
                        f"Should not have any FAILED status for successful action")
        
        # Verify status progression order: PROCESSING comes before COMPLETED
        processing_indices = [i for i, u in enumerate(status_updates) if u['status'] == 'PROCESSING']
        completed_indices = [i for i, u in enumerate(status_updates) if u['status'] == 'COMPLETED']
        
        if processing_indices and completed_indices:
            self.assertLess(processing_indices[0], completed_indices[0],
                          f"PROCESSING status should come before COMPLETED status")
    
    @given(
        action=st.sampled_from(ALL_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_failed_action_status_progression(self, action, instance_id, user_email):
        """
        Property Test: Failed Action Status Progression
        
        For any action that fails in ServerActionProcessor, the system should
        send status updates in the correct sequence:
        1. PROCESSING (when processing starts)
        2. FAILED (when handler fails)
        
        **Feature: async-server-actions, Property 5: Status update progression**
        **Validates: Requirements 2.2, 2.4**
        """
        # Track all status updates sent to AppSync
        status_updates = []
        
        def capture_status_update(action_name, inst_id, status, message=None, email=None):
            """Capture status updates for verification"""
            status_updates.append({
                'action': action_name,
                'instanceId': inst_id,
                'status': status,
                'message': message,
                'userEmail': email
            })
            return True
        
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
        
        # Mock the handler functions to FAIL
        with patch.object(index, 'handle_server_action') as mock_handle_server:
            mock_handle_server.return_value = False
            
            with patch.object(index, 'handle_fix_role') as mock_handle_fix:
                mock_handle_fix.return_value = False
                
                with patch.object(index, 'handle_update_server_config') as mock_handle_config:
                    mock_handle_config.return_value = False
                    
                    # Mock AppSync status updates
                    with patch.object(index, 'send_to_appsync', side_effect=capture_status_update):
                        
                        # Process the message
                        result = index.process_server_action(message_body)
                        
                        # Verify the operation failed
                        self.assertFalse(result, f"Action '{action}' should fail")
        
        # Verify status update progression
        self.assertGreaterEqual(len(status_updates), 2,
                               f"Should have at least 2 status updates for action '{action}'")
        
        # Verify first status is PROCESSING (when processing starts)
        self.assertEqual(status_updates[0]['status'], 'PROCESSING',
                        f"First status update should be PROCESSING when processing starts")
        self.assertEqual(status_updates[0]['instanceId'], instance_id,
                        f"First status update should have correct instance ID")
        
        # Verify final status is FAILED
        self.assertEqual(status_updates[-1]['status'], 'FAILED',
                        f"Final status update should be FAILED for failed action")
        self.assertEqual(status_updates[-1]['instanceId'], instance_id,
                        f"Final status update should have correct instance ID")
        
        # Verify no COMPLETED status in the sequence
        completed_statuses = [u for u in status_updates if u['status'] == 'COMPLETED']
        self.assertEqual(len(completed_statuses), 0,
                        f"Should not have any COMPLETED status for failed action")
        
        # Verify status progression order: PROCESSING comes before FAILED
        processing_indices = [i for i, u in enumerate(status_updates) if u['status'] == 'PROCESSING']
        failed_indices = [i for i, u in enumerate(status_updates) if u['status'] == 'FAILED']
        
        if processing_indices and failed_indices:
            self.assertLess(processing_indices[0], failed_indices[0],
                          f"PROCESSING status should come before FAILED status")
    
    @given(
        action=st.sampled_from(ALL_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_status_updates_contain_required_fields(self, action, instance_id, user_email):
        """
        Property Test: Status Updates Contain Required Fields
        
        For any action, all status updates should contain the required
        fields: action, instanceId, and status.
        
        **Feature: async-server-actions, Property 5: Status update progression**
        **Validates: Requirements 2.5**
        """
        # Track all status updates sent to AppSync
        status_updates = []
        
        def capture_status_update(action_name, inst_id, status, message=None, email=None):
            """Capture status updates for verification"""
            status_updates.append({
                'action': action_name,
                'instanceId': inst_id,
                'status': status,
                'message': message,
                'userEmail': email
            })
            return True
        
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
                    with patch.object(index, 'send_to_appsync', side_effect=capture_status_update):
                        
                        # Process the message
                        index.process_server_action(message_body)
        
        # Verify all status updates contain required fields
        for i, update in enumerate(status_updates):
            self.assertIn('action', update,
                         f"Status update {i} should contain 'action' field")
            self.assertIn('instanceId', update,
                         f"Status update {i} should contain 'instanceId' field")
            self.assertIn('status', update,
                         f"Status update {i} should contain 'status' field")
            
            # Verify values are not None
            self.assertIsNotNone(update['action'],
                               f"Status update {i} 'action' should not be None")
            self.assertIsNotNone(update['instanceId'],
                               f"Status update {i} 'instanceId' should not be None")
            self.assertIsNotNone(update['status'],
                               f"Status update {i} 'status' should not be None")
            
            # Verify status is one of the valid values
            self.assertIn(update['status'], ['PROCESSING', 'COMPLETED', 'FAILED'],
                         f"Status update {i} status should be PROCESSING, COMPLETED, or FAILED")
            
            # Verify instance ID matches
            self.assertEqual(update['instanceId'], instance_id,
                           f"Status update {i} should have correct instance ID")
    
    @given(
        action=st.sampled_from(ALL_ACTIONS),
        instance_id=st.from_regex(r'i-[0-9a-f]{17}', fullmatch=True),
        user_email=st.emails(),
    )
    @settings(max_examples=100)
    def test_no_status_regression(self, action, instance_id, user_email):
        """
        Property Test: No Status Regression
        
        For any action, status updates should never regress from a final
        state (COMPLETED or FAILED) back to PROCESSING.
        
        **Feature: async-server-actions, Property 5: Status update progression**
        **Validates: Requirements 2.2, 2.3, 2.4**
        """
        # Track all status updates sent to AppSync
        status_updates = []
        
        def capture_status_update(action_name, inst_id, status, message=None, email=None):
            """Capture status updates for verification"""
            status_updates.append({
                'action': action_name,
                'instanceId': inst_id,
                'status': status,
                'message': message,
                'userEmail': email
            })
            return True
        
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
                    with patch.object(index, 'send_to_appsync', side_effect=capture_status_update):
                        
                        # Process the message
                        index.process_server_action(message_body)
        
        # Verify no status regression
        final_state_reached = False
        for i, update in enumerate(status_updates):
            if update['status'] in ['COMPLETED', 'FAILED']:
                final_state_reached = True
            elif final_state_reached and update['status'] == 'PROCESSING':
                self.fail(f"Status regressed from final state back to PROCESSING at update {i}")


if __name__ == '__main__':
    unittest.main()
