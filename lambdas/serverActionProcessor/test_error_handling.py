"""
Unit tests for error handling scenarios in ServerActionProcessor Lambda

Tests cover:
- EC2 operation failure handling
- IAM profile attachment failure handling
- Invalid message format handling
- Missing required fields handling

Requirements: 1.5, 4.5
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock environment variables before importing the module
os.environ['TAG_APP_VALUE'] = 'test-app'
os.environ['APP_NAME'] = 'test-app'
os.environ['ENVIRONMENT_NAME'] = 'test'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['APPSYNC_URL'] = 'https://test.appsync-api.us-east-1.amazonaws.com/graphql'

# Mock boto3 session and credentials before importing
with patch('boto3.Session') as mock_session:
    mock_creds = MagicMock()
    mock_creds.access_key = 'test-access-key'
    mock_creds.secret_key = 'test-secret-key'
    mock_creds.token = 'test-token'
    mock_session.return_value.get_credentials.return_value.get_frozen_credentials.return_value = mock_creds
    mock_session.return_value.region_name = 'us-east-1'
    
    # Mock the Lambda layer modules before importing index
    sys.modules['ec2Helper'] = MagicMock()
    sys.modules['utilHelper'] = MagicMock()
    sys.modules['requests_aws4auth'] = MagicMock()
    
    import index


class TestEC2OperationFailure:
    """Test cases for EC2 operation failure scenarios"""
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    @patch('index.ec2_client')
    def test_start_instance_failure(self, mock_ec2_client, mock_ec2_utils, mock_send_to_appsync):
        """Test that EC2 start_instances failure is handled correctly"""
        # Mock instance in stopped state
        mock_ec2_utils.list_server_by_id.return_value = {
            'Instances': [{
                'State': {'Name': 'stopped'}
            }]
        }
        
        # Mock EC2 start_instances to raise exception
        mock_ec2_client.start_instances.side_effect = Exception("EC2 service unavailable")
        
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        result = index.handle_server_action('start', 'i-1234567890abcdef0')
        
        assert result is False
        mock_ec2_client.start_instances.assert_called_once()
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    @patch('index.ec2_client')
    def test_stop_instance_failure(self, mock_ec2_client, mock_ec2_utils, mock_send_to_appsync):
        """Test that EC2 stop_instances failure is handled correctly"""
        # Mock instance in running state
        mock_ec2_utils.list_server_by_id.return_value = {
            'Instances': [{
                'State': {'Name': 'running'}
            }]
        }
        
        # Mock EC2 stop_instances to raise exception
        mock_ec2_client.stop_instances.side_effect = Exception("Insufficient permissions")
        
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        result = index.handle_server_action('stop', 'i-1234567890abcdef0')
        
        assert result is False
        mock_ec2_client.stop_instances.assert_called_once()
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    @patch('index.ec2_client')
    def test_restart_instance_failure(self, mock_ec2_client, mock_ec2_utils, mock_send_to_appsync):
        """Test that EC2 reboot_instances failure is handled correctly"""
        # Mock instance in running state
        mock_ec2_utils.list_server_by_id.return_value = {
            'Instances': [{
                'State': {'Name': 'running'}
            }]
        }
        
        # Mock EC2 reboot_instances to raise exception
        mock_ec2_client.reboot_instances.side_effect = Exception("Instance not responding")
        
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        result = index.handle_server_action('restart', 'i-1234567890abcdef0')
        
        assert result is False
        mock_ec2_client.reboot_instances.assert_called_once()
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    def test_instance_not_found(self, mock_ec2_utils, mock_send_to_appsync):
        """Test that missing instance is handled correctly"""
        # Mock instance not found
        mock_ec2_utils.list_server_by_id.return_value = {
            'Instances': []
        }
        
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        result = index.handle_server_action('start', 'i-nonexistent')
        
        assert result is False


class TestIAMProfileAttachmentFailure:
    """Test cases for IAM profile attachment failure scenarios"""
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    def test_unauthorized_operation_error(self, mock_ec2_utils, mock_send_to_appsync):
        """Test that UnauthorizedOperation error is handled correctly"""
        # Mock describe_iam_profile to return None (no profile attached)
        mock_ec2_utils.describe_iam_profile.return_value = None
        
        # Create a mock IamProfile instance
        with patch('index.IamProfile') as mock_iam_profile_class:
            mock_iam_instance = MagicMock()
            mock_iam_profile_class.return_value = mock_iam_instance
            
            # Mock manage_iam_profile to return UnauthorizedOperation error
            mock_iam_instance.manage_iam_profile.return_value = {
                "status": "error",
                "message": "User is not authorized to perform: iam:PassRole",
                "code": "UnauthorizedOperation"
            }
            
            # Mock AppSync to return True
            mock_send_to_appsync.return_value = True
            
            result = index.handle_fix_role('i-1234567890abcdef0')
            
            assert result is False
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    def test_iam_profile_attachment_timeout(self, mock_ec2_utils, mock_send_to_appsync):
        """Test that IAM profile attachment timeout is handled correctly"""
        # Mock describe_iam_profile to return None (no profile attached)
        mock_ec2_utils.describe_iam_profile.return_value = None
        
        # Create a mock IamProfile instance
        with patch('index.IamProfile') as mock_iam_profile_class:
            mock_iam_instance = MagicMock()
            mock_iam_profile_class.return_value = mock_iam_instance
            
            # Mock manage_iam_profile to return False (timeout)
            mock_iam_instance.manage_iam_profile.return_value = False
            
            # Mock AppSync to return True
            mock_send_to_appsync.return_value = True
            
            result = index.handle_fix_role('i-1234567890abcdef0')
            
            assert result is False
    
    @patch('index.send_to_appsync')
    def test_iam_profile_exception(self, mock_send_to_appsync):
        """Test that IAM profile exception is handled correctly"""
        # Create a mock IamProfile instance that raises exception
        with patch('index.IamProfile') as mock_iam_profile_class:
            mock_iam_profile_class.side_effect = Exception("IAM service unavailable")
            
            # Mock AppSync to return True
            mock_send_to_appsync.return_value = True
            
            result = index.handle_fix_role('i-1234567890abcdef0')
            
            assert result is False


class TestInvalidMessageFormat:
    """Test cases for invalid message format scenarios"""
    
    @patch('index.send_to_appsync')
    def test_invalid_json_message(self, mock_send_to_appsync):
        """Test that invalid JSON message is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        # Invalid JSON string
        invalid_message = "not a valid json {{"
        
        result = index.process_server_action(invalid_message)
        
        assert result is False
    
    @patch('index.send_to_appsync')
    def test_missing_action_field(self, mock_send_to_appsync):
        """Test that missing action field is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        # Message missing 'action' field
        message = json.dumps({
            'instanceId': 'i-1234567890abcdef0',
            'timestamp': 1700000000
        })
        
        result = index.process_server_action(message)
        
        assert result is False
    
    @patch('index.send_to_appsync')
    def test_missing_instance_id_field(self, mock_send_to_appsync):
        """Test that missing instanceId field is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        # Message missing 'instanceId' field
        message = json.dumps({
            'action': 'start',
            'timestamp': 1700000000
        })
        
        result = index.process_server_action(message)
        
        assert result is False
    
    @patch('index.send_to_appsync')
    def test_unknown_action_type(self, mock_send_to_appsync):
        """Test that unknown action type is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        # Message with unknown action
        message = json.dumps({
            'action': 'unknownAction',
            'instanceId': 'i-1234567890abcdef0',
            'timestamp': 1700000000
        })
        
        result = index.process_server_action(message)
        
        assert result is False
        # Verify FAILED status was sent to AppSync
        mock_send_to_appsync.assert_called()


class TestConfigUpdateFailure:
    """Test cases for configuration update failure scenarios"""
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    def test_missing_arguments(self, mock_ec2_utils, mock_send_to_appsync):
        """Test that missing arguments for config update is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        result = index.handle_update_server_config('i-1234567890abcdef0', None)
        
        assert result is False
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    def test_invalid_schedule_expression(self, mock_ec2_utils, mock_send_to_appsync):
        """Test that invalid schedule expression is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        # Mock set_instance_attributes_to_tags to return schedule config
        mock_ec2_utils.set_instance_attributes_to_tags.return_value = {
            'shutdownMethod': 'Schedule',
            'stopScheduleExpression': 'invalid cron expression'
        }
        
        # Mock configure_shutdown_event to raise ValueError
        mock_ec2_utils.configure_shutdown_event.side_effect = ValueError("Invalid cron expression")
        
        arguments = {
            'id': 'i-1234567890abcdef0',
            'shutdownMethod': 'Schedule',
            'stopScheduleExpression': 'invalid cron expression'
        }
        
        result = index.handle_update_server_config('i-1234567890abcdef0', arguments)
        
        assert result is False
    
    @patch('index.send_to_appsync')
    @patch('index.ec2_utils')
    def test_missing_alarm_parameters(self, mock_ec2_utils, mock_send_to_appsync):
        """Test that missing alarm parameters is handled correctly"""
        # Mock AppSync to return True
        mock_send_to_appsync.return_value = True
        
        # Mock set_instance_attributes_to_tags to return CPU config without threshold
        mock_ec2_utils.set_instance_attributes_to_tags.return_value = {
            'shutdownMethod': 'CPUUtilization',
            'alarmThreshold': None,
            'alarmEvaluationPeriod': None
        }
        
        arguments = {
            'id': 'i-1234567890abcdef0',
            'shutdownMethod': 'CPUUtilization'
        }
        
        result = index.handle_update_server_config('i-1234567890abcdef0', arguments)
        
        assert result is False


class TestSQSHandlerErrors:
    """Test cases for SQS handler error scenarios"""
    
    @patch('index.process_server_action')
    def test_handler_processes_all_messages(self, mock_process):
        """Test that handler processes all messages even if some fail"""
        # Mock process_server_action to fail for first message, succeed for second
        mock_process.side_effect = [False, True]
        
        event = {
            'Records': [
                {
                    'messageId': 'msg-1',
                    'body': json.dumps({'action': 'start', 'instanceId': 'i-111'})
                },
                {
                    'messageId': 'msg-2',
                    'body': json.dumps({'action': 'stop', 'instanceId': 'i-222'})
                }
            ]
        }
        
        # Handler should not raise exception
        index.handler(event, None)
        
        # Verify both messages were processed
        assert mock_process.call_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
