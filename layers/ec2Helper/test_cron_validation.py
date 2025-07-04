#!/usr/bin/env python3
"""
Test script for cron expression validation and formatting
"""
import sys
import os

# Add the current directory to path for testing
sys.path.insert(0, '.')

# Mock the environment variables and dependencies
os.environ['TAG_APP_VALUE'] = 'test'
os.environ['EC2_INSTANCE_PROFILE_ARN'] = 'test-arn'

# Mock boto3 for testing
class MockBoto3:
    def client(self, service):
        return self
    
    def describe_tags(self, **kwargs):
        return {'Tags': []}

sys.modules['boto3'] = MockBoto3()

# Import the Ec2Utils class
from ec2Helper import Ec2Utils

def test_cron_expressions():
    """Test various cron expression formats"""
    ec2_utils = Ec2Utils()
    
    test_cases = [
        # Valid cases
        ("30 14 * * 1,2,3", "cron(30 14 * * 1,2,3 *)"),  # Standard 5-field cron
        ("0 9 * * 0", "cron(0 9 * * 0 *)"),  # Sunday at 9 AM
        ("15 22 * * 1-5", "cron(15 22 * * 1-5 *)"),  # Weekdays at 10:15 PM
        ("cron(30 14 * * 1,2,3 *)", "cron(30 14 * * 1,2,3 *)"),  # Already formatted
        
        # Invalid cases
        ("", None),  # Empty string
        ("30 14 * *", None),  # Too few fields
        ("30 14 * * 1 2 3", None),  # Too many fields
        ("60 14 * * 1", None),  # Invalid minute
        ("30 25 * * 1", None),  # Invalid hour
        ("30 14 * * 8", None),  # Invalid day of week
    ]
    
    print("Testing cron expression validation and formatting:")
    print("=" * 60)
    
    for input_expr, expected in test_cases:
        try:
            result = ec2_utils._format_schedule_expression(input_expr)
            status = "✅ PASS" if result == expected else "❌ FAIL"
            print(f"{status} Input: '{input_expr}' -> Output: '{result}' (Expected: '{expected}')")
        except Exception as e:
            print(f"❌ ERROR Input: '{input_expr}' -> Exception: {e}")
    
    print("\n" + "=" * 60)
    print("Test completed!")

if __name__ == "__main__":
    test_cron_expressions()