#!/usr/bin/env python3
"""
Property-based test for EC2 configuration round-trip
Tests that configuration values persist correctly through save and retrieve operations

**Feature: user-based-auto-shutdown, Property 1: Configuration Persistence**
**Validates: Requirements 1.4**
"""
import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings

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


class TestConfigurationRoundTrip(unittest.TestCase):
    """
    Property-based test suite for configuration round-trip persistence
    
    **Feature: user-based-auto-shutdown, Property 1: Configuration Persistence**
    **Validates: Requirements 1.4**
    """
    
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
        
        # Store created tags for retrieval simulation
        self.stored_tags = {}
    
    def tearDown(self):
        """Clean up after tests"""
        self.patcher.stop()
    
    def _simulate_tag_storage(self, instance_id, tags):
        """Simulate storing tags in EC2"""
        self.stored_tags[instance_id] = {tag['Key']: tag['Value'] for tag in tags}
    
    def _simulate_tag_retrieval(self, instance_id):
        """Simulate retrieving tags from EC2"""
        if instance_id not in self.stored_tags:
            return []
        return [{'Key': k, 'Value': v} for k, v in self.stored_tags[instance_id].items()]
    
    @given(
        threshold=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        period=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=100)
    def test_configuration_persistence_round_trip(self, threshold, period):
        """
        Property Test: Configuration Persistence
        
        For any valid configuration with threshold (0-100) and period (1-60),
        saving the configuration and then retrieving it should return the exact
        same values (with appropriate type conversions: float for threshold, int for period).
        
        **Feature: user-based-auto-shutdown, Property 1: Configuration Persistence**
        **Validates: Requirements 1.4**
        """
        # Arrange - Create configuration with random valid values
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': threshold,
            'alarmEvaluationPeriod': period
        }
        
        # Mock the get_instance_attributes_from_tags to return empty initially
        self.ec2_utils.get_instance_attributes_from_tags = Mock(return_value={
            'id': self.instance_id,
            'shutdownMethod': '',
            'alarmThreshold': 0.0,
            'alarmEvaluationPeriod': 0
        })
        
        # Mock delete_tags to succeed
        self.mock_ec2_client.delete_tags.return_value = {}
        
        # Mock create_tags to capture the tags being set
        def capture_tags(Resources, Tags):
            self._simulate_tag_storage(Resources[0], Tags)
            return {}
        
        self.mock_ec2_client.create_tags.side_effect = capture_tags
        
        # Mock the paginator for tag retrieval
        def mock_paginate(**kwargs):
            tags = self._simulate_tag_retrieval(self.instance_id)
            return [{'Tags': tags}]
        
        mock_paginator = Mock()
        mock_paginator.paginate.side_effect = mock_paginate
        self.mock_ec2_client.get_paginator.return_value = mock_paginator
        
        # Act - Save configuration via set_instance_attributes_to_tags
        save_result = self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Retrieve configuration via get_instance_attributes_from_tags
        # We need to call the actual method, not the mock
        self.ec2_utils.get_instance_attributes_from_tags = Ec2Utils.get_instance_attributes_from_tags.__get__(
            self.ec2_utils, Ec2Utils
        )
        retrieved_config = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
        
        # Assert - Retrieved values should match original (with type conversions)
        self.assertEqual(retrieved_config['id'], self.instance_id)
        self.assertEqual(retrieved_config['shutdownMethod'], 'Connections')
        
        # Threshold should match as float (allowing for floating point precision)
        self.assertIsInstance(retrieved_config['alarmThreshold'], float)
        self.assertAlmostEqual(retrieved_config['alarmThreshold'], threshold, places=5)
        
        # Period should match as int
        self.assertIsInstance(retrieved_config['alarmEvaluationPeriod'], int)
        self.assertEqual(retrieved_config['alarmEvaluationPeriod'], period)
    
    @given(
        threshold=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
        period=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=100)
    def test_configuration_persistence_with_additional_fields(self, threshold, period):
        """
        Property Test: Configuration Persistence with Additional Fields
        
        For any valid configuration including optional fields (runCommand, workDir),
        all fields should persist correctly through save and retrieve operations.
        
        **Feature: user-based-auto-shutdown, Property 1: Configuration Persistence**
        **Validates: Requirements 1.4**
        """
        # Arrange - Create configuration with random valid values and additional fields
        input_config = {
            'id': self.instance_id,
            'shutdownMethod': 'Connections',
            'alarmThreshold': threshold,
            'alarmEvaluationPeriod': period,
            'runCommand': 'java -jar server.jar',
            'workDir': '/home/minecraft'
        }
        
        # Mock the get_instance_attributes_from_tags to return empty initially
        self.ec2_utils.get_instance_attributes_from_tags = Mock(return_value={
            'id': self.instance_id,
            'shutdownMethod': '',
            'alarmThreshold': 0.0,
            'alarmEvaluationPeriod': 0,
            'runCommand': '',
            'workDir': ''
        })
        
        # Mock delete_tags to succeed
        self.mock_ec2_client.delete_tags.return_value = {}
        
        # Mock create_tags to capture the tags being set
        def capture_tags(Resources, Tags):
            self._simulate_tag_storage(Resources[0], Tags)
            return {}
        
        self.mock_ec2_client.create_tags.side_effect = capture_tags
        
        # Mock the paginator for tag retrieval
        def mock_paginate(**kwargs):
            tags = self._simulate_tag_retrieval(self.instance_id)
            return [{'Tags': tags}]
        
        mock_paginator = Mock()
        mock_paginator.paginate.side_effect = mock_paginate
        self.mock_ec2_client.get_paginator.return_value = mock_paginator
        
        # Act - Save configuration
        save_result = self.ec2_utils.set_instance_attributes_to_tags(input_config)
        
        # Retrieve configuration
        self.ec2_utils.get_instance_attributes_from_tags = Ec2Utils.get_instance_attributes_from_tags.__get__(
            self.ec2_utils, Ec2Utils
        )
        retrieved_config = self.ec2_utils.get_instance_attributes_from_tags(self.instance_id)
        
        # Assert - All fields should match
        self.assertEqual(retrieved_config['id'], self.instance_id)
        self.assertEqual(retrieved_config['shutdownMethod'], 'Connections')
        self.assertAlmostEqual(retrieved_config['alarmThreshold'], threshold, places=5)
        self.assertEqual(retrieved_config['alarmEvaluationPeriod'], period)
        self.assertEqual(retrieved_config['runCommand'], 'java -jar server.jar')
        self.assertEqual(retrieved_config['workDir'], '/home/minecraft')


if __name__ == '__main__':
    unittest.main()
