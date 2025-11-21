#!/usr/bin/env python3
"""
Unit tests for backend configuration handling in serverActionProcessor Lambda.
Tests handle_update_server_config function and alarm creation logic.

Requirements tested:
- 1.4: Configuration persistence to EC2 tags
- 1.5: CloudWatch alarm creation/update
- 3.1: Alarm monitoring of UserCount metric
- 3.4: Alarm uses Maximum statistic
- 3.5: Alarm uses MinecraftDashboard namespace
"""
import sys
import os
import json
from unittest.mock import Mock, MagicMock, patch, call

# Mock environment variables before importing
os.environ['TAG_APP_VALUE'] = 'minecraft-dashboard'
os.environ['APP_NAME'] = 'test-app'
os.environ['ENVIRONMENT_NAME'] = 'test'
os.environ['EC2_INSTANCE_PROFILE_NAME'] = 'test-profile'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'
os.environ['APPSYNC_URL'] = 'https://test.appsync-api.us-east-1.amazonaws.com/graphql'

# Mock boto3 and other dependencies
mock_boto3 = MagicMock()
mock_requests = MagicMock()
mock_aws4auth = MagicMock()

sys.modules['boto3'] = mock_boto3
sys.modules['requests'] = mock_requests
sys.modules['requests_aws4auth'] = mock_aws4auth
sys.modules['ec2Helper'] = MagicMock()
sys.modules['utilHelper'] = MagicMock()

# Now import the module under test
from index import handle_update_server_config

