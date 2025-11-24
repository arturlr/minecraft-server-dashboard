#!/usr/bin/env python3
"""
Test EventBridge rule creation with the converted cron expressions
"""
import boto3
import json

def test_eventbridge_rule():
    """Test creating EventBridge rule with converted cron expression"""
    
    # Test the converted expressions
    test_expressions = [
        "cron(00 02 * * 1,2,3,4,5,6,7 *)",  # Converted stop schedule
        "cron(00 14 * * 1,2,3,4,5,6,7 *)",  # Converted start schedule
    ]
    
    eventbridge = boto3.client('events')
    
    for i, schedule_expr in enumerate(test_expressions):
        rule_name = f"test-rule-{i}"
        
        try:
            print(f"Testing schedule expression: {schedule_expr}")
            
            # Try to create the rule
            response = eventbridge.put_rule(
                Name=rule_name,
                ScheduleExpression=schedule_expr,
                State='DISABLED',  # Keep it disabled for testing
                Description="Test rule for cron validation"
            )
            
            print(f"✅ SUCCESS: Rule created with ARN: {response['RuleArn']}")
            
            # Clean up - delete the test rule
            eventbridge.delete_rule(Name=rule_name)
            print(f"✅ Test rule {rule_name} deleted")
            
        except Exception as e:
            print(f"❌ ERROR: Failed to create rule with expression '{schedule_expr}': {e}")

if __name__ == "__main__":
    test_eventbridge_rule()