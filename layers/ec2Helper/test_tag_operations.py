#!/usr/bin/env python3
"""
Unit tests for EC2 tag operations in ec2Helper.py
Tests get_instance_attributes_from_tags and set_instance_attributes_to_tags functions
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from botocore.exceptions import ClientError

# Mock environment variables before importing
os.environ['TAG_APP_VALUE'] = 'test-app'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'arn:aws:iam::123456789012:instance-profile/test-profile'

# Mock boto3 and dependencies
sys.path.insert(0, '/opt/utilHelper')

# Create mock utilHelper module with proper capitalize_first_letter function
class MockUtils:
    @staticmethod
    def capitalize_first_letter(text):
        """
        Mock implementation that converts camelCase to PascalCase
        e.g., shutdownMethod -> ShutdownMethod, alarmThreshold -> AlarmThreshold
        """
        if not text:
            return text
        # Simply capitalize the first character
        return text[0].upper() + text[1:] if len(text) > 0 else text

mock_util_helper = MagicMock()
mock_util_helper.Utils = MockUtils
sys.modules['utilHelper'] = mock_util_helper

# Import after mocking
from ec2Helper import Ec2Utils


class TestGetInstanceAttributesFromTags(unittest.TestCase):
    """Test suite for get_instance_attributes_from_tags function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.instance_id = 'i-1234567890abcdef0'
        
        # Create mock clients
        self.mock_ec2_client = Mock()
        self.mock_sts_client = Mock()
        self.mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
        
        # Patch boto3.client to return appropriate mocks
        self.patcher = patch('boto3.client')
        self.mock_boto_client = self.patcher.start()
        
        def client_factory(service_name):
            if service_name == 'sts':
                return self.mock_sts_client
            return self.mock_ec2_client
        
        self.mock_boto_client.side_effect = client_factory
        
        # Create Ec2Utils instance
        self.ec2_utils = Ec2Utils()
        self.ec2_utils.ec2_client = self.mock_ec2_client
    
    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()
    
    def test_retrieval_of_shutdown_method_tag(self):
        """Test retrieval of shutdownMethod tag"""
        # Arrange
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                'Tags': [
                    {'Key': 'ShutdownMethod', 'Value': 'Connections'},
                    {'Key': 'AlarmThreshold', 'Value': '0'},
                    {'Key': 'AlarmEvaluationPeriod', 'Value': '10'}
                ]
            }
        ]
        self.mock_ec2_client.get_paginator.return_value = mock_paginator
        
        # Act
        result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
        
        # Assert
        self.assertEqual(result['shutdownMethod'], 'Connections')
        self.assertEqual(result['id'], self.instance_id)
    
    def test_conversion_of_alarm_threshold_string_to_float(self):
        """Test conversion of alarmThreshold string to float"""
        # Arrange - test various valid numeric strings
        test_cases = [
            ('0', 0.0),
            ('5', 5.0),
            ('10.5', 10.5),
            ('100', 100.0),
            ('0.0', 0.0)
        ]
        
        for threshold_str, expected_float in test_cases:
            with self.subTest(threshold=threshold_str):
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = [
                    {
                        'Tags': [
                            {'Key': 'AlarmThreshold', 'Value': threshold_str}
                        ]
                    }
                ]
                self.mock_ec2_client.get_paginator.return_value = mock_paginator
                
                # Act
                result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
                
                # Assert
                self.assertEqual(result['alarmThreshold'], expected_float)
                self.assertIsInstance(result['alarmThreshold'], float)
    
    def test_conversion_of_alarm_evaluation_period_string_to_int(self):
        """Test conversion of alarmEvaluationPeriod string to int"""
        # Arrange - test various valid numeric strings
        test_cases = [
            ('1', 1),
            ('5', 5),
            ('10', 10),
            ('60', 60)
        ]
        
        for period_str, expected_int in test_cases:
            with self.subTest(period=period_str):
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = [
                    {
                        'Tags': [
                            {'Key': 'AlarmEvaluationPeriod', 'Value': period_str}
                        ]
                    }
                ]
                self.mock_ec2_client.get_paginator.return_value = mock_paginator
                
                # Act
                result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
                
                # Assert
                self.assertEqual(result['alarmEvaluationPeriod'], expected_int)
                self.assertIsInstance(result['alarmEvaluationPeriod'], int)
    
    def test_handling_of_missing_tags_default_values(self):
        """Test handling of missing tags returns default values"""
        # Arrange - no tags returned
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {'Tags': []}
        ]
        self.mock_ec2_client.get_paginator.return_value = mock_paginator
        
        # Act
        result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
        
        # Assert - verify all default values
        self.assertEqual(result['id'], self.instance_id)
        self.assertEqual(result['shutdownMethod'], '')
        self.assertEqual(result['stopScheduleExpression'], '')
        self.assertEqual(result['startScheduleExpression'], '')
        self.assertEqual(result['alarmType'], '')
        self.assertEqual(result['alarmThreshold'], 0.0)
        self.assertEqual(result['alarmEvaluationPeriod'], 0)
        self.assertEqual(result['runCommand'], '')
        self.assertEqual(result['workDir'], '')
        self.assertEqual(result['groupMembers'], '')
    
    def test_handling_of_invalid_numeric_values_threshold(self):
        """Test handling of invalid alarmThreshold values"""
        # Arrange - test various invalid values (excluding 'NaN' which converts to float('nan'))
        invalid_values = ['invalid', 'abc', '', 'null']
        
        for invalid_value in invalid_values:
            with self.subTest(invalid_threshold=invalid_value):
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = [
                    {
                        'Tags': [
                            {'Key': 'AlarmThreshold', 'Value': invalid_value}
                        ]
                    }
                ]
                self.mock_ec2_client.get_paginator.return_value = mock_paginator
                
                # Act
                result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
                
                # Assert - should default to 0.0
                self.assertEqual(result['alarmThreshold'], 0.0)
                self.assertIsInstance(result['alarmThreshold'], float)
    
    def test_handling_of_invalid_numeric_values_period(self):
        """Test handling of invalid alarmEvaluationPeriod values"""
        # Arrange - test various invalid values
        invalid_values = ['invalid', 'xyz', '', 'NaN', 'null', '10.5']  # float not valid for int
        
        for invalid_value in invalid_values:
            with self.subTest(invalid_period=invalid_value):
                mock_paginator = Mock()
                mock_paginator.paginate.return_value = [
                    {
                        'Tags': [
                            {'Key': 'AlarmEvaluationPeriod', 'Value': invalid_value}
                        ]
                    }
                ]
                self.mock_ec2_client.get_paginator.return_value = mock_paginator
                
                # Act
                result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
                
                # Assert - should default to 0
                self.assertEqual(result['alarmEvaluationPeriod'], 0)
                self.assertIsInstance(result['alarmEvaluationPeriod'], int)
    
    def test_error_handling_returns_defaults(self):
        """Test that errors during tag retrieval return default values"""
        # Arrange - simulate an error
        mock_paginator = Mock()
        mock_paginator.paginate.side_effect = ClientError(
            {'Error': {'Code': 'InvalidInstanceID.NotFound', 'Message': 'Instance not found'}},
            'DescribeTags'
        )
        self.mock_ec2_client.get_paginator.return_value = mock_paginator
        
        # Act
        result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
        
        # Assert - should return default values
        self.assertEqual(result['id'], self.instance_id)
        self.assertEqual(result['alarmThreshold'], 0.0)
        self.assertEqual(result['alarmEvaluationPeriod'], 0)
        self.assertEqual(result['shutdownMethod'], '')
    
    def test_case_insensitive_tag_key_matching(self):
        """Test that tag keys are matched case-insensitively"""
        # Arrange - tags with various cases
        mock_paginator = Mock()
        mock_paginator.paginate.return_value = [
            {
                'Tags': [
                    {'Key': 'SHUTDOWNMETHOD', 'Value': 'Schedule'},
                    {'Key': 'alarmthreshold', 'Value': '5'},
                    {'Key': 'AlarmEvaluationPeriod', 'Value': '15'}
                ]
            }
        ]
        self.mock_ec2_client.get_paginator.return_value = mock_paginator
        
        # Act
        result = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
        
        # Assert - all should be retrieved regardless of case
        self.assertEqual(result['shutdownMethod'], 'Schedule')
        self.assertEqual(result['alarmThreshold'], 5.0)
        self.assertEqual(result['alarmEvaluationPeriod'], 15)