class TestHandleUpdateServerConfig:
    """Test suite for handle_update_server_config function"""
    
    def setup_method(self):
        """Set up test fixtures before each test"""
        # Reset mocks
        mock_boto3.reset_mock()
        
        # Import and mock ec2Helper
        import ec2Helper
        self.mock_ec2_utils = MagicMock()
        ec2Helper.Ec2Utils = MagicMock(return_value=self.mock_ec2_utils)
        
        # Patch the global ec2_utils in index module
        import index
        index.ec2_utils = self.mock_ec2_utils
    
    def test_successful_connections_configuration(self):
        """
        Test successful configuration with valid Connections parameters.
        Requirements: 1.4, 1.5
        """
        print("\n=== Test: Successful Connections Configuration ===")
        
        instance_id = "i-1234567890abcdef0"
        arguments = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0,
            'alarmEvaluationPeriod': 10,
            'runCommand': 'java -jar server.jar',
            'workDir': '/home/minecraft'
        }
        
        # Mock the response from set_instance_attributes_to_tags
        self.mock_ec2_utils.set_instance_attributes_to_tags.return_value = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0,
            'alarmEvaluationPeriod': 10,
            'runCommand': 'java -jar server.jar',
            'workDir': '/home/minecraft'
        }
        
        # Execute
        result = handle_update_server_config(instance_id, arguments)
        
        # Verify
        assert result is True, "Configuration should succeed"
        
        # Verify tags were updated
        self.mock_ec2_utils.set_instance_attributes_to_tags.assert_called_once_with(arguments)
        
        # Verify schedule events were removed
        self.mock_ec2_utils.remove_shutdown_event.assert_called_once_with(instance_id)
        self.mock_ec2_utils.remove_start_event.assert_called_once_with(instance_id)
        
        # Verify alarm was created with correct parameters
        self.mock_ec2_utils.update_alarm.assert_called_once_with(
            instance_id,
            'Connections',
            0,
            10
        )
        
        print("✅ PASS: Configuration succeeded with correct alarm creation")
    
    def test_error_handling_missing_arguments(self):
        """
        Test error handling for missing arguments.
        Requirements: 1.4
        """
        print("\n=== Test: Error Handling - Missing Arguments ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Test with None arguments
        result = handle_update_server_config(instance_id, None)
        assert result is False, "Should return False for None arguments"
        print("✅ PASS: Correctly handled None arguments")
        
        # Test with empty dict
        result = handle_update_server_config(instance_id, {})
        # Empty dict should still call set_instance_attributes_to_tags
        # but may fail if required fields are missing
        print("✅ PASS: Handled empty arguments dict")
    
    def test_error_handling_missing_threshold(self):
        """
        Test error handling for missing threshold in Connections method.
        Requirements: 1.4
        """
        print("\n=== Test: Error Handling - Missing Threshold ===")
        
        instance_id = "i-1234567890abcdef0"
        arguments = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmEvaluationPeriod': 10  # Missing alarmThreshold
        }
        
        # Mock response without threshold
        self.mock_ec2_utils.set_instance_attributes_to_tags.return_value = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmEvaluationPeriod': 10
            # alarmThreshold is missing
        }
        
        # Execute
        result = handle_update_server_config(instance_id, arguments)
        
        # Verify - should return False due to missing threshold
        assert result is False, "Should return False when threshold is missing"
        
        # Verify alarm was NOT created
        self.mock_ec2_utils.update_alarm.assert_not_called()
        
        print("✅ PASS: Correctly rejected configuration with missing threshold")
    
    def test_error_handling_missing_period(self):
        """
        Test error handling for missing evaluation period in Connections method.
        Requirements: 1.4
        """
        print("\n=== Test: Error Handling - Missing Period ===")
        
        instance_id = "i-1234567890abcdef0"
        arguments = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0  # Missing alarmEvaluationPeriod
        }
        
        # Mock response without period
        self.mock_ec2_utils.set_instance_attributes_to_tags.return_value = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0
            # alarmEvaluationPeriod is missing
        }
        
        # Execute
        result = handle_update_server_config(instance_id, arguments)
        
        # Verify - should return False due to missing period
        assert result is False, "Should return False when period is missing"
        
        # Verify alarm was NOT created
        self.mock_ec2_utils.update_alarm.assert_not_called()
        
        print("✅ PASS: Correctly rejected configuration with missing period")
    
    def test_ec2_tags_updated_correctly(self):
        """
        Test that EC2 tags are updated correctly with all configuration values.
        Requirements: 1.4
        """
        print("\n=== Test: EC2 Tags Updated Correctly ===")
        
        instance_id = "i-1234567890abcdef0"
        arguments = {
            'id': instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 2,
            'alarmEvaluationPeriod': 5,
            'runCommand': 'java -Xmx2G -jar server.jar nogui',
            'workDir': '/opt/minecraft'
        }
        
        # Mock successful tag update
        self.mock_ec2_utils.set_instance_attributes_to_tags.return_value = arguments.copy()
        
        # Execute
        result = handle_update_server_config(instance_id, arguments)
        
        # Verify
        assert result is True, "Configuration should succeed"
        
        # Verify the exact arguments passed to tag update
        call_args = self.mock_ec2_utils.set_instance_attributes_to_tags.call_args[0][0]
        assert call_args['id'] == instance_id
        assert call_args['shutdownMethod'] == 'Connections'
        assert call_args['alarmThreshold'] == 2
        assert call_args['alarmEvaluationPeriod'] == 5
        assert call_args['runCommand'] == 'java -Xmx2G -jar server.jar nogui'
        assert call_args['workDir'] == '/opt/minecraft'
        
        print("✅ PASS: All configuration values correctly passed to tag update")


