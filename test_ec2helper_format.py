#!/usr/bin/env python3
"""Test the ec2Helper _format_schedule_expression method"""

import sys
sys.path.insert(0, 'cfn/.aws-sam/cache/0f0837c0-b2fe-4db1-9375-bc02ffa9384a/python')

from ec2Helper import Ec2Utils

# Create instance
ec2 = Ec2Utils()

# Test cases from the working test
test_cases = [
    ("30 14 * * 1,2,3", "cron(30 14 ? * 1,2,3 *)"),
    ("0 9 * * 0", "cron(0 9 ? * 7 *)"),
    ("00 03 * * 1,2,3,4,5,6,0", "cron(0 3 ? * * *)"),
    ("30 16 * * 1,2,3,4,5,6,0", "cron(30 16 ? * * *)"),
]

print("Testing ec2Helper._format_schedule_expression:")
print("=" * 80)

for input_expr, expected in test_cases:
    try:
        result = ec2._format_schedule_expression(input_expr)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status}")
        print(f"  Input:    '{input_expr}'")
        print(f"  Expected: '{expected}'")
        print(f"  Got:      '{result}'")
    except Exception as e:
        print(f"❌ ERROR")
        print(f"  Input:    '{input_expr}'")
        print(f"  Expected: '{expected}'")
        print(f"  Error:    {e}")
    print()

print("=" * 80)
