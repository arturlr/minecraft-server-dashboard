#!/usr/bin/env python3
"""
Simple test for cron day-of-week conversion logic
"""

def convert_single_dow(value):
    """Convert a single day-of-week value from standard cron (0-6) to EventBridge (1-7)."""
    if value == '0':  # Sunday
        return '7'
    elif value.isdigit() and 1 <= int(value) <= 6:
        return value
    else:
        return None

def convert_day_of_week(day_of_week):
    """Convert day-of-week from standard cron format to EventBridge format."""
    if day_of_week == '*':
        return '*'
        
    # Handle comma-separated values
    if ',' in day_of_week:
        values = day_of_week.split(',')
        converted_values = []
        for val in values:
            converted_val = convert_single_dow(val.strip())
            if converted_val is None:
                return None
            converted_values.append(converted_val)
        return ','.join(converted_values)
    
    # Handle ranges
    if '-' in day_of_week:
        try:
            start, end = day_of_week.split('-')
            start_converted = convert_single_dow(start.strip())
            end_converted = convert_single_dow(end.strip())
            if start_converted is None or end_converted is None:
                return None
            return f"{start_converted}-{end_converted}"
        except ValueError:
            return None
    
    # Handle single value
    return convert_single_dow(day_of_week)

def format_schedule_expression(cron_expression):
    """Format and validate cron expression for EventBridge."""
    if not cron_expression or not isinstance(cron_expression, str):
        return None
        
    cron_expression = cron_expression.strip()
    
    # If already in EventBridge format, return as-is
    if cron_expression.startswith('cron(') and cron_expression.endswith(')'):
        return cron_expression
    
    # Handle standard 5-field cron expression
    fields = cron_expression.split()
    if len(fields) == 5:
        minute, hour, day, month, day_of_week = fields
        
        # Convert day-of-week
        converted_dow = convert_day_of_week(day_of_week)
        if not converted_dow:
            return None
        
        # Convert to EventBridge format
        eventbridge_cron = f"cron({minute} {hour} {day} {month} {converted_dow} *)"
        return eventbridge_cron
    
    return None

def validate_single_dow_value(value):
    """Validate a single day-of-week value for standard cron (0-6)."""
    try:
        val = int(value)
        return 0 <= val <= 6  # Standard cron allows 0-6
    except ValueError:
        return False

def validate_dow_field(day_of_week):
    """Validate day-of-week field for standard cron format (0-6, where 0=Sunday)."""
    if day_of_week == '*':
        return True
        
    # Handle comma-separated values
    if ',' in day_of_week:
        values = day_of_week.split(',')
        return all(validate_single_dow_value(val.strip()) for val in values)
    
    # Handle ranges
    if '-' in day_of_week:
        try:
            start, end = day_of_week.split('-')
            return (validate_single_dow_value(start.strip()) and 
                   validate_single_dow_value(end.strip()))
        except ValueError:
            return False
    
    # Single value
    return validate_single_dow_value(day_of_week)

def test_cron_expressions():
    """Test various cron expression formats"""
    test_cases = [
        # The failing cases from the error
        ("00 03 * * 1,2,3,4,5,6,0", "cron(00 03 * * 1,2,3,4,5,6,7 *)"),
        ("00 12 * * 1,2,3,4,5,6,0", "cron(00 12 * * 1,2,3,4,5,6,7 *)"),
        ("00 02 * * 1,2,3,4,5,6,0", "cron(00 02 * * 1,2,3,4,5,6,7 *)"),  # New failing case
        ("00 14 * * 1,2,3,4,5,6,0", "cron(00 14 * * 1,2,3,4,5,6,7 *)"),  # New failing case
        
        # Other test cases
        ("30 14 * * 1,2,3", "cron(30 14 * * 1,2,3 *)"),
        ("0 9 * * 0", "cron(0 9 * * 7 *)"),  # Sunday conversion
        ("15 22 * * 1-5", "cron(15 22 * * 1-5 *)"),  # Range
        ("* * * * *", "cron(* * * * * *)"),  # All wildcards
    ]
    
    # Test validation first
    print("Testing day-of-week validation:")
    print("-" * 40)
    dow_test_cases = [
        ("1,2,3,4,5,6,0", True),
        ("0", True),
        ("7", False),  # Invalid in standard cron
        ("1-5", True),
        ("*", True),
    ]
    
    for dow, expected in dow_test_cases:
        result = validate_dow_field(dow)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} DOW: '{dow}' -> Valid: {result} (Expected: {expected})")
    
    print("\nTesting full cron expression conversion:")
    print("-" * 50)
    

    
    for input_expr, expected in test_cases:
        result = format_schedule_expression(input_expr)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"{status} Input: '{input_expr}'")
        print(f"     Output: '{result}'")
        print(f"   Expected: '{expected}'")
        print()
    
    print("=" * 60)

if __name__ == "__main__":
    test_cron_expressions()