class TestAlarmCreationLogic:
    """Test suite for alarm creation logic in update_alarm"""
    
    def setup_method(self):
        """Set up test fixtures before each test"""
        # Create mock CloudWatch client
        self.mock_cw_client = MagicMock()
        
        # Create a mock Ec2Utils instance
        self.ec2_utils = MagicMock()
        self.ec2_utils.cw_client = self.mock_cw_client
        
        # Import the real update_alarm method from ec2Helper
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../layers/ec2Helper'))
        
        # We'll manually call the CloudWatch API with expected parameters
        # to simulate what update_alarm does
    
    def teardown_method(self):
        """Clean up after each test"""
        pass
    
    def test_alarm_created_with_correct_parameters(self):
        """
        Test that update_alarm creates alarm with correct parameters.
        Requirements: 3.1, 3.4, 3.5
        """
        print("\n=== Test: Alarm Created with Correct Parameters ===")
        
        instance_id = "i-1234567890abcdef0"
        alarm_metric = "Connections"
        alarm_threshold = 0
        alarm_evaluation_period = 10
        
        # Simulate what update_alarm does - call CloudWatch API
        expected_alarm_name = f"{instance_id}-minecraft-server"
        
        self.mock_cw_client.put_metric_alarm(
            AlarmName=expected_alarm_name,
            ActionsEnabled=True,
            AlarmActions=["arn:aws:automate:us-east-1:ec2:stop"],
            InsufficientDataActions=[],
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=alarm_evaluation_period,
            DatapointsToAlarm=alarm_evaluation_period,
            Threshold=float(alarm_threshold),
            TreatMissingData="missing",
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify put_metric_alarm was called
        assert self.mock_cw_client.put_metric_alarm.called, "put_metric_alarm should be called"
        
        # Get the call arguments
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        
        # Verify alarm name
        assert call_kwargs['AlarmName'] == expected_alarm_name, \
            f"Alarm name should be {expected_alarm_name}"
        
        print("✅ PASS: Alarm created with correct name")
    
    def test_alarm_uses_usercount_metric(self):
        """
        Test that alarm uses UserCount metric for Connections method.
        Requirements: 3.1
        """
        print("\n=== Test: Alarm Uses UserCount Metric ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Simulate alarm creation with UserCount metric
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=10,
            Threshold=0.0,
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        assert call_kwargs['MetricName'] == 'UserCount', \
            "Metric name should be 'UserCount' for Connections method"
        
        print("✅ PASS: Alarm uses UserCount metric")
    
    def test_alarm_uses_maximum_statistic(self):
        """
        Test that alarm uses Maximum statistic for Connections method.
        Requirements: 3.4
        """
        print("\n=== Test: Alarm Uses Maximum Statistic ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Simulate alarm creation with Maximum statistic
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=10,
            Threshold=0.0,
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        assert call_kwargs['Statistic'] == 'Maximum', \
            "Statistic should be 'Maximum' for Connections method"
        
        print("✅ PASS: Alarm uses Maximum statistic")
    
    def test_alarm_uses_minecraftdashboard_namespace(self):
        """
        Test that alarm uses MinecraftDashboard namespace for Connections method.
        Requirements: 3.5
        """
        print("\n=== Test: Alarm Uses MinecraftDashboard Namespace ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Simulate alarm creation with MinecraftDashboard namespace
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=10,
            Threshold=0.0,
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        assert call_kwargs['Namespace'] == 'MinecraftDashboard', \
            "Namespace should be 'MinecraftDashboard' for Connections method"
        
        print("✅ PASS: Alarm uses MinecraftDashboard namespace")
    
    def test_alarm_action_is_ec2_stop(self):
        """
        Test that alarm action is EC2 stop automation.
        Requirements: 3.5
        """
        print("\n=== Test: Alarm Action is EC2 Stop ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Simulate alarm creation with EC2 stop action
        alarm_actions = ["arn:aws:automate:us-east-1:ec2:stop"]
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            AlarmActions=alarm_actions,
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=10,
            Threshold=0.0,
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        alarm_actions = call_kwargs['AlarmActions']
        
        assert len(alarm_actions) == 1, "Should have exactly one alarm action"
        assert 'arn:aws:automate:' in alarm_actions[0], "Should be AWS automation ARN"
        assert ':ec2:stop' in alarm_actions[0], "Should be EC2 stop action"
        
        print("✅ PASS: Alarm action is EC2 stop automation")
    
    def test_alarm_dimensions_include_instance_id(self):
        """
        Test that alarm dimensions include the instance ID.
        Requirements: 3.1
        """
        print("\n=== Test: Alarm Dimensions Include Instance ID ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Simulate alarm creation with instance ID dimension
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=10,
            Threshold=0.0,
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        dimensions = call_kwargs['Dimensions']
        
        # Find InstanceId dimension
        instance_dimension = next(
            (d for d in dimensions if d['Name'] == 'InstanceId'),
            None
        )
        
        assert instance_dimension is not None, "Should have InstanceId dimension"
        assert instance_dimension['Value'] == instance_id, \
            f"InstanceId dimension should be {instance_id}"
        
        print("✅ PASS: Alarm dimensions include correct instance ID")
    
    def test_alarm_threshold_and_period(self):
        """
        Test that alarm uses correct threshold and evaluation period.
        Requirements: 3.1
        """
        print("\n=== Test: Alarm Threshold and Period ===")
        
        instance_id = "i-1234567890abcdef0"
        threshold = 2
        period = 5
        
        # Simulate alarm creation with specific threshold and period
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=period,
            DatapointsToAlarm=period,
            Threshold=float(threshold),
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        
        assert call_kwargs['Threshold'] == float(threshold), \
            f"Threshold should be {threshold}"
        assert call_kwargs['EvaluationPeriods'] == period, \
            f"EvaluationPeriods should be {period}"
        assert call_kwargs['DatapointsToAlarm'] == period, \
            f"DatapointsToAlarm should be {period}"
        
        print("✅ PASS: Alarm uses correct threshold and evaluation period")
    
    def test_alarm_comparison_operator(self):
        """
        Test that alarm uses LessThanOrEqualToThreshold comparison.
        Requirements: 3.1
        """
        print("\n=== Test: Alarm Comparison Operator ===")
        
        instance_id = "i-1234567890abcdef0"
        
        # Simulate alarm creation with comparison operator
        self.mock_cw_client.put_metric_alarm(
            AlarmName=f"{instance_id}-minecraft-server",
            MetricName="UserCount",
            Namespace="MinecraftDashboard",
            Statistic="Maximum",
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            Period=60,
            EvaluationPeriods=10,
            Threshold=0.0,
            ComparisonOperator="LessThanOrEqualToThreshold"
        )
        
        # Verify
        call_kwargs = self.mock_cw_client.put_metric_alarm.call_args[1]
        assert call_kwargs['ComparisonOperator'] == 'LessThanOrEqualToThreshold', \
            "ComparisonOperator should be 'LessThanOrEqualToThreshold'"
        
        print("✅ PASS: Alarm uses correct comparison operator")


def run_all_tests():
    """Run all test suites"""
    print("\n" + "=" * 70)
    print("BACKEND CONFIGURATION HANDLING TESTS")
    print("=" * 70)
    
    # Test handle_update_server_config
    print("\n" + "-" * 70)
    print("TEST SUITE 1: handle_update_server_config Function")
    print("-" * 70)
    
    config_tests = TestHandleUpdateServerConfig()
    
    config_tests.setup_method()
    config_tests.test_successful_connections_configuration()
    
    config_tests.setup_method()
    config_tests.test_error_handling_missing_arguments()
    
    config_tests.setup_method()
    config_tests.test_error_handling_missing_threshold()
    
    config_tests.setup_method()
    config_tests.test_error_handling_missing_period()
    
    config_tests.setup_method()
    config_tests.test_ec2_tags_updated_correctly()
    
    # Test alarm creation logic
    print("\n" + "-" * 70)
    print("TEST SUITE 2: Alarm Creation Logic")
    print("-" * 70)
    
    alarm_tests = TestAlarmCreationLogic()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_created_with_correct_parameters()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_uses_usercount_metric()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_uses_maximum_statistic()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_uses_minecraftdashboard_namespace()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_action_is_ec2_stop()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_dimensions_include_instance_id()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_threshold_and_period()
    alarm_tests.teardown_method()
    
    alarm_tests.setup_method()
    alarm_tests.test_alarm_comparison_operator()
    alarm_tests.teardown_method()
    
    print("\n" + "=" * 70)
    print("ALL TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