class TestSetInstanceAttributesToTags(unittest.TestCase):
    """Test suite for set_instance_attributes_to_tags function"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.instance_id = 'i-1234567890abcdef0'
        
        # Create mock clients
        self.mock_ec2_client = Mock()
        self.mock_sts_client = Mock()
        self.mock_sts_client.get_caller_identity.return_value = {'Account': '123456789012'}
        
        # Patch boto3.client
        self.patcher = patch('boto3.client')
        self.mock_boto_client = self.patcher.start()
        
        def client_factory(service_name):
            if service_name == 'sts':
                return self.mock_sts_client
            return self.mock_ec2_client
        
        self.mock_boto_client.side_effect = client_factory
        
        # Create Ec2Utils instance
        self.ec2_utils = Ec2Utils()
        self.ec2_utils.ec2_client = self.mock_ec2_client
        
        # Mock get_instance_attributes_from_tags to return existing tags
        self.ec2_utils.get_instance_attributes_from_tags = Mock(return_value={
            'id': self.instance_id,
            'shutdownMethod': 'CPUUtilization',
            'alarmThreshold': 5.0,
            'alarmEvaluationPeriod': 30
        })
    
    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()
    
    def test_tag_creation_with_valid_configuration(self):
        """Test tag creation with valid Connections configuration"""
        # Arrange
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0,
            'alarmEvaluationPeriod': 10,
            'runCommand': 'java -jar server.jar',
            'workDir': '/home/minecraft'
        }
        
        # Act
        result = self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Assert - verify delete_tags was called
        self.mock_ec2_client.delete_tags.assert_called_once()
        delete_call_args = self.mock_ec2_client.delete_tags.call_args
        self.assertEqual(delete_call_args[1]['Resources'], [self.instance_id])
        
        # Assert - verify create_tags was called with correct tags
        self.mock_ec2_client.create_tags.assert_called_once()
        create_call_args = self.mock_ec2_client.create_tags.call_args
        self.assertEqual(create_call_args[1]['Resources'], [self.instance_id])
        
        # Verify tags are properly formatted
        tags = create_call_args[1]['Tags']
        tag_dict = {tag['Key']: tag['Value'] for tag in tags}
        
        self.assertEqual(tag_dict['ShutdownMethod'], 'Connections')
        self.assertEqual(tag_dict['AlarmThreshold'], '0')
        self.assertEqual(tag_dict['AlarmEvaluationPeriod'], '10')
        self.assertEqual(tag_dict['RunCommand'], 'java -jar server.jar')
        self.assertEqual(tag_dict['WorkDir'], '/home/minecraft')
        
        # Assert - verify return value
        self.assertEqual(result['id'], self.instance_id)
        self.assertEqual(result['shutdownMethod'], 'Connections')
    
    def test_tag_deletion_and_recreation(self):
        """Test that existing tags are deleted before creating new ones"""
        # Arrange
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Schedule',
            'stopScheduleExpression': '0 23 * * *'
        }
        
        # Act
        self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Assert - verify delete was called before create
        self.assertEqual(self.mock_ec2_client.delete_tags.call_count, 1)
        self.assertEqual(self.mock_ec2_client.create_tags.call_count, 1)
        
        # Verify delete was called first
        calls = self.mock_ec2_client.method_calls
        delete_index = next(i for i, call in enumerate(calls) if call[0] == 'delete_tags')
        create_index = next(i for i, call in enumerate(calls) if call[0] == 'create_tags')
        self.assertLess(delete_index, create_index)
    
    def test_handling_of_empty_values(self):
        """Test handling of empty string values (should be excluded)"""
        # Arrange
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0,
            'alarmEvaluationPeriod': 10,
            'runCommand': '',  # Empty string
            'workDir': ''  # Empty string
        }
        
        # Act
        result = self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Assert - verify empty values are not included in tags
        create_call_args = self.mock_ec2_client.create_tags.call_args
        tags = create_call_args[1]['Tags']
        tag_keys = [tag['Key'] for tag in tags]
        
        # Empty values should be filtered out
        self.assertNotIn('RunCommand', tag_keys)
        self.assertNotIn('WorkDir', tag_keys)
        
        # Non-empty values should be present
        self.assertIn('ShutdownMethod', tag_keys)
        self.assertIn('AlarmThreshold', tag_keys)
    
    def test_handling_of_null_values(self):
        """Test handling of None values (should be excluded)"""
        # Arrange
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0,
            'alarmEvaluationPeriod': None,  # None value
            'runCommand': None  # None value
        }
        
        # Act
        result = self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Assert - verify None values are not included in tags
        create_call_args = self.mock_ec2_client.create_tags.call_args
        tags = create_call_args[1]['Tags']
        tag_keys = [tag['Key'] for tag in tags]
        
        # None values should be filtered out
        self.assertNotIn('AlarmEvaluationPeriod', tag_keys)
        self.assertNotIn('RunCommand', tag_keys)
        
        # Non-None values should be present
        self.assertIn('ShutdownMethod', tag_keys)
        self.assertIn('AlarmThreshold', tag_keys)
    
    def test_missing_instance_id_raises_error(self):
        """Test that missing instance ID raises ValueError"""
        # Arrange
        input_config = {
            'shutdownMethod': 'Connections',
            'alarmThreshold': 0
        }
        
        # Act & Assert
        with self.assertRaises(ValueError) as context:
            self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        self.assertIn('Instance ID is required', str(context.exception))
    
    def test_numeric_values_converted_to_strings(self):
        """Test that numeric values are properly converted to strings for tags"""
        # Arrange
        input_config = {
            'id': self.instance_id,
            'alarmThreshold': 5.5,  # Float
            'alarmEvaluationPeriod': 30  # Int
        }
        
        # Act
        self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Assert - verify values are converted to strings
        create_call_args = self.mock_ec2_client.create_tags.call_args
        tags = create_call_args[1]['Tags']
        tag_dict = {tag['Key']: tag['Value'] for tag in tags}
        
        self.assertEqual(tag_dict['AlarmThreshold'], '5.5')
        self.assertIsInstance(tag_dict['AlarmThreshold'], str)
        
        self.assertEqual(tag_dict['AlarmEvaluationPeriod'], '30')
        self.assertIsInstance(tag_dict['AlarmEvaluationPeriod'], str)
    
    def test_error_handling_during_tag_operations(self):
        """Test error handling when tag operations fail"""
        # Arrange
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Connections'
        }
        
        # Simulate error during create_tags
        self.mock_ec2_client.create_tags.side_effect = ClientError(
            {'Error': {'Code': 'UnauthorizedOperation', 'Message': 'Not authorized'}},
            'CreateTags'
        )
        
        # Act & Assert - should not raise, but log error
        result = self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Result should be None when error occurs
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
