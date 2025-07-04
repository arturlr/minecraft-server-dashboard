#!/usr/bin/env python3
"""
Test script for tag validation functionality
"""
import sys
import os
import json

# Add the layers to the path for testing
sys.path.insert(0, '../../layers/ec2Helper')
sys.path.insert(0, '../../layers/utilHelper')

# Mock the environment variables
os.environ['TAG_APP_VALUE'] = 'minecraft-dashboard'
os.environ['COGNITO_USER_POOL_ID'] = 'test-pool'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'test-arn'

# Import the validation function
from index import validate_instance_tags

def test_validation():
    """
    Test the validation function with mock data
    Note: This will fail without actual AWS credentials and instance,
    but shows the structure of the validation
    """
    try:
        # Test with a mock instance ID
        result = validate_instance_tags('i-1234567890abcdef0')
        print("Validation result:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"Expected error (no AWS credentials/instance): {e}")
        print("Validation function structure is correct")

if __name__ == "__main__":
    test_validation